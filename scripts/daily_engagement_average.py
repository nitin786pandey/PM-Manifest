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


def calculate_trend_analysis(daily_sums: List[Dict[str, Any]]) -> Dict[str, Any]:
	"""
	Analyze day-by-day trends and detect substantial changes.
	Returns trend metrics, day-over-day changes, and anomaly detection.
	"""
	if len(daily_sums) < 2:
		return {"error": "Need at least 2 days of data for trend analysis"}
	
	# Sort by date to ensure chronological order
	sorted_days = sorted(daily_sums, key=lambda x: x["date"])
	values = [day["sum_count"] for day in sorted_days]
	
	# Calculate day-over-day changes
	day_over_day_changes = []
	for i in range(1, len(sorted_days)):
		prev_value = sorted_days[i - 1]["sum_count"]
		curr_value = sorted_days[i]["sum_count"]
		if prev_value == 0:
			pct_change = 0.0
		else:
			pct_change = ((curr_value - prev_value) / prev_value) * 100.0
		
		day_over_day_changes.append({
			"date": sorted_days[i]["date"],
			"previous_date": sorted_days[i - 1]["date"],
			"current_value": curr_value,
			"previous_value": prev_value,
			"absolute_change": curr_value - prev_value,
			"percentage_change": pct_change,
		})
	
	# Calculate moving averages (7-day and 14-day)
	moving_avg_7 = []
	moving_avg_14 = []
	for i in range(len(values)):
		start_7 = max(0, i - 6)
		start_14 = max(0, i - 13)
		avg_7 = sum(values[start_7:i + 1]) / (i - start_7 + 1) if i >= 0 else values[i]
		avg_14 = sum(values[start_14:i + 1]) / (i - start_14 + 1) if i >= 0 else values[i]
		moving_avg_7.append(avg_7)
		moving_avg_14.append(avg_14)
	
	# Calculate statistics
	mean = sum(values) / len(values)
	variance = sum((x - mean) ** 2 for x in values) / len(values)
	std_dev = variance ** 0.5
	
	# Detect outliers using z-scores (values > 2 standard deviations from mean)
	outliers = []
	for i, day in enumerate(sorted_days):
		z_score = (day["sum_count"] - mean) / std_dev if std_dev > 0 else 0
		if abs(z_score) > 2.0:
			outliers.append({
				"date": day["date"],
				"value": day["sum_count"],
				"z_score": z_score,
				"deviation_from_mean": day["sum_count"] - mean,
				"deviation_pct": ((day["sum_count"] - mean) / mean * 100.0) if mean > 0 else 0.0,
			})
	
	# Find largest increases
	largest_increases = sorted(
		day_over_day_changes,
		key=lambda x: x["percentage_change"],
		reverse=True
	)[:5]
	
	# Find largest decreases
	largest_decreases = sorted(
		day_over_day_changes,
		key=lambda x: x["percentage_change"]
	)[:5]
	
	# Detect trend breaks (when 7-day moving average shifts significantly)
	trend_breaks = []
	for i in range(7, len(sorted_days)):
		# Compare current 7-day avg with previous 7-day avg
		prev_avg = sum(values[i - 7:i]) / 7
		curr_avg = sum(values[i - 6:i + 1]) / 7
		if prev_avg > 0:
			shift_pct = ((curr_avg - prev_avg) / prev_avg) * 100.0
			# Flag if shift is > 15%
			if abs(shift_pct) > 15.0:
				trend_breaks.append({
					"date": sorted_days[i]["date"],
					"previous_7day_avg": prev_avg,
					"current_7day_avg": curr_avg,
					"shift_percentage": shift_pct,
					"shift_type": "increase" if shift_pct > 0 else "decrease",
				})
	
	# Calculate overall trend (linear regression slope)
	n = len(values)
	if n > 1:
		x = list(range(n))
		sum_x = sum(x)
		sum_y = sum(values)
		sum_xy = sum(x[i] * values[i] for i in range(n))
		sum_x2 = sum(xi * xi for xi in x)
		
		slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if (n * sum_x2 - sum_x * sum_x) != 0 else 0
		
		# Calculate trend direction and strength
		trend_direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"
		trend_strength = abs(slope) / mean * 100 if mean > 0 else 0  # Percentage change per day
	else:
		slope = 0
		trend_direction = "insufficient_data"
		trend_strength = 0
	
	# Add moving averages to daily data
	enhanced_daily_data = []
	for i, day in enumerate(sorted_days):
		enhanced_daily_data.append({
			"date": day["date"],
			"sum_count": day["sum_count"],
			"moving_avg_7day": moving_avg_7[i],
			"moving_avg_14day": moving_avg_14[i],
		})
	
	return {
		"statistics": {
			"mean": mean,
			"median": sorted(values)[len(values) // 2] if values else 0,
			"std_deviation": std_dev,
			"min": min(values),
			"max": max(values),
			"range": max(values) - min(values),
		},
		"trend": {
			"direction": trend_direction,
			"slope": slope,
			"strength_per_day_pct": trend_strength,
			"estimated_change_over_period": slope * (n - 1),
			"estimated_change_over_period_pct": (slope * (n - 1) / mean * 100) if mean > 0 else 0,
		},
		"day_over_day_changes": day_over_day_changes,
		"enhanced_daily_data": enhanced_daily_data,
		"outliers": outliers,
		"largest_increases": largest_increases,
		"largest_decreases": largest_decreases,
		"trend_breaks": trend_breaks,
	}


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
	
	# Perform trend analysis
	trend_analysis = calculate_trend_analysis(daily_sums)
	
	return {
		"daily_average": daily_avg,
		"total_sum": total_sum,
		"number_of_days": len(daily_sums),
		"daily_breakdown": daily_sums,
		"trend_analysis": trend_analysis,
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

	# Print summary of key findings
	if "trend_analysis" in result:
		trend = result["trend_analysis"]
		print("\n" + "="*80)
		print("TREND ANALYSIS SUMMARY")
		print("="*80)
		
		if "statistics" in trend:
			stats = trend["statistics"]
			print(f"\nOverall Statistics:")
			print(f"  Mean: {stats['mean']:,.2f}")
			print(f"  Median: {stats['median']:,.2f}")
			print(f"  Std Deviation: {stats['std_deviation']:,.2f}")
			print(f"  Range: {stats['min']:,.2f} to {stats['max']:,.2f}")
		
		if "trend" in trend:
			trend_info = trend["trend"]
			print(f"\nOverall Trend:")
			print(f"  Direction: {trend_info['direction']}")
			print(f"  Strength: {trend_info['strength_per_day_pct']:.4f}% per day")
			print(f"  Estimated change over period: {trend_info['estimated_change_over_period_pct']:.2f}%")
		
		if "largest_increases" in trend and trend["largest_increases"]:
			print(f"\nTop 5 Largest Day-over-Day Increases:")
			for i, inc in enumerate(trend["largest_increases"], 1):
				print(f"  {i}. {inc['date']}: {inc['percentage_change']:+.2f}% "
				      f"({inc['previous_value']:,.0f} → {inc['current_value']:,.0f})")
		
		if "trend_breaks" in trend and trend["trend_breaks"]:
			print(f"\nSignificant Trend Breaks (7-day moving average shifts >15%):")
			for i, break_info in enumerate(trend["trend_breaks"], 1):
				print(f"  {i}. {break_info['date']}: {break_info['shift_type']} of {break_info['shift_percentage']:+.2f}% "
				      f"({break_info['previous_7day_avg']:,.0f} → {break_info['current_7day_avg']:,.0f})")
		
		if "outliers" in trend and trend["outliers"]:
			print(f"\nOutliers (values >2 standard deviations from mean):")
			for i, outlier in enumerate(trend["outliers"], 1):
				print(f"  {i}. {outlier['date']}: {outlier['value']:,.0f} "
				      f"(z-score: {outlier['z_score']:.2f}, deviation: {outlier['deviation_pct']:+.2f}%)")
		
		print("\n" + "="*80 + "\n")
	
	# Print full JSON output
	print(json.dumps(result, indent=2))


if __name__ == "__main__":
	main()
