#!/usr/bin/env python3
"""
Query daily sum of eventProperties.count for widgetVisitedSession events
filtered by "Lotus" widget for the last 60 days.
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Dict, Any, List

from es_fetch import (
	ElasticsearchConfig,
	base_bool_query,
	build_date_range_query,
	search,
)
from agent_runner import detect_counter_event


def list_available_widgets(cfg: ElasticsearchConfig, gte: str, lte: str, indices: str = None):
	"""List available widget names/identifiers to help find the correct field."""
	filters = [
		build_date_range_query(gte=gte, lte=lte),
		{"term": {"eventName.keyword": "widgetVisitedSession"}},
	]
	dsl = {
		"size": 0,
		"track_total_hits": True,
		"query": base_bool_query(filters),
		"aggs": {
			"by_store": {
				"terms": {"field": "storeId.keyword", "size": 20}
			}
		}
	}
	try:
		resp = search(cfg, dsl, indices=indices)
		buckets = resp.get("aggregations", {}).get("by_store", {}).get("buckets", [])
		store_ids = [b["key"] for b in buckets[:10]]
		print(f"Sample storeIds with widgetVisitedSession events: {store_ids}", file=sys.stderr)
	except Exception as e:
		print(f"Could not list stores: {e}", file=sys.stderr)


def discover_widget_name_field(cfg: ElasticsearchConfig, gte: str, lte: str, indices: str = None) -> str:
	"""
	Discover the correct field name for widget name by sampling widgetVisitedSession events.
	Returns the field path that contains "Lotus" value.
	"""
	# Sample a few documents to find the widget name field
	filters = [
		build_date_range_query(gte=gte, lte=lte),
		{"term": {"eventName.keyword": "widgetVisitedSession"}},
	]
	dsl = {
		"size": 100,
		"track_total_hits": True,
		"query": base_bool_query(filters),
		"sort": [{"createdAt": {"order": "desc"}}],
	}
	
	try:
		resp = search(cfg, dsl, indices=indices)
		hits = resp.get("hits", {}).get("hits", [])
		
		if not hits:
			print("Warning: No widgetVisitedSession events found. Using default field name.", file=sys.stderr)
			return "eventProperties.widgetName"
		
		# Try common field names
		candidate_fields = [
			"eventProperties.widgetName",
			"eventProperties.widget",
			"widgetName",
			"widget",
		]
		
		# Also check all keys in eventProperties to find potential widget-related fields
		all_event_prop_keys = set()
		for hit in hits[:10]:  # Check first 10 hits
			event_props = hit.get("_source", {}).get("eventProperties", {}) or {}
			all_event_prop_keys.update(event_props.keys())
		
		# Look for fields that might contain "Lotus"
		for hit in hits:
			source = hit.get("_source", {})
			event_props = source.get("eventProperties", {}) or {}
			
			# Check all eventProperties keys for "Lotus" value (case-insensitive)
			for key, value in event_props.items():
				if isinstance(value, str) and value.lower() == "lotus":
					return f"eventProperties.{key}"
				if value == "Lotus":
					return f"eventProperties.{key}"
			
			# Check candidate fields (case-insensitive)
			for field in candidate_fields:
				if "." in field:
					parts = field.split(".")
					value = source
					for part in parts:
						if isinstance(value, dict):
							value = value.get(part)
						else:
							value = None
							break
				else:
					value = source.get(field) or event_props.get(field)
				
				if isinstance(value, str) and value.lower() == "lotus":
					return field
				if value == "Lotus":
					return field
			
			# Also check top-level fields like eventSource
			for top_key in ["eventSource", "widgetType", "widgetName"]:
				top_value = source.get(top_key)
				if isinstance(top_value, str) and top_value.lower() == "lotus":
					return top_key
				if top_value == "Lotus":
					return top_key
		
		# If not found, check the full document structure
		print(f"Warning: 'Lotus' not found in sample. Available eventProperties keys: {sorted(all_event_prop_keys)[:20]}", file=sys.stderr)
		list_available_widgets(cfg, gte, lte, indices)
		
		# Print a sample document structure for debugging
		if hits:
			sample = hits[0].get("_source", {})
			print(f"Sample document top-level keys: {sorted(sample.keys())[:20]}", file=sys.stderr)
			# Search for "Lotus" anywhere in the document (case-insensitive)
			import json as json_module
			sample_str = json_module.dumps(sample, indent=2)
			if "lotus" in sample_str.lower():
				print("Found 'lotus' (case-insensitive) in sample document. Checking structure...", file=sys.stderr)
				# Try to find it recursively
				def find_lotus(obj, path=""):
					if isinstance(obj, dict):
						for k, v in obj.items():
							if isinstance(v, str) and "lotus" in v.lower():
								return f"{path}.{k}" if path else k
							result = find_lotus(v, f"{path}.{k}" if path else k)
							if result:
								return result
					elif isinstance(obj, list):
						for i, item in enumerate(obj):
							result = find_lotus(item, f"{path}[{i}]")
							if result:
								return result
					return None
				
				lotus_path = find_lotus(sample)
				if lotus_path:
					print(f"Found 'Lotus' at path: {lotus_path}", file=sys.stderr)
					# Convert to Elasticsearch field path format
					if lotus_path.startswith("eventProperties."):
						return lotus_path
					else:
						return f"eventProperties.{lotus_path}" if not lotus_path.startswith("eventProperties") else lotus_path
		
		return "eventProperties.widgetName"
	except Exception as e:
		print(f"Warning: Error discovering widget field: {e}. Using default.", file=sys.stderr)
		# Default fallback
		return "eventProperties.widgetName"


def build_lotus_widget_daily_dsl(
	gte: str,
	lte: str,
	use_sum_count: bool,
	widget_name_field: str = "eventProperties.widgetName",
	widget_value: str = "Lotus",
) -> Dict[str, Any]:
	"""
	Build DSL for daily aggregation of widgetVisitedSession events for Lotus widget.
	"""
	filters = [
		build_date_range_query(gte=gte, lte=lte),
		{"term": {"eventName.keyword": "widgetVisitedSession"}},
	]
	
	# Build widget name filter based on field structure
	if widget_name_field.startswith("eventProperties."):
		# Nested field in eventProperties
		filters.append({"term": {f"{widget_name_field}.keyword": widget_value}})
	else:
		# Top-level field
		filters.append({"term": {f"{widget_name_field}.keyword": widget_value}})
	
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
	"""Extract daily series from aggregation response."""
	buckets = resp.get("aggregations", {}).get("by_day", {}).get("buckets", []) or []
	series: List[Dict[str, Any]] = []
	for b in buckets:
		value = float(b.get("total", {}).get("value", 0.0)) if use_sum_count else float(b.get("doc_count", 0))
		date_key = b.get("key_as_string") or b.get("key")
		# Convert timestamp to date string if needed
		if isinstance(date_key, int):
			date_key = datetime.fromtimestamp(date_key / 1000).strftime("%Y-%m-%d")
		series.append({"date": date_key, "count": value})
	return series


def lotus_widget_daily_count(
	cfg: ElasticsearchConfig,
	gte: str,
	lte: str,
	indices: str = None,
	widget_field: str = None,
	widget_value: str = "Lotus",
) -> List[Dict[str, Any]]:
	"""
	Get daily sum of eventProperties.count for widgetVisitedSession events for Lotus widget.
	"""
	# Discover the widget name field if not provided
	if widget_field:
		widget_name_field = widget_field
		print(f"Using provided widget field: {widget_field}", file=sys.stderr)
	else:
		widget_name_field = discover_widget_name_field(cfg, gte, lte, indices)
	
	# First detect if this is a counter event
	is_counter = detect_counter_event(
		cfg,
		event_name="widgetVisitedSession",
		gte=gte,
		lte=lte,
		store_id=None,
		indices=indices,
	)
	
	# Try multiple query strategies
	strategies = [
		# Strategy 1: Use discovered/provided field
		lambda: build_lotus_widget_daily_dsl(gte, lte, is_counter, widget_name_field, widget_value),
		# Strategy 2: Try storeId (maybe widget_value is a store identifier)
		lambda: build_lotus_widget_daily_dsl_with_store(cfg, gte, lte, is_counter, widget_value, indices),
	]
	
	# Only try strategy 3 (no filter) if widget_field was not explicitly provided
	if not widget_field:
		strategies.append(lambda: build_all_widget_daily_dsl(gte, lte, is_counter))
	
	for i, build_dsl in enumerate(strategies):
		try:
			dsl = build_dsl()
			resp = search(cfg, dsl, indices=indices)
			series = extract_daily_series(resp, use_sum_count=is_counter)
			if series and any(row["count"] > 0 for row in series):
				if i == 2:  # Strategy 3 - no filter
					print("Warning: No Lotus filter found, returning all widgetVisitedSession events", file=sys.stderr)
				return series
		except Exception as e:
			if i < len(strategies) - 1:
				continue
			raise
	
	return []


def build_lotus_widget_daily_dsl_with_store(
	cfg: ElasticsearchConfig,
	gte: str,
	lte: str,
	use_sum_count: bool,
	store_identifier: str,
	indices: str = None,
) -> Dict[str, Any]:
	"""Try filtering by storeId in case 'Lotus' is a store identifier."""
	filters = [
		build_date_range_query(gte=gte, lte=lte),
		{"term": {"eventName.keyword": "widgetVisitedSession"}},
		{"term": {"storeId.keyword": store_identifier}},
	]
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


def build_all_widget_daily_dsl(
	gte: str,
	lte: str,
	use_sum_count: bool,
) -> Dict[str, Any]:
	"""Build DSL without widget filter (for testing)."""
	filters = [
		build_date_range_query(gte=gte, lte=lte),
		{"term": {"eventName.keyword": "widgetVisitedSession"}},
	]
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


def print_table(data: List[Dict[str, Any]]):
	"""Print data as a formatted table."""
	if not data:
		print("No data found.")
		return
	
	# Print header
	print(f"{'Date':<12} {'Count':>15}")
	print("-" * 28)
	
	# Print rows
	total = 0.0
	for row in sorted(data, key=lambda x: x["date"]):
		date = row["date"]
		count = row["count"]
		total += count
		print(f"{date:<12} {count:>15,.0f}")
	
	# Print total
	print("-" * 28)
	print(f"{'Total':<12} {total:>15,.0f}")


def main():
	parser = argparse.ArgumentParser(
		description="Get daily sum of eventProperties.count for widgetVisitedSession events for Lotus widget"
	)
	parser.add_argument("--gte", type=str, default="now-60d/d", help="Start time (Elasticsearch format)")
	parser.add_argument("--lte", type=str, default="now", help="End time (Elasticsearch format)")
	parser.add_argument("--indices", type=str, default=None, help="Override indices")
	parser.add_argument("--json", action="store_true", help="Output as JSON instead of table")
	parser.add_argument("--widget-field", type=str, default=None, help="Override widget name field (e.g., 'eventProperties.widgetName' or 'storeId')")
	parser.add_argument("--widget-value", type=str, default="Lotus", help="Widget name/value to filter by (default: 'Lotus')")
	args = parser.parse_args()

	try:
		cfg = ElasticsearchConfig.from_env()
		if args.indices:
			cfg.indices = args.indices
	except RuntimeError as e:
		print(f"Error: {e}", file=sys.stderr)
		sys.exit(1)

	try:
		print(f"Querying widgetVisitedSession events for '{args.widget_value}' widget from {args.gte} to {args.lte}...", file=sys.stderr)
		results = lotus_widget_daily_count(
			cfg=cfg,
			gte=args.gte,
			lte=args.lte,
			indices=cfg.indices,
			widget_field=args.widget_field,
			widget_value=args.widget_value,
		)
		
		if args.json:
			print(json.dumps(results, indent=2))
		else:
			print_table(results)
	except Exception as e:
		print(f"Error: {e}", file=sys.stderr)
		import traceback
		traceback.print_exc()
		sys.exit(1)


if __name__ == "__main__":
	main()
