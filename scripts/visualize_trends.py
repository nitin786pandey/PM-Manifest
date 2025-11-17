#!/usr/bin/env python3
"""
Visualize daily engagement trends and generate PDF/image reports.
"""

import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10


def load_analysis_data() -> Dict[str, Any]:
	"""Load analysis data by running the daily_engagement_average script."""
	script_path = Path(__file__).parent / "daily_engagement_average.py"
	result = subprocess.run(
		["python3", str(script_path)],
		cwd=str(script_path.parent),
		capture_output=True,
		text=True
	)
	
	# Extract JSON from output
	output_lines = result.stdout.split('\n')
	json_start = None
	for i, line in enumerate(output_lines):
		if line.strip().startswith('{'):
			json_start = i
			break
	
	if json_start is None:
		raise RuntimeError("Could not find JSON output from analysis script")
	
	json_str = '\n'.join(output_lines[json_start:])
	return json.loads(json_str)


def parse_date(date_str: str) -> datetime:
	"""Parse ISO date string to datetime."""
	# Handle both full ISO and date-only formats
	if 'T' in date_str:
		return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
	else:
		return datetime.fromisoformat(date_str)


def create_time_series_plot(data: Dict[str, Any], ax: plt.Axes) -> None:
	"""Create time series plot with moving averages and outliers."""
	trend = data.get('trend_analysis', {})
	daily_data = trend.get('enhanced_daily_data', [])
	
	if not daily_data:
		ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)
		return
	
	# Parse dates and values
	dates = [parse_date(day['date']) for day in daily_data]
	values = [day['sum_count'] for day in daily_data]
	ma7 = [day['moving_avg_7day'] for day in daily_data]
	ma14 = [day['moving_avg_14day'] for day in daily_data]
	
	# Get outliers
	outliers = trend.get('outliers', [])
	outlier_dates = {parse_date(out['date']): out['value'] for out in outliers}
	
	# Get statistics for mean line
	stats = trend.get('statistics', {})
	mean_val = stats.get('mean', 0)
	
	# Plot
	ax.plot(dates, values, 'o-', label='Daily Sum', linewidth=1.5, markersize=4, alpha=0.7, color='#2E86AB')
	ax.plot(dates, ma7, '-', label='7-Day Moving Average', linewidth=2, color='#A23B72', alpha=0.8)
	ax.plot(dates, ma14, '-', label='14-Day Moving Average', linewidth=2, color='#F18F01', alpha=0.8)
	ax.axhline(y=mean_val, color='gray', linestyle='--', linewidth=1.5, label=f'Mean ({mean_val:,.0f})', alpha=0.7)
	
	# Highlight outliers
	for out_date, out_value in outlier_dates.items():
		ax.plot(out_date, out_value, 'ro', markersize=12, markerfacecolor='red', 
		        markeredgecolor='darkred', markeredgewidth=2, zorder=5, label='Outlier' if out_date == list(outlier_dates.keys())[0] else '')
	
	# Highlight largest increases
	largest_inc = trend.get('largest_increases', [])
	if largest_inc:
		top_inc = largest_inc[0]
		top_date = parse_date(top_inc['date'])
		top_value = top_inc['current_value']
		ax.annotate(f'Largest Increase\n+{top_inc["percentage_change"]:.1f}%',
		           xy=(top_date, top_value), xytext=(10, 20),
		           textcoords='offset points', fontsize=9,
		           bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7),
		           arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
	
	ax.set_xlabel('Date', fontsize=12, fontweight='bold')
	ax.set_ylabel('Sum of eventProperties.count', fontsize=12, fontweight='bold')
	ax.set_title('Daily Engagement Trend with Moving Averages', fontsize=14, fontweight='bold', pad=20)
	ax.legend(loc='best', fontsize=9)
	ax.grid(True, alpha=0.3)
	
	# Format x-axis dates
	ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
	ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 10)))
	plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')


def create_day_over_day_plot(data: Dict[str, Any], ax: plt.Axes) -> None:
	"""Create day-over-day percentage change plot."""
	trend = data.get('trend_analysis', {})
	changes = trend.get('day_over_day_changes', [])
	
	if not changes:
		ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)
		return
	
	dates = [parse_date(change['date']) for change in changes]
	pct_changes = [change['percentage_change'] for change in changes]
	
	# Color bars based on positive/negative
	colors = ['#06A77D' if x >= 0 else '#D00000' for x in pct_changes]
	
	ax.bar(dates, pct_changes, color=colors, alpha=0.7, width=0.8)
	ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
	ax.axhline(y=15, color='orange', linestyle='--', linewidth=1, alpha=0.5, label='±15% threshold')
	ax.axhline(y=-15, color='orange', linestyle='--', linewidth=1, alpha=0.5)
	
	# Highlight largest changes
	largest_inc = trend.get('largest_increases', [])
	if largest_inc:
		top_inc = largest_inc[0]
		top_date = parse_date(top_inc['date'])
		top_pct = top_inc['percentage_change']
		ax.plot(top_date, top_pct, 'ro', markersize=10, zorder=5)
		ax.annotate(f'+{top_pct:.1f}%', xy=(top_date, top_pct),
		           xytext=(0, 15), textcoords='offset points',
		           fontsize=10, fontweight='bold', color='red',
		           bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
	
	ax.set_xlabel('Date', fontsize=12, fontweight='bold')
	ax.set_ylabel('Day-over-Day Change (%)', fontsize=12, fontweight='bold')
	ax.set_title('Day-over-Day Percentage Changes', fontsize=14, fontweight='bold', pad=20)
	ax.legend(loc='best', fontsize=9)
	ax.grid(True, alpha=0.3, axis='y')
	
	# Format x-axis dates
	ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
	ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 10)))
	plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')


def create_statistics_summary(data: Dict[str, Any], ax: plt.Axes) -> None:
	"""Create a text summary of statistics."""
	ax.axis('off')
	
	trend = data.get('trend_analysis', {})
	stats = trend.get('statistics', {})
	trend_info = trend.get('trend', {})
	
	summary_text = []
	summary_text.append("TREND ANALYSIS SUMMARY")
	summary_text.append("=" * 60)
	summary_text.append("")
	
	summary_text.append("Overall Statistics:")
	summary_text.append(f"  Mean: {stats.get('mean', 0):,.2f}")
	summary_text.append(f"  Median: {stats.get('median', 0):,.2f}")
	summary_text.append(f"  Std Deviation: {stats.get('std_deviation', 0):,.2f}")
	summary_text.append(f"  Min: {stats.get('min', 0):,.0f}")
	summary_text.append(f"  Max: {stats.get('max', 0):,.0f}")
	summary_text.append("")
	
	summary_text.append("Trend Direction:")
	summary_text.append(f"  Direction: {trend_info.get('direction', 'unknown')}")
	summary_text.append(f"  Strength: {trend_info.get('strength_per_day_pct', 0):.4f}% per day")
	summary_text.append(f"  Estimated change over period: {trend_info.get('estimated_change_over_period_pct', 0):.2f}%")
	summary_text.append("")
	
	largest_inc = trend.get('largest_increases', [])
	if largest_inc:
		summary_text.append("Top 3 Largest Increases:")
		for i, inc in enumerate(largest_inc[:3], 1):
			date = inc['date'][:10]
			summary_text.append(f"  {i}. {date}: {inc['percentage_change']:+.2f}% "
			                   f"({inc['previous_value']:,.0f} → {inc['current_value']:,.0f})")
		summary_text.append("")
	
	outliers = trend.get('outliers', [])
	if outliers:
		summary_text.append("Statistical Outliers (>2 std dev):")
		for i, out in enumerate(outliers[:5], 1):
			date = out['date'][:10]
			summary_text.append(f"  {i}. {date}: {out['value']:,.0f} "
			                   f"(z-score: {out['z_score']:.2f}, {out['deviation_pct']:+.2f}%)")
	
	text_content = '\n'.join(summary_text)
	ax.text(0.05, 0.95, text_content, transform=ax.transAxes,
	       fontsize=10, verticalalignment='top', fontfamily='monospace',
	       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))


def create_outlier_analysis(data: Dict[str, Any], ax: plt.Axes) -> None:
	"""Create a plot highlighting outliers with z-scores."""
	trend = data.get('trend_analysis', {})
	daily_data = trend.get('enhanced_daily_data', [])
	outliers = trend.get('outliers', [])
	
	if not daily_data:
		ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)
		return
	
	dates = [parse_date(day['date']) for day in daily_data]
	values = [day['sum_count'] for day in daily_data]
	stats = trend.get('statistics', {})
	mean_val = stats.get('mean', 0)
	std_dev = stats.get('std_deviation', 0)
	
	# Plot all points
	ax.scatter(dates, values, alpha=0.5, s=30, color='blue', label='Normal values', zorder=1)
	
	# Highlight outliers
	outlier_dict = {parse_date(out['date']): out for out in outliers}
	for out_date, out_info in outlier_dict.items():
		color = 'red' if out_info['z_score'] > 0 else 'darkred'
		ax.scatter(out_date, out_info['value'], s=200, color=color, 
		          edgecolors='black', linewidth=2, zorder=5,
		          label='High outlier' if out_info['z_score'] > 0 and out_date == list(outlier_dict.keys())[0] else '')
		ax.annotate(f"z={out_info['z_score']:.2f}\n{out_info['value']:,.0f}",
		           xy=(out_date, out_info['value']), xytext=(10, 20),
		           textcoords='offset points', fontsize=8, fontweight='bold',
		           bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.8),
		           arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
	
	# Add mean and std dev bands
	ax.axhline(y=mean_val, color='green', linestyle='-', linewidth=2, label=f'Mean ({mean_val:,.0f})', alpha=0.7)
	ax.axhline(y=mean_val + 2 * std_dev, color='orange', linestyle='--', linewidth=1.5, label='±2 Std Dev', alpha=0.6)
	ax.axhline(y=mean_val - 2 * std_dev, color='orange', linestyle='--', linewidth=1.5, alpha=0.6)
	ax.fill_between(dates, mean_val - 2 * std_dev, mean_val + 2 * std_dev, 
	                alpha=0.1, color='orange', label='Normal range')
	
	ax.set_xlabel('Date', fontsize=12, fontweight='bold')
	ax.set_ylabel('Sum of eventProperties.count', fontsize=12, fontweight='bold')
	ax.set_title('Outlier Detection Analysis', fontsize=14, fontweight='bold', pad=20)
	ax.legend(loc='best', fontsize=9)
	ax.grid(True, alpha=0.3)
	
	# Format x-axis dates
	ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
	ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 10)))
	plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')


def generate_visualization_report(
	output_dir: str = "output", 
	formats: List[str] = None,
	data: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
	"""
	Generate visualization report in multiple formats.
	
	Args:
		output_dir: Directory to save output files
		formats: List of formats to generate ('pdf', 'png', or both)
		data: Optional pre-computed analysis data. If None, will run analysis script.
	
	Returns:
		Dictionary with paths to generated files
	"""
	if formats is None:
		formats = ['pdf', 'png']
	
	# Create output directory
	output_path = Path(output_dir)
	output_path.mkdir(exist_ok=True)
	
	# Load data
	if data is None:
		print("Loading analysis data...")
		data = load_analysis_data()
	else:
		print("Using provided analysis data...")
	
	# Generate timestamp for filenames
	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
	
	output_files = {}
	
	# Create figures
	print("Generating visualizations...")
	
	if 'pdf' in formats:
		# Create PDF with multiple pages
		pdf_path = output_path / f"trend_analysis_report_{timestamp}.pdf"
		with PdfPages(str(pdf_path)) as pdf:
			# Page 1: Time series with moving averages
			fig1, ax1 = plt.subplots(figsize=(14, 8))
			create_time_series_plot(data, ax1)
			plt.tight_layout()
			pdf.savefig(fig1, bbox_inches='tight')
			plt.close(fig1)
			
			# Page 2: Day-over-day changes
			fig2, ax2 = plt.subplots(figsize=(14, 8))
			create_day_over_day_plot(data, ax2)
			plt.tight_layout()
			pdf.savefig(fig2, bbox_inches='tight')
			plt.close(fig2)
			
			# Page 3: Outlier analysis
			fig3, ax3 = plt.subplots(figsize=(14, 8))
			create_outlier_analysis(data, ax3)
			plt.tight_layout()
			pdf.savefig(fig3, bbox_inches='tight')
			plt.close(fig3)
			
			# Page 4: Statistics summary
			fig4, ax4 = plt.subplots(figsize=(14, 8))
			create_statistics_summary(data, ax4)
			plt.tight_layout()
			pdf.savefig(fig4, bbox_inches='tight')
			plt.close(fig4)
			
			# Add metadata
			d = pdf.infodict()
			d['Title'] = 'Daily Engagement Trend Analysis Report'
			d['Author'] = 'Trend Analysis Tool'
			d['Subject'] = 'Widget Engagement Trends'
			d['Keywords'] = 'trend analysis, engagement, analytics'
			d['CreationDate'] = datetime.now()
		
		output_files['pdf'] = str(pdf_path)
		print(f"PDF report saved: {pdf_path}")
	
	if 'png' in formats:
		# Create individual PNG images
		# Time series
		fig1, ax1 = plt.subplots(figsize=(14, 8))
		create_time_series_plot(data, ax1)
		plt.tight_layout()
		png1_path = output_path / f"time_series_{timestamp}.png"
		plt.savefig(png1_path, dpi=300, bbox_inches='tight')
		plt.close(fig1)
		output_files['time_series_png'] = str(png1_path)
		
		# Day-over-day
		fig2, ax2 = plt.subplots(figsize=(14, 8))
		create_day_over_day_plot(data, ax2)
		plt.tight_layout()
		png2_path = output_path / f"day_over_day_{timestamp}.png"
		plt.savefig(png2_path, dpi=300, bbox_inches='tight')
		plt.close(fig2)
		output_files['day_over_day_png'] = str(png2_path)
		
		# Outliers
		fig3, ax3 = plt.subplots(figsize=(14, 8))
		create_outlier_analysis(data, ax3)
		plt.tight_layout()
		png3_path = output_path / f"outliers_{timestamp}.png"
		plt.savefig(png3_path, dpi=300, bbox_inches='tight')
		plt.close(fig3)
		output_files['outliers_png'] = str(png3_path)
		
		# Summary
		fig4, ax4 = plt.subplots(figsize=(14, 8))
		create_statistics_summary(data, ax4)
		plt.tight_layout()
		png4_path = output_path / f"summary_{timestamp}.png"
		plt.savefig(png4_path, dpi=300, bbox_inches='tight')
		plt.close(fig4)
		output_files['summary_png'] = str(png4_path)
		
		print(f"PNG images saved in: {output_path}")
	
	return output_files


def main():
	parser = argparse.ArgumentParser(
		description="Generate visualization reports for daily engagement trends"
	)
	parser.add_argument(
		"--output-dir", "-o",
		type=str,
		default="output",
		help="Output directory for generated files (default: output)"
	)
	parser.add_argument(
		"--format", "-f",
		type=str,
		choices=['pdf', 'png', 'both'],
		default='both',
		help="Output format: pdf, png, or both (default: both)"
	)
	args = parser.parse_args()
	
	formats = ['pdf', 'png'] if args.format == 'both' else [args.format]
	
	try:
		output_files = generate_visualization_report(
			output_dir=args.output_dir,
			formats=formats
		)
		
		print("\n" + "="*80)
		print("VISUALIZATION REPORT GENERATED SUCCESSFULLY")
		print("="*80)
		for key, path in output_files.items():
			print(f"  {key}: {path}")
		print("="*80)
		
	except Exception as e:
		print(f"Error generating visualization: {e}")
		import traceback
		traceback.print_exc()
		return 1
	
	return 0


if __name__ == "__main__":
	exit(main())
