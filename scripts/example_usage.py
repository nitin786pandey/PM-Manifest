#!/usr/bin/env python3
"""
Example usage of the trend visualization tool.
"""

from visualize_trends import generate_visualization_report
from daily_engagement_average import run_daily_engagement_analysis, ElasticsearchConfig


def example_1_simple_usage():
	"""Example 1: Simple usage - generate reports with default settings."""
	print("Example 1: Generating reports with default settings...")
	
	output_files = generate_visualization_report(
		output_dir="output",
		formats=['pdf', 'png']
	)
	
	print("\nGenerated files:")
	for key, path in output_files.items():
		print(f"  {key}: {path}")


def example_2_custom_data():
	"""Example 2: Use custom analysis data."""
	print("\nExample 2: Using custom analysis data...")
	
	# Run your own analysis
	cfg = ElasticsearchConfig.from_env()
	data = run_daily_engagement_analysis(
		cfg=cfg,
		event_name="widgetVisitedSession",
		event_identifiers=[
			"DISENGAGED_ON_THE_PRODUCT_PAGE",
			"PRODUCT_ADD_TO_CART",
			"HOME_PAGE_WELCOME_MESSAGE",
			"PRODUCT_HISTORY_RECOMMENDATION",
			"PRODUCT_REMOVE_FROM_CART",
		],
		gte="now-60d/d",
		lte="now",
		store_id=None,
		indices=None,
	)
	
	# Generate visualizations with custom data
	output_files = generate_visualization_report(
		output_dir="output",
		formats=['pdf'],
		data=data
	)
	
	print("\nGenerated files:")
	for key, path in output_files.items():
		print(f"  {key}: {path}")


def example_3_pdf_only():
	"""Example 3: Generate only PDF report."""
	print("\nExample 3: Generating PDF-only report...")
	
	output_files = generate_visualization_report(
		output_dir="output",
		formats=['pdf']
	)
	
	print(f"\nPDF report: {output_files.get('pdf', 'Not generated')}")


if __name__ == "__main__":
	print("="*80)
	print("TREND VISUALIZATION - USAGE EXAMPLES")
	print("="*80)
	
	try:
		example_1_simple_usage()
		# Uncomment to run other examples:
		# example_2_custom_data()
		# example_3_pdf_only()
		
	except Exception as e:
		print(f"\nError: {e}")
		import traceback
		traceback.print_exc()
