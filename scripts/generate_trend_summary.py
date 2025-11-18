#!/usr/bin/env python3
"""
Generate a summary report from the trend analysis results.
"""

import json
import subprocess
import sys


def main():
    # Run the analysis script and capture output
    result = subprocess.run(
        ["python3", "daily_engagement_average.py"],
        cwd="/workspace/scripts",
        capture_output=True,
        text=True
    )
    
    # Extract JSON from output (it's at the end after the summary)
    output_lines = result.stdout.split('\n')
    json_start = None
    for i, line in enumerate(output_lines):
        if line.strip().startswith('{'):
            json_start = i
            break
    
    if json_start is None:
        print("Error: Could not find JSON output")
        sys.exit(1)
    
    # Parse JSON
    json_str = '\n'.join(output_lines[json_start:])
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        sys.exit(1)
    
    trend = data.get('trend_analysis', {})
    
    # Generate summary
    print('='*80)
    print('TREND ANALYSIS - KEY FINDINGS')
    print('='*80)
    print()
    print('OVERALL TREND:')
    trend_info = trend.get('trend', {})
    print(f'  Direction: {trend_info.get("direction", "unknown")}')
    print(f'  Estimated change over 60 days: {trend_info.get("estimated_change_over_period_pct", 0):.2f}%')
    print()
    
    stats = trend.get('statistics', {})
    print('STATISTICS:')
    print(f'  Mean: {stats.get("mean", 0):,.2f}')
    print(f'  Median: {stats.get("median", 0):,.2f}')
    print(f'  Std Deviation: {stats.get("std_deviation", 0):,.2f}')
    print(f'  Range: {stats.get("min", 0):,.0f} to {stats.get("max", 0):,.0f}')
    print()
    
    print('SUBSTANTIAL INCREASES DETECTED:')
    print('  The following dates show significant day-over-day increases:')
    for i, inc in enumerate(trend.get('largest_increases', [])[:5], 1):
        date = inc['date'][:10]
        print(f'  {i}. {date}: {inc["percentage_change"]:+.2f}% increase')
        print(f'     ({inc["previous_value"]:,.0f} → {inc["current_value"]:,.0f})')
    print()
    
    print('OUTLIERS (Statistical Anomalies >2 std dev from mean):')
    outliers = trend.get('outliers', [])
    if outliers:
        for i, out in enumerate(outliers, 1):
            date = out['date'][:10]
            print(f'  {i}. {date}: {out["value"]:,.0f} (z-score: {out["z_score"]:.2f}, {out["deviation_pct"]:+.2f}% from mean)')
    else:
        print('  No outliers detected')
    print()
    
    print('='*80)
    print()
    print('KEY INSIGHT:')
    largest_inc = trend.get('largest_increases', [])
    if largest_inc:
        top_inc = largest_inc[0]
        date = top_inc['date'][:10]
        print(f'  The most significant change occurred on {date} with a')
        print(f'  {top_inc["percentage_change"]:.2f}% day-over-day increase')
        print(f'  ({top_inc["previous_value"]:,.0f} → {top_inc["current_value"]:,.0f}).')
        print()
        print('  This spike suggests a substantial change occurred around this time,')
        print('  such as:')
        print('    - A product launch or feature release')
        print('    - A marketing campaign or promotion')
        print('    - A system configuration change')
        print('    - A change in user behavior patterns')
    print()


if __name__ == "__main__":
    main()
