# Daily Engagement Trend Analysis Report

## Executive Summary

Analysis of daily average engagement (sum of `eventProperties.count` for `widgetVisitedSession` events with specific event identifiers) over the last 60 days reveals:

- **Overall Trend**: Decreasing (-14.60% over the 60-day period)
- **Most Significant Change**: October 5, 2025 - 38.92% day-over-day increase
- **Key Anomaly Period**: October 5-8, 2025 - Sustained high engagement levels

## Key Findings

### 1. Substantial Increase on October 5, 2025

**The most significant change occurred on October 5, 2025:**
- **Day-over-day increase**: 38.92%
- **Values**: 228,918 → 318,021 (+89,103)
- **Statistical significance**: z-score of 2.97 (highly unusual, >2 standard deviations from mean)

### 2. Sustained High Engagement Period (October 5-8)

The spike on October 5 was not isolated - it was followed by several days of elevated engagement:

| Date | Value | Deviation from Mean |
|------|-------|-------------------|
| Oct 5 | 318,021 | +45.48% |
| Oct 6 | 309,624 | +41.63% |
| Oct 8 | 286,438 | +31.03% |

This pattern suggests a **sustained change** rather than a one-day anomaly.

### 3. Other Significant Increases

Additional notable increases detected:

1. **September 23, 2025**: +23.81% (200,719 → 248,503)
2. **November 6, 2025**: +21.79% (213,998 → 260,623)
3. **October 11, 2025**: +9.85% (191,467 → 210,319)
4. **October 12, 2025**: +8.87% (210,319 → 228,965)

### 4. Statistical Outliers

Four days were identified as statistical outliers (>2 standard deviations from mean):

- **October 5**: 318,021 (z-score: 2.97, +45.48%)
- **October 6**: 309,624 (z-score: 2.72, +41.63%)
- **October 8**: 286,438 (z-score: 2.03, +31.03%)
- **November 17**: 106,790 (z-score: -3.34, -51.15%) - *Low outlier*

## Overall Statistics

- **Mean**: 218,607.56
- **Median**: 213,998.00
- **Standard Deviation**: 33,485.49
- **Range**: 106,790 to 318,021
- **Overall Trend**: Decreasing at 0.24% per day

## Recommendations

### Investigation Priorities

1. **October 5, 2025 Event**
   - Review product releases, feature launches, or system changes around this date
   - Check marketing campaigns or promotions that started on or before this date
   - Examine any configuration changes to the widget or event tracking
   - Review user behavior changes or new user segments

2. **Sustained Period (Oct 5-8)**
   - The multi-day pattern suggests a systemic change rather than a one-time event
   - Investigate what maintained the elevated engagement for several days
   - Check if there were any ongoing campaigns or features active during this period

3. **September 23 Spike**
   - Second-largest increase (23.81%) - investigate similar factors as Oct 5
   - Check if there's a pattern or correlation with the Oct 5 event

### Potential Causes to Investigate

- **Product/Feature Launch**: New widget features or capabilities
- **Marketing Campaign**: Promotional activities or advertising campaigns
- **System Configuration**: Changes to event tracking, counting logic, or aggregation
- **User Behavior Shift**: Changes in how users interact with the widget
- **External Events**: Industry events, holidays, or seasonal patterns
- **Technical Changes**: Updates to the widget implementation or event firing logic

## Data Details

- **Event Name**: `widgetVisitedSession`
- **Event Identifiers Filtered**:
  - DISENGAGED_ON_THE_PRODUCT_PAGE
  - PRODUCT_ADD_TO_CART
  - HOME_PAGE_WELCOME_MESSAGE
  - PRODUCT_HISTORY_RECOMMENDATION
  - PRODUCT_REMOVE_FROM_CART
- **Date Range**: Last 60 days (September 18 - November 17, 2025)
- **Scope**: All stores

## Next Steps

1. Review deployment logs and release notes around October 5, 2025
2. Check marketing calendar for campaigns starting in early October
3. Examine system configuration changes in the days leading up to October 5
4. Compare engagement patterns before and after October 5 to identify what changed
5. Investigate the September 23 spike for potential correlation with October 5 event

---

*Report generated from Elasticsearch analysis of widget engagement events*
