# Smart Column Selection and Check Type Recommendations

## Overview

This document describes the Phase 2 implementation of intelligent selection for baselinr. Phase 1 implemented usage-based table selection. Phase 2 adds **column-level intelligence** that automatically suggests appropriate data quality checks based on column characteristics.

## Features

### 1. Automatic Check Recommendations

The system analyzes column metadata and statistical properties to infer appropriate data quality checks:

- **Timestamp columns** (`*_at`, `*_date`, `*_time`) → Freshness, completeness, valid date range checks
- **Identifier columns** (`*_id`, `*_key`, `uuid`) → Uniqueness, completeness, format validation
- **Numeric columns** (`amount`, `price`, `quantity`) → Range validation, distribution monitoring, non-negative constraints
- **String columns** → Format validation (email, phone, URL), allowed values for categorical data
- **Boolean columns** (`is_*`, `has_*`) → Completeness, value distribution checks
- **JSON columns** → Valid JSON structure validation

### 2. Confidence Scoring

Each recommendation includes a confidence score (0.0 - 1.0) based on:

- **Metadata signals**: Column name patterns, data types, constraints
- **Statistical signals**: Cardinality, null percentage, value distributions
- **Pattern matches**: How well the column matches known patterns
- **Column importance**: Primary key, foreign key, position in table

Confidence levels:
- **High (0.8-1.0)**: Strong signals, safe to auto-apply
- **Medium (0.5-0.8)**: Reasonable signals, user validation recommended
- **Low (0.3-0.5)**: Weak signals, manual review required

### 3. Pattern Learning

The system learns from your existing configurations:

- Observes column naming conventions in your config files
- Identifies patterns (suffixes like `_at`, prefixes like `is_`)
- Associates patterns with check types you've configured
- Uses learned patterns to improve future recommendations

## Architecture

### New Module Structure

```
baselinr/smart_selection/
├── column_analysis/           # Column analysis components
│   ├── __init__.py
│   ├── metadata_analyzer.py   # Extract metadata signals from DB
│   ├── statistical_analyzer.py # Analyze profiling statistics
│   ├── pattern_matcher.py     # Match naming patterns
│   └── check_inferencer.py    # Infer appropriate checks
├── scoring/                   # Confidence scoring
│   ├── __init__.py
│   ├── confidence_scorer.py   # Calculate confidence scores
│   └── check_prioritizer.py   # Rank and filter recommendations
├── learning/                  # Pattern learning
│   ├── __init__.py
│   ├── pattern_learner.py     # Learn from existing configs
│   └── pattern_store.py       # Persist learned patterns
├── config.py                  # Extended with column settings
├── recommender.py             # Updated for column recommendations
└── __init__.py                # Updated exports
```

### Key Classes

| Class | Purpose |
|-------|---------|
| `MetadataAnalyzer` | Extracts column metadata (types, constraints, keys) from database |
| `StatisticalAnalyzer` | Analyzes profiling data for cardinality, distributions, patterns |
| `PatternMatcher` | Matches column names against known patterns (email, timestamp, etc.) |
| `CheckInferencer` | Maps column characteristics to appropriate check types |
| `ConfidenceScorer` | Calculates confidence scores for recommendations |
| `CheckPrioritizer` | Ranks checks and applies limits to avoid over-monitoring |
| `PatternLearner` | Learns patterns from existing configurations |
| `PatternStore` | Persists learned patterns to disk |
| `ColumnRecommendationEngine` | Orchestrates the column recommendation process |

## Configuration

### Extended Smart Selection Config

```yaml
smart_selection:
  enabled: true
  
  tables:
    mode: "recommend"  # From Phase 1
    # ... existing table selection config
  
  columns:
    enabled: true
    mode: "recommend"  # recommend | auto | disabled
    
    inference:
      use_profiling_data: true      # Use existing profile stats
      confidence_threshold: 0.7     # Minimum confidence to recommend
      max_checks_per_column: 3      # Avoid over-monitoring
      
      prioritize:
        primary_keys: true
        foreign_keys: true
        timestamp_columns: true
        high_cardinality_strings: false
      
      preferred_checks:
        - completeness
        - freshness
        - uniqueness
      
      avoided_checks:
        - custom_sql  # Don't auto-generate complex checks
    
    patterns:
      - match: "*_email"
        checks:
          - type: format_email
            confidence: 0.95
      
      - match: "revenue_*"
        checks:
          - type: non_negative
            confidence: 0.9
          - type: distribution
            confidence: 0.8
    
    learning:
      enabled: true
      min_occurrences: 2
      min_confidence: 0.7
```

## CLI Usage

### Generate Column Recommendations

```bash
# Recommend checks for all columns in recommended/configured tables
baselinr recommend --columns --config config.yaml

# Recommend for specific table only
baselinr recommend --columns --table analytics.user_events

# Show detailed reasoning for recommendations
baselinr recommend --columns --explain

# Preview changes without applying
baselinr recommend --columns --dry-run

# Apply high-confidence recommendations to config
baselinr recommend --columns --apply
```

### Example Output

```
Analyzing 15 recommended tables...
Analyzing columns in analytics.user_events (45 columns)...
Analyzing columns in analytics.transactions (32 columns)...

Generated 247 column check recommendations across 15 tables
  - High confidence: 156 (63%)
  - Medium confidence: 71 (29%)
  - Low confidence: 20 (8%)

Output saved to: recommendations.yaml

Review recommendations with: baselinr recommend --columns --explain
Apply recommendations with: baselinr recommend --columns --apply
```

### Detailed Explain Mode

```
$ baselinr recommend --columns --explain --table analytics.user_events

Table: analytics.user_events
45 columns analyzed, 23 checks recommended

HIGH CONFIDENCE RECOMMENDATIONS:
✓ event_id (varchar)
  → uniqueness check (confidence: 0.98)
    Reason: Primary key pattern, 100% distinct values
  → completeness check (confidence: 0.95)
    Reason: Critical identifier field

✓ event_timestamp (timestamp)
  → freshness check (confidence: 0.98)
    Reason: Timestamp column, updated continuously
  → completeness check (confidence: 0.95)
    Reason: Required temporal marker

✓ user_email (varchar)
  → format_email check (confidence: 0.92)
    Reason: Column name matches email pattern
  → completeness check (confidence: 0.88)
    Reason: Important contact field

MEDIUM CONFIDENCE RECOMMENDATIONS:
○ event_type (varchar)
  → allowed_values check (confidence: 0.75)
    Reason: Low cardinality (12 values), categorical pattern
```

## Recommendation Output Format

The `recommendations.yaml` file includes column-level recommendations:

```yaml
recommended_tables:
  - schema: analytics
    table: user_events
    confidence: 0.95
    reasons:
      - "Queried 1,247 times in last 30 days"
    
    column_recommendations:
      - column: event_id
        data_type: varchar
        confidence: 0.95
        signals:
          - "Column name matches pattern: *_id"
          - "Primary key indicator"
          - "100% unique values"
        suggested_checks:
          - type: uniqueness
            confidence: 0.98
            config:
              threshold: 1.0
          - type: completeness
            confidence: 0.95
            config:
              min_completeness: 1.0
      
      - column: user_email
        data_type: varchar
        confidence: 0.92
        signals:
          - "Column name matches email pattern"
        suggested_checks:
          - type: format_email
            confidence: 0.92
            config:
              pattern: "email"

low_confidence_suggestions:
  - schema: analytics
    table: user_events
    column: metadata_json
    confidence: 0.45
    signals:
      - "JSON column detected"
    suggested_checks:
      - type: valid_json
        confidence: 0.60
    note: "Consider manual inspection to define schema validation"
```

## Check Types

The system can recommend the following check types:

| Check Type | Description | Typical Columns |
|------------|-------------|-----------------|
| `completeness` | Ensure column has minimal null values | All important columns |
| `uniqueness` | Ensure values are unique | Primary keys, IDs |
| `freshness` | Ensure data is recent | Timestamp columns |
| `format_email` | Validate email format | Email columns |
| `format_phone` | Validate phone format | Phone columns |
| `format_uuid` | Validate UUID format | UUID columns |
| `format_url` | Validate URL format | URL columns |
| `non_negative` | Ensure values >= 0 | Amounts, counts, prices |
| `range` | Validate min/max bounds | Numeric columns |
| `distribution` | Monitor statistical distribution | Important metrics |
| `allowed_values` | Validate against enum | Categorical columns |
| `valid_json` | Validate JSON structure | JSON columns |
| `referential_integrity` | Validate FK references | Foreign keys |

## Pattern Matching

### Built-in Patterns

The system includes 20+ built-in patterns for common column types:

- **Timestamps**: `*_at`, `*_date`, `*_time`, `timestamp`, `created`, `updated`
- **Identifiers**: `*_id`, `*_key`, `uuid`, `guid`
- **Email**: `*email*`, `*_email`
- **Phone**: `*phone*`, `*mobile*`
- **Monetary**: `*amount*`, `*price*`, `*cost*`, `*revenue*`
- **Boolean**: `is_*`, `has_*`, `*_flag`, `active`, `enabled`
- **Status**: `*status*`, `*state*`, `*type*`
- **URLs**: `*url*`, `*link*`, `*href*`

### Custom Patterns

Add custom patterns in your config:

```yaml
smart_selection:
  columns:
    patterns:
      # Company-specific patterns
      - match: "order_ref_*"
        checks:
          - type: uniqueness
          - type: format_alphanumeric
        confidence: 0.9
      
      - match: "*_currency_code"
        checks:
          - type: allowed_values
            config:
              values: ["USD", "EUR", "GBP", "JPY"]
        confidence: 0.95
```

## Pattern Learning

### How It Works

1. The system scans your existing `baselinr` configuration
2. Identifies columns with explicit check configurations
3. Extracts patterns from column names (suffixes, prefixes)
4. Associates patterns with check types
5. Stores learned patterns for future recommendations

### Learned Patterns Storage

Patterns are stored in `.baselinr_patterns.yaml`:

```yaml
version: "1.0"
patterns:
  - pattern: "*_at"
    pattern_type: suffix
    suggested_checks:
      - freshness
      - completeness
    confidence: 0.92
    source_columns:
      - created_at
      - updated_at
      - deleted_at
    occurrence_count: 15
  
  - pattern: "is_*"
    pattern_type: prefix
    suggested_checks:
      - completeness
    confidence: 0.88
    source_columns:
      - is_active
      - is_verified
      - is_deleted
    occurrence_count: 8
```

### Export Learned Patterns

Convert learned patterns to config format:

```python
from baselinr.smart_selection.learning import PatternStore

store = PatternStore()
config = store.export_to_config()
# Add to your baselinr config under smart_selection.columns.patterns
```

## Integration with Phase 1

Column recommendations integrate seamlessly with table recommendations:

1. Phase 1 identifies which tables to monitor
2. Phase 2 analyzes columns in those tables
3. Combined report includes both table and column recommendations
4. `--apply` adds both table entries and column checks to config

```bash
# Full recommendation flow
baselinr recommend                    # Table recommendations only
baselinr recommend --columns          # Table + column recommendations
baselinr recommend --columns --apply  # Apply both to config
```

## Performance Considerations

### Column Analysis Limits

- Default `max_checks_per_column`: 3 (configurable)
- Default `max_checks_per_table`: 50 (configurable)
- Statistical analysis uses cached profiling data when available

### Caching

- Metadata analysis results are cached per session
- Statistical analysis uses existing profiling results
- Learned patterns are persisted to disk

## Testing

The implementation includes 76 unit tests across 4 test files:

```bash
# Run all column selection tests
pytest tests/test_column_analysis.py         # 28 tests
pytest tests/test_column_scoring.py          # 15 tests
pytest tests/test_column_learning.py         # 20 tests
pytest tests/test_column_recommendation_integration.py  # 13 tests
```

## Future Enhancements

Potential improvements for future versions:

1. **Industry profiles**: Pre-configured patterns for healthcare, finance, e-commerce
2. **Composite checks**: Recommendations for cross-column validations (e.g., `start_date < end_date`)
3. **Severity levels**: Different check severities (error vs. warning)
4. **External rule libraries**: Integration with community-contributed patterns
5. **ML-based inference**: Use machine learning for pattern detection
6. **Feedback loop**: Learn from accepted/rejected recommendations

## Related Documentation

- [Smart Table Selection](../guides/SMART_TABLE_SELECTION.md) - Phase 1 documentation
- [Data Validation](../guides/DATA_VALIDATION.md) - Check type reference
- [Configuration Reference](../schemas/SCHEMA_REFERENCE.md) - Full config schema
