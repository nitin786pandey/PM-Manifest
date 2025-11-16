import os
import time
import typing as t
from dataclasses import dataclass

import requests


DEFAULT_INDICES = "manifest-events-prod-alias,events-prod-alias,bik-internal-events"


@dataclass
class ElasticsearchConfig:
	"""Holds Elasticsearch connection configuration."""
	base_url: str
	api_key: str
	indices: str = DEFAULT_INDICES

	@staticmethod
	def from_env() -> "ElasticsearchConfig":
		base_url = os.getenv("ELASTIC_BASE_URL", "").rstrip("/")
		api_key = os.getenv("ELASTIC_API_KEY", "")
		if not base_url or not api_key:
			raise RuntimeError("ELASTIC_BASE_URL and ELASTIC_API_KEY must be set in environment")
		return ElasticsearchConfig(base_url=base_url, api_key=api_key)

	def headers(self) -> dict:
		return {
			"Content-Type": "application/json",
			"Authorization": f"ApiKey {self.api_key}",
		}


def _url(cfg: ElasticsearchConfig, path: str) -> str:
	return f"{cfg.base_url}/{path.lstrip('/')}"


def get_mapping(cfg: ElasticsearchConfig, indices: t.Optional[str] = None) -> dict:
	"""Fetch index mappings to discover fields (especially eventProperties.*)."""
	indices = indices or cfg.indices
	resp = requests.get(_url(cfg, f"{indices}/_mapping"), headers=cfg.headers(), timeout=60)
	resp.raise_for_status()
	return resp.json()


def search(
	cfg: ElasticsearchConfig,
	dsl: dict,
	indices: t.Optional[str] = None,
	timeout_s: int = 120,
) -> dict:
	"""Run a single _search call and return raw JSON."""
	indices = indices or cfg.indices
	resp = requests.post(_url(cfg, f"{indices}/_search"), headers=cfg.headers(), json=dsl, timeout=timeout_s)
	resp.raise_for_status()
	return resp.json()


def search_all(
	cfg: ElasticsearchConfig,
	dsl: dict,
	indices: t.Optional[str] = None,
	sort: t.Optional[t.List[t.Union[str, dict]]] = None,
	batch_size: int = 1000,
	max_docs: t.Optional[int] = None,
	sleep_ms: int = 0,
) -> t.List[dict]:
	"""
	Paginate through hits using search_after. Returns concatenated hits (not sources).
	Prefer aggregations when possible; this is for exceptional cases.
	"""
	indices = indices or cfg.indices

	dsl = dict(dsl)  # shallow copy
	dsl.setdefault("track_total_hits", True)
	dsl["size"] = batch_size
	if sort:
		dsl["sort"] = sort
	elif "sort" not in dsl:
		# Stable sort for pagination: by createdAt then _id
		dsl["sort"] = [
			{"createdAt": "asc"},
			{"_id": "asc"},
		]

	all_hits: t.List[dict] = []
	search_after: t.Optional[t.List[t.Any]] = None

	while True:
		if search_after:
			dsl["search_after"] = search_after
		resp = requests.post(_url(cfg, f"{indices}/_search"), headers=cfg.headers(), json=dsl, timeout=180)
		resp.raise_for_status()
		data = resp.json()
		hits = data.get("hits", {}).get("hits", [])
		if not hits:
			break
		all_hits.extend(hits)
		if max_docs is not None and len(all_hits) >= max_docs:
			all_hits = all_hits[:max_docs]
			break
		search_after = hits[-1].get("sort")
		if sleep_ms:
			time.sleep(sleep_ms / 1000.0)
	return all_hits


def build_date_range_query(gte: str, lte: str = "now") -> dict:
	return {
		"range": {
			"createdAt": {
				"gte": gte,
				"lte": lte,
			}
		}
	}


def base_bool_query(filters: t.List[dict]) -> dict:
	return {
		"bool": {
			"filter": filters or []
		}
	}


