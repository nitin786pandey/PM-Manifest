#!/usr/bin/env python3
"""
Simple wrapper to generate trend analysis reports with visualizations.
This script combines data analysis and visualization in one command.
"""

import argparse
import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

from visualize_trends import generate_visualization_report


def main():
	parser = argparse.ArgumentParser(
		description="Generate comprehensive trend analysis report with visualizations",
		formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog="""
Examples:
  # Generate PDF and PNG reports
  python3 generate_trend_report.py
  
  # Generate only PDF
  python3 generate_trend_report.py --format pdf
  
  # Generate only PNG images
  python3 generate_trend_report.py --format png
  
  # Custom output directory
  python3 generate_trend_report.py --output-dir reports
		"""
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
	
	print("="*80)
	print("TREND ANALYSIS REPORT GENERATOR")
	print("="*80)
	print()
	
	formats = ['pdf', 'png'] if args.format == 'both' else [args.format]
	
	try:
		output_files = generate_visualization_report(
			output_dir=args.output_dir,
			formats=formats
		)
		
		print()
		print("="*80)
		print("REPORT GENERATION COMPLETE")
		print("="*80)
		print()
		print("Generated files:")
		for key, path in sorted(output_files.items()):
			file_path = Path(path)
			size_mb = file_path.stat().st_size / (1024 * 1024) if file_path.exists() else 0
			print(f"  • {key:20s} : {path} ({size_mb:.2f} MB)")
		print()
		print("="*80)
		
		# Print summary
		if 'pdf' in output_files:
			print(f"\n📄 PDF Report: {output_files['pdf']}")
		if 'time_series_png' in output_files:
			print(f"\n📊 Visualizations saved as PNG images in: {args.output_dir}/")
		
		return 0
		
	except Exception as e:
		print(f"\n❌ Error generating report: {e}")
		import traceback
		traceback.print_exc()
		return 1


if __name__ == "__main__":
	sys.exit(main())
