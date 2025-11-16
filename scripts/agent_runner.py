import argparse
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from es_fetch import (
	ElasticsearchConfig,
	base_bool_query,
	build_date_range_query,
	search,
)
from es_to_df import hits_to_dataframe
from manifest_analysis import (
	compute_interaction_rate,
	filter_event,
	compute_unique_sessions,
	compute_total_sales,
	compute_aov,
	compute_interaction_rate_from_counts,
	make_two_periods,
	compute_shift_share_drivers,
)


def ask_or_default(prompt: str, default: str) -> str:
	"""
	Ask a question on console (if interactive), otherwise use default.
	"""
	if os.isatty(0):
		resp = input(f"{prompt} [{default}]: ").strip()
		return resp or default
	return default


def build_session_counts_dsl(gte: str, lte: str, session_field: str = "visitorSessionId", store_id: Optional[str] = None) -> Dict[str, Any]:
	"""
	Builds an aggregation to count total sessions and interacted sessions.
	This assumes documents representing sessions exist (e.g., widget/session events).
	"""
	filters = [build_date_range_query(gte=gte, lte=lte)]
	if store_id:
		filters.append({"term": {"storeId.keyword": store_id}})
	query = base_bool_query(filters)
	dsl = {
		"track_total_hits": True,
		"size": 0,
		"query": query,
		"aggs": {
			"total_sessions": {"cardinality": {"field": f"{session_field}.keyword"}},
			"interacted_sessions": {
				"filter": {"term": {"hasInteracted": True}},
				"aggs": {"unique_sessions": {"cardinality": {"field": f"{session_field}.keyword"}}},
			},
		},
	}
	return dsl


def build_checkout_agg_dsl(gte: str, lte: str, store_id: Optional[str] = None) -> Dict[str, Any]:
	filters = [build_date_range_query(gte=gte, lte=lte), {"term": {"eventName.keyword": "checkoutCompleted"}}]
	if store_id:
		filters.append({"term": {"storeId.keyword": store_id}})
	query = base_bool_query(filters)
	return {
		"track_total_hits": True,
		"size": 0,
		"query": query,
		"aggs": {
			"total_sales": {"sum": {"field": "eventProperties.totalAmountUSD"}},
			"unique_sessions": {"cardinality": {"field": "visitorSessionId.keyword"}},
		},
	}


def build_event_count_dsl(gte: str, lte: str, event_name: str, store_id: Optional[str] = None) -> Dict[str, Any]:
	filters = [build_date_range_query(gte=gte, lte=lte), {"term": {"eventName.keyword": event_name}}]
	if store_id:
		filters.append({"term": {"storeId.keyword": store_id}})
	query = base_bool_query(filters)
	return {
		"track_total_hits": True,
		"size": 0,
		"query": query,
	}


def _extract_total_hits(resp: Dict[str, Any]) -> int:
	hits = resp.get("hits", {})
	total = hits.get("total", 0)
	if isinstance(total, dict):
		return int(total.get("value", 0) or 0)
	return int(total or 0)


def build_event_sum_count_dsl(gte: str, lte: str, event_name: str, store_id: Optional[str] = None) -> Dict[str, Any]:
	filters = [build_date_range_query(gte=gte, lte=lte), {"term": {"eventName.keyword": event_name}}]
	if store_id:
		filters.append({"term": {"storeId.keyword": store_id}})
	query = base_bool_query(filters)
	return {
		"track_total_hits": True,
		"size": 0,
		"query": query,
		"aggs": {"total_count": {"sum": {"field": "eventProperties.count"}}},
	}


def _extract_sum_count(resp: Dict[str, Any]) -> float:
	return float(resp.get("aggregations", {}).get("total_count", {}).get("value", 0.0) or 0.0)


def detect_counter_event(cfg: ElasticsearchConfig, event_name: str, gte: str, lte: str, store_id: Optional[str], indices: Optional[str] = None) -> bool:
	"""
	Detect if an event is a counter: if any sampled document contains eventProperties.count.
	Fallback approach when mappings are restricted.
	"""
	filters = [build_date_range_query(gte=gte, lte=lte), {"term": {"eventName.keyword": event_name}}]
	if store_id:
		filters.append({"term": {"storeId.keyword": store_id}})
	dsl = {
		"size": 25,
		"track_total_hits": True,
		"query": base_bool_query(filters),
		"sort": [{"createdAt": {"order": "desc"}}],
	}
	try:
		resp = search(cfg, dsl, indices=indices)
	except Exception:
		return False
	for hit in resp.get("hits", {}).get("hits", []):
		props = hit.get("_source", {}).get("eventProperties", {}) or {}
		if "count" in props:
			return True
	return False


def get_event_total(cfg: ElasticsearchConfig, event_name: str, gte: str, lte: str, store_id: Optional[str], indices: Optional[str] = None) -> float:
	"""
	Return total for an event across timeframe:
	- If counter: sum(eventProperties.count)
	- Else: total document hits
	"""
	is_counter = detect_counter_event(cfg, event_name=event_name, gte=gte, lte=lte, store_id=store_id, indices=indices)
	if is_counter:
		resp = search(cfg, build_event_sum_count_dsl(gte=gte, lte=lte, event_name=event_name, store_id=store_id), indices=indices)
		return _extract_sum_count(resp)
	resp = search(cfg, build_event_count_dsl(gte=gte, lte=lte, event_name=event_name, store_id=store_id), indices=indices)
	return float(_extract_total_hits(resp))


def build_daily_timeseries_dsl(
	gte: str,
	lte: str,
	event_name: str,
	store_id: Optional[str],
	use_sum_count: bool,
) -> Dict[str, Any]:
	filters = [build_date_range_query(gte=gte, lte=lte), {"term": {"eventName.keyword": event_name}}]
	if store_id:
		filters.append({"term": {"storeId.keyword": store_id}})
	query = base_bool_query(filters)
	aggs: Dict[str, Any] = {
		"by_day": {
			"date_histogram": {"field": "createdAt", "calendar_interval": "day"}
		}
	}
	if use_sum_count:
		aggs["by_day"]["aggs"] = {"total": {"sum": {"field": "eventProperties.count"}}}
	return {
		"track_total_hits": True,
		"size": 0,
		"query": query,
		"aggs": aggs,
	}


def extract_daily_series(resp: Dict[str, Any], use_sum_count: bool) -> List[Dict[str, Any]]:
	buckets = resp.get("aggregations", {}).get("by_day", {}).get("buckets", []) or []
	series: List[Dict[str, Any]] = []
	for b in buckets:
		value = float(b.get("total", {}).get("value", 0.0)) if use_sum_count else float(b.get("doc_count", 0))
		series.append({"date": b.get("key_as_string") or b.get("key"), "value": value})
	return series


def counter_aware_daily_series(
	cfg: ElasticsearchConfig,
	event_name: str,
	gte: str,
	lte: str,
	store_id: Optional[str],
	indices: Optional[str] = None,
) -> List[Dict[str, Any]]:
	is_counter = detect_counter_event(cfg, event_name=event_name, gte=gte, lte=lte, store_id=store_id, indices=indices)
	dsl = build_daily_timeseries_dsl(gte=gte, lte=lte, event_name=event_name, store_id=store_id, use_sum_count=is_counter)
	resp = search(cfg, dsl, indices=indices)
	return extract_daily_series(resp, use_sum_count=is_counter)


def build_terms_cohort_dsl(
	gte: str,
	lte: str,
	event_name: str,
	cohort_field: str,
	use_sum_count: bool,
	size: int = 1000,
) -> Dict[str, Any]:
	filters = [build_date_range_query(gte=gte, lte=lte), {"term": {"eventName.keyword": event_name}}]
	query = base_bool_query(filters)
	sub_aggs: Dict[str, Any] = {}
	if use_sum_count:
		sub_aggs["total"] = {"sum": {"field": "eventProperties.count"}}
	return {
		"track_total_hits": True,
		"size": 0,
		"query": query,
		"aggs": {
			"by_key": {
				"terms": {"field": f"{cohort_field}.keyword", "size": size},
				"aggs": sub_aggs,
			}
		},
	}


def extract_terms_values(resp: Dict[str, Any], use_sum_count: bool) -> Dict[str, float]:
	buckets = resp.get("aggregations", {}).get("by_key", {}).get("buckets", []) or []
	out: Dict[str, float] = {}
	for b in buckets:
		key = b.get("key")
		value = float(b.get("total", {}).get("value", 0.0)) if use_sum_count else float(b.get("doc_count", 0))
		out[str(key)] = value
	return out


def counter_aware_cohort_totals(
	cfg: ElasticsearchConfig,
	event_name: str,
	gte: str,
	lte: str,
	cohort_field: str,
	indices: Optional[str] = None,
) -> Tuple[Dict[str, float], bool]:
	# Detect counter with a quick sample
	is_counter = detect_counter_event(cfg, event_name=event_name, gte=gte, lte=lte, store_id=None, indices=indices)
	dsl = build_terms_cohort_dsl(gte=gte, lte=lte, event_name=event_name, cohort_field=cohort_field, use_sum_count=is_counter)
	resp = search(cfg, dsl, indices=indices)
	return extract_terms_values(resp, use_sum_count=is_counter), is_counter


def run_rca_interaction_rate(
	cfg: ElasticsearchConfig,
	store_id: Optional[str],
	indices: Optional[str],
	compare_days: int,
	cohort_field: str,
	top_x: int,
) -> Dict[str, Any]:
	steps: List[str] = []
	queries: List[Dict[str, Any]] = []
	gte_cur, lte_cur, gte_prev, lte_prev = make_two_periods(compare_days=compare_days)
	steps.append(f"Preparing counter-aware daily timeseries for {compare_days}d and prior {compare_days}d.")
	# Daily series for clicks and visits
	clicks_cur = counter_aware_daily_series(cfg, "widgetClickedSession", gte_cur, lte_cur, store_id, indices)
	visits_cur = counter_aware_daily_series(cfg, "widgetVisitedSession", gte_cur, lte_cur, store_id, indices)
	clicks_prev = counter_aware_daily_series(cfg, "widgetClickedSession", gte_prev, lte_prev, store_id, indices)
	visits_prev = counter_aware_daily_series(cfg, "widgetVisitedSession", gte_prev, lte_prev, store_id, indices)
	# Summaries
	sum_clicks_cur = sum(pt["value"] for pt in clicks_cur)
	sum_visits_cur = sum(pt["value"] for pt in visits_cur)
	sum_clicks_prev = sum(pt["value"] for pt in clicks_prev)
	sum_visits_prev = sum(pt["value"] for pt in visits_prev)
	rate_cur = compute_interaction_rate_from_counts(sum_clicks_cur, sum_visits_cur)
	rate_prev = compute_interaction_rate_from_counts(sum_clicks_prev, sum_visits_prev)
	steps.append(f"Executed series: visits={sum_visits_cur:.0f} vs {sum_visits_prev:.0f}, clicks={sum_clicks_cur:.0f} vs {sum_clicks_prev:.0f}.")
	# Cohort breakdown by cohort_field
	steps.append(f"Executing cohort breakdown by {cohort_field}.")
	visits_by_key_cur, _ = counter_aware_cohort_totals(cfg, "widgetVisitedSession", gte_cur, lte_cur, cohort_field, indices)
	clicks_by_key_cur, _ = counter_aware_cohort_totals(cfg, "widgetClickedSession", gte_cur, lte_cur, cohort_field, indices)
	visits_by_key_prev, _ = counter_aware_cohort_totals(cfg, "widgetVisitedSession", gte_prev, lte_prev, cohort_field, indices)
	clicks_by_key_prev, _ = counter_aware_cohort_totals(cfg, "widgetClickedSession", gte_prev, lte_prev, cohort_field, indices)
	keys = set(list(visits_by_key_cur.keys()) + list(visits_by_key_prev.keys()) + list(clicks_by_key_cur.keys()) + list(clicks_by_key_prev.keys()))
	cohort_rows: List[Dict[str, Any]] = []
	for k in keys:
		v_cur = visits_by_key_cur.get(k, 0.0)
		c_cur = clicks_by_key_cur.get(k, 0.0)
		v_prev = visits_by_key_prev.get(k, 0.0)
		c_prev = clicks_by_key_prev.get(k, 0.0)
		r_cur_k = compute_interaction_rate_from_counts(c_cur, v_cur)
		r_prev_k = compute_interaction_rate_from_counts(c_prev, v_prev)
		cohort_rows.append({
			"key": k,
			"visits": v_cur,
			"clicks": c_cur,
			"rate": r_cur_k,
			"visits_prev": v_prev,
			"clicks_prev": c_prev,
			"rate_prev": r_prev_k,
		})
	# Contributions (simple: weight by current visit share times rate change)
	total_v_cur = sum_visits_cur if sum_visits_cur > 0 else 1.0
	for row in cohort_rows:
		share = row["visits"] / total_v_cur
		row["contribution_to_delta"] = share * (row["rate"] - row["rate_prev"])
	# Top contributors
	top_contributors = sorted(cohort_rows, key=lambda r: abs(r.get("contribution_to_delta", 0.0)), reverse=True)[: top_x]
	# Drivers
	drivers = compute_shift_share_drivers(
		sum_clicks_cur, sum_visits_cur, sum_clicks_prev, sum_visits_prev,
		{r["key"]: r["clicks"] for r in cohort_rows},
		{r["key"]: r["visits"] for r in cohort_rows},
		{r["key"]: r["clicks_prev"] for r in cohort_rows},
		{r["key"]: r["visits_prev"] for r in cohort_rows},
	)
	# Output structure
	return {
		"summary": {
			"period_current": {"visits": sum_visits_cur, "clicks": sum_clicks_cur, "rate": rate_cur},
			"period_previous": {"visits": sum_visits_prev, "clicks": sum_clicks_prev, "rate": rate_prev},
			"delta": {"visits": sum_visits_cur - sum_visits_prev, "clicks": sum_clicks_cur - sum_clicks_prev, "rate": rate_cur - rate_prev},
		},
		"timeSeries": [
			{"date": s["date"], "visits": s["value"], "clicks": next((c["value"] for c in clicks_cur if c["date"] == s["date"]), 0.0), "rate": compute_interaction_rate_from_counts(next((c["value"] for c in clicks_cur if c["date"] == s["date"]), 0.0), s["value"])}
			for s in visits_cur
		],
		"cohortBreakdown": cohort_rows,
		"topContributors": top_contributors,
		"drivers": drivers,
		"steps": steps,
	}

def run_interaction_rate_analysis(cfg: ElasticsearchConfig, gte: str, lte: str, store_id: Optional[str] = None) -> Dict[str, Any]:
	"""
	Compute interaction rate and related drivers using aggregations.
	"""
	dsl_sessions = build_session_counts_dsl(gte=gte, lte=lte, session_field="visitorSessionId", store_id=store_id)
	session_resp = search(cfg, dsl_sessions)
	total_sessions = session_resp.get("aggregations", {}).get("total_sessions", {}).get("value", 0)
	interacted_sessions = session_resp.get("aggregations", {}).get("interacted_sessions", {}).get("unique_sessions", {}).get("value", 0)
	interaction_rate = (interacted_sessions / total_sessions * 100.0) if total_sessions else 0.0

	# Sales context
	dsl_checkout = build_checkout_agg_dsl(gte=gte, lte=lte, store_id=store_id)
	checkout_resp = search(cfg, dsl_checkout)
	total_sales = checkout_resp.get("aggregations", {}).get("total_sales", {}).get("value", 0.0)
	unique_order_sessions = checkout_resp.get("aggregations", {}).get("unique_sessions", {}).get("value", 0)

	return {
		"interaction_rate": interaction_rate,
		"total_sessions": total_sessions,
		"interacted_sessions": interacted_sessions,
		"total_store_sales_usd": total_sales,
		"unique_sessions_with_orders": unique_order_sessions,
	}


def run_interaction_rate_clicks_over_visits(cfg: ElasticsearchConfig, gte: str, lte: str, store_id: Optional[str] = None) -> Dict[str, Any]:
	"""
	Interaction rate = count(widgetClickedSession) / count(widgetVisitedSession) * 100.
	"""
	clicks = get_event_total(cfg, event_name="widgetClickedSession", gte=gte, lte=lte, store_id=store_id)
	visits = get_event_total(cfg, event_name="widgetVisitedSession", gte=gte, lte=lte, store_id=store_id)
	rate = (clicks / visits * 100.0) if visits else 0.0
	return {
		"interaction_rate": rate,
		"widget_clicks": clicks,
		"widget_visits": visits,
	}


def main() -> None:
	parser = argparse.ArgumentParser(description="Agentic runner for Manifest analytics")
	parser.add_argument("--question", type=str, required=True, help="Natural language question")
	parser.add_argument("--gte", type=str, default="now-90d/d", help="Start time (Elasticsearch format)")
	parser.add_argument("--lte", type=str, default="now", help="End time (Elasticsearch format)")
	parser.add_argument("--indices", type=str, default=None, help="Override indices")
	parser.add_argument("--session-field", type=str, default="visitorSessionId", help="Session id field")
	parser.add_argument("--store-id", type=str, default=None, help="Filter by storeId (exact match)")
	parser.add_argument("--cohort", type=str, default="storeId", help="Cohort dimension field (default: storeId)")
	parser.add_argument("--top-x", type=int, default=10, help="Top contributors to include")
	parser.add_argument("--compare-window", type=int, default=28, help="Compare window in days (current vs previous)")
	args = parser.parse_args()

	cfg = ElasticsearchConfig.from_env()
	if args.indices:
		cfg.indices = args.indices

	question = args.question.lower().strip()

	# Clarify ambiguous definitions
	if "interaction rate" in question:
		# Use clicks/visits definition per latest guidance
		result_clicks_visits = run_interaction_rate_clicks_over_visits(cfg, gte=args.gte, lte=args.lte, store_id=args.store_id)
		# Include legacy hasInteracted context for reference
		result_sessions = run_interaction_rate_analysis(cfg, gte=args.gte, lte=args.lte, store_id=args.store_id)
		result = {
			"clicks_over_visits": result_clicks_visits,
			"sessions_based": result_sessions,
		}
		print(json.dumps({"answer": result}, indent=2))
		return
	if "rca" in question and "interaction rate" in question:
		cohort_field = args.cohort or "storeId"
		rca = run_rca_interaction_rate(
			cfg=cfg,
			store_id=args.store_id,
			indices=cfg.indices,
			compare_days=args.compare_window,
			cohort_field=cohort_field,
			top_x=args.top_x,
		)
		print(json.dumps({"answer": rca}, indent=2))
		return

	print(json.dumps({"info": "No supported question detected yet.", "question": args.question}, indent=2))


if __name__ == "__main__":
	main()


