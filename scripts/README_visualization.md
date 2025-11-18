# Trend Analysis Visualization Tool

This tool generates comprehensive visualizations and reports for daily engagement trend analysis.

## Features

- **Time Series Analysis**: Daily trends with 7-day and 14-day moving averages
- **Day-over-Day Changes**: Percentage change analysis with highlighted spikes
- **Outlier Detection**: Statistical outlier identification with z-scores
- **Summary Statistics**: Key metrics and insights
- **Multiple Formats**: PDF reports and high-resolution PNG images

## Usage

### Command Line

#### Generate both PDF and PNG reports:
```bash
cd /workspace/scripts
python3 generate_trend_report.py
```

#### Generate only PDF:
```bash
python3 generate_trend_report.py --format pdf
```

#### Generate only PNG images:
```bash
python3 generate_trend_report.py --format png
```

#### Custom output directory:
```bash
python3 generate_trend_report.py --output-dir reports
```

### Direct Visualization Script

You can also use the visualization script directly:

```bash
python3 visualize_trends.py --format both --output-dir output
```

## Output Files

### PDF Report
- **File**: `trend_analysis_report_YYYYMMDD_HHMMSS.pdf`
- **Contents**: Multi-page PDF with all visualizations
  - Page 1: Time series with moving averages
  - Page 2: Day-over-day percentage changes
  - Page 3: Outlier analysis
  - Page 4: Statistics summary

### PNG Images
- **time_series_YYYYMMDD_HHMMSS.png**: Daily trend with moving averages
- **day_over_day_YYYYMMDD_HHMMSS.png**: Day-over-day changes
- **outliers_YYYYMMDD_HHMMSS.png**: Outlier detection visualization
- **summary_YYYYMMDD_HHMMSS.png**: Text summary of statistics

All PNG images are generated at 300 DPI for high-quality printing and presentation.

## Programmatic Usage

You can also import and use the visualization functions programmatically:

```python
from scripts.visualize_trends import generate_visualization_report

# Generate reports
output_files = generate_visualization_report(
    output_dir="reports",
    formats=['pdf', 'png']
)

# Access generated file paths
print(f"PDF: {output_files['pdf']}")
print(f"Time series PNG: {output_files['time_series_png']}")
```

## Visualizations Explained

### 1. Time Series Plot
- Shows daily engagement values over time
- Includes 7-day and 14-day moving averages to smooth out noise
- Highlights statistical outliers in red
- Annotates the largest increase with details
- Includes mean line for reference

### 2. Day-over-Day Changes
- Bar chart showing percentage change from previous day
- Green bars for increases, red for decreases
- Highlights changes exceeding ±15% threshold
- Annotates the largest increase

### 3. Outlier Analysis
- Scatter plot of all daily values
- Highlights outliers (>2 standard deviations from mean)
- Shows z-scores and values for each outlier
- Includes mean and ±2 standard deviation bands

### 4. Statistics Summary
- Text-based summary of key metrics
- Overall statistics (mean, median, std dev, min, max)
- Trend direction and strength
- Top increases and outliers

## Dependencies

- `matplotlib`: For plotting and PDF generation
- `seaborn`: For enhanced styling
- `pandas`: For data handling (via daily_engagement_average.py)
- `requests`: For Elasticsearch queries (via daily_engagement_average.py)

## Requirements

- Python 3.9+
- Elasticsearch credentials (ELASTIC_BASE_URL and ELASTIC_API_KEY)
- Access to the analysis script (`daily_engagement_average.py`)

## Integration

The visualization tool automatically:
1. Runs the `daily_engagement_average.py` script to fetch and analyze data
2. Extracts the JSON results
3. Generates visualizations based on the analysis
4. Exports in the requested formats

## Customization

To customize visualizations, edit `visualize_trends.py`:
- Modify colors in the plotting functions
- Adjust figure sizes in `plt.rcParams`
- Change outlier detection thresholds
- Add additional charts or analysis

## Troubleshooting

**Error: "Could not find JSON output"**
- Ensure `daily_engagement_average.py` is working correctly
- Check that Elasticsearch credentials are set

**Error: "No data available"**
- Verify the date range returns data
- Check Elasticsearch connection and indices

**Missing dependencies**
```bash
pip3 install matplotlib seaborn reportlab
```

## Examples

### Generate report for presentation:
```bash
python3 generate_trend_report.py --format pdf --output-dir presentations
```

### Generate images for dashboard:
```bash
python3 generate_trend_report.py --format png --output-dir dashboard_images
```

### Quick analysis:
```bash
python3 generate_trend_report.py
# Generates both PDF and PNG in ./output directory
```
