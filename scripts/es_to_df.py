import typing as t

import pandas as pd
from pandas import json_normalize


def hits_to_dataframe(hits: t.List[dict], flatten_event_properties: bool = True) -> pd.DataFrame:
	"""
	Convert Elasticsearch hits into a pandas DataFrame.
	- Extracts `_index`, `_id`, `_source.*`
	- Optionally flattens `_source.eventProperties.*` to top-level columns with prefix `eventProperties.`
	"""
	if not hits:
		return pd.DataFrame()

	normalized = json_normalize(
		hits,
		sep=".",
	)
	# Keep only _index, _id, and _source.* columns
	cols = [c for c in normalized.columns if c == "_index" or c == "_id" or c.startswith("_source.")]
	df = normalized[cols].copy()

	# Strip the _source. prefix
	df.columns = [c.replace("_source.", "") if c.startswith("_source.") else c for c in df.columns]

	if flatten_event_properties:
		# json_normalize already flattens nested dicts with dot sep
		# This ensures eventProperties fields appear as "eventProperties.fieldName"
		pass

	return df


