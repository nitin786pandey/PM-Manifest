#!/usr/bin/env python3
"""
Calculate daily average of sum of eventProperties.count for widgetVisitedSession events
with specific eventIdentifiers over the last 60 days.
"""

import argparse
import json
import os
from typing import Any, Dict, List, Optional

from es_fetch import ElasticsearchConfig, base_bool_query, build_date_range_query, search


def build_daily_engagement_dsl(
	gte: str,
	lte: str,
	event_name: str,
	event_identifiers: List[str],
	store_id: Optional[str] = None,
) -> Dict[str, Any]:
	"""
	Build DSL query to:
	1. Filter by eventName and eventIdentifiers
	2. Group by day using date_histogram
	3. Sum eventProperties.count per day
	"""
	filters = [
		build_date_range_query(gte=gte, lte=lte),
		{"term": {"eventName.keyword": event_name}},
		{"terms": {"eventProperties.eventIdentifier.keyword": event_identifiers}},
	]
	if store_id:
		filters.append({"term": {"storeId.keyword": store_id}})
	
	query = base_bool_query(filters)
	
	return {
		"track_total_hits": True,
		"size": 0,
		"query": query,
		"aggs": {
			"by_day": {
				"date_histogram": {
					"field": "createdAt",
					"calendar_interval": "day",
					"min_doc_count": 0,
				},
				"aggs": {
					"total_count": {
						"sum": {"field": "eventProperties.count"}
					}
				}
			}
		}
	}


def extract_daily_sums(resp: Dict[str, Any]) -> List[Dict[str, Any]]:
	"""Extract daily sums from aggregation response."""
	buckets = resp.get("aggregations", {}).get("by_day", {}).get("buckets", []) or []
	daily_sums: List[Dict[str, Any]] = []
	for bucket in buckets:
		date = bucket.get("key_as_string") or bucket.get("key")
		total_count = float(bucket.get("total_count", {}).get("value", 0.0) or 0.0)
		daily_sums.append({
			"date": date,
			"sum_count": total_count
		})
	return daily_sums


def calculate_daily_average(daily_sums: List[Dict[str, Any]]) -> float:
	"""Calculate the average of daily sums."""
	if not daily_sums:
		return 0.0
	total = sum(day["sum_count"] for day in daily_sums)
	return total / len(daily_sums)


def run_daily_engagement_analysis(
	cfg: ElasticsearchConfig,
	event_name: str,
	event_identifiers: List[str],
	gte: str,
	lte: str,
	store_id: Optional[str] = None,
	indices: Optional[str] = None,
) -> Dict[str, Any]:
	"""
	Calculate daily average of sum of eventProperties.count for specified events.
	"""
	dsl = build_daily_engagement_dsl(
		gte=gte,
		lte=lte,
		event_name=event_name,
		event_identifiers=event_identifiers,
		store_id=store_id,
	)
	
	resp = search(cfg, dsl, indices=indices)
	daily_sums = extract_daily_sums(resp)
	daily_avg = calculate_daily_average(daily_sums)
	
	# Calculate total sum for reference
	total_sum = sum(day["sum_count"] for day in daily_sums)
	
	return {
		"daily_average": daily_avg,
		"total_sum": total_sum,
		"number_of_days": len(daily_sums),
		"daily_breakdown": daily_sums,
		"query_params": {
			"event_name": event_name,
			"event_identifiers": event_identifiers,
			"date_range": {"gte": gte, "lte": lte},
			"store_id": store_id,
		}
	}


def main() -> None:
	parser = argparse.ArgumentParser(
		description="Calculate daily average of sum of eventProperties.count for widgetVisitedSession events"
	)
	parser.add_argument("--gte", type=str, default="now-60d/d", help="Start time (Elasticsearch format)")
	parser.add_argument("--lte", type=str, default="now", help="End time (Elasticsearch format)")
	parser.add_argument("--indices", type=str, default=None, help="Override indices")
	parser.add_argument("--store-id", type=str, default=None, help="Filter by storeId (exact match)")
	args = parser.parse_args()

	cfg = ElasticsearchConfig.from_env()
	if args.indices:
		cfg.indices = args.indices

	# Event identifiers to filter
	event_identifiers = [
		"DISENGAGED_ON_THE_PRODUCT_PAGE",
		"PRODUCT_ADD_TO_CART",
		"HOME_PAGE_WELCOME_MESSAGE",
		"PRODUCT_HISTORY_RECOMMENDATION",
		"PRODUCT_REMOVE_FROM_CART",
	]

	result = run_daily_engagement_analysis(
		cfg=cfg,
		event_name="widgetVisitedSession",
		event_identifiers=event_identifiers,
		gte=args.gte,
		lte=args.lte,
		store_id=args.store_id,
		indices=cfg.indices,
	)

	print(json.dumps(result, indent=2))


if __name__ == "__main__":
	main()
