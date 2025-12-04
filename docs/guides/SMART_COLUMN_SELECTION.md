# Smart Column Selection and Check Type Recommendations

## Overview

Smart Column Selection is Phase 2 of baselinr's intelligent selection capabilities. Building on Phase 1's usage-based table selection, this feature automatically suggests appropriate data quality checks at the column level based on column characteristics.

**Key Benefits:**
- Reduces manual configuration effort by auto-recommending checks
- Analyzes column metadata and statistical properties to infer check types
- Learns from existing configurations to improve recommendations
- Provides confidence scores to help prioritize which checks to apply
- Avoids over-monitoring by recommending only high-value checks

## Architecture

The implementation consists of three main modules:

```
baselinr/smart_selection/
├── column_analysis/           # Column analysis and check inference
│   ├── metadata_analyzer.py   # Extracts column metadata signals
│   ├── statistical_analyzer.py # Analyzes profiling statistics
│   ├── pattern_matcher.py     # Matches naming convention patterns
│   └── check_inferencer.py    # Maps signals to check types
├── scoring/                   # Confidence and priority scoring
│   ├── confidence_scorer.py   # Calculates confidence scores
│   └── check_prioritizer.py   # Ranks and filters recommendations
└── learning/                  # Pattern learning from configs
    ├── pattern_learner.py     # Learns patterns from existing configs
    └── pattern_store.py       # Persists learned patterns
```

## Configuration

Add column-level smart selection settings to your `config.yaml`:

```yaml
smart_selection:
  enabled: true
  
  # Table selection (Phase 1)
  tables:
    mode: "recommend"
    # ... existing table selection config
  
  # Column selection (Phase 2 - NEW)
  columns:
    enabled: true
    mode: "recommend"  # Options: recommend | auto | disabled
    
    # Inference settings
    inference:
      use_profiling_data: true      # Use existing profile stats
      confidence_threshold: 0.7     # Minimum confidence to recommend
      max_checks_per_column: 3      # Avoid over-monitoring
      
      # Column prioritization
      prioritize:
        primary_keys: true
        foreign_keys: true
        timestamp_columns: true
        high_cardinality_strings: false
      
      # Check type preferences
      preferred_checks:
        - completeness
        - freshness
        - uniqueness
      
      avoided_checks:
        - custom_sql  # Don't auto-generate complex checks
    
    # Custom pattern overrides
    patterns:
      - match: "*_email"
        checks:
          - type: format_email
            confidence: 0.95
      
      - match: "revenue_*"
        checks:
          - type: non_negative
          - type: distribution
    
    # Learning settings
    learning:
      enabled: true
      min_occurrences: 2
      min_confidence: 0.6
```

## CLI Usage

### Generate Column Recommendations

```bash
# Recommend checks for all columns in recommended tables
baselinr recommend --columns --config config.yaml

# Recommend for a specific table
baselinr recommend --columns --table analytics.user_events

# Show detailed reasoning for each recommendation
baselinr recommend --columns --explain

# Preview changes without applying
baselinr recommend --columns --dry-run

# Apply recommendations to config
baselinr recommend --columns --apply
```

### Example Output

```
$ baselinr recommend --columns --config config.yaml

Analyzing 15 recommended tables...
Analyzing columns in analytics.user_events (45 columns)...
Analyzing columns in analytics.transactions (32 columns)...
...

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

MEDIUM CONFIDENCE RECOMMENDATIONS:
○ user_email (varchar)
  → format_email check (confidence: 0.75)
    Reason: Email pattern in column name
...
```

## How It Works

### 1. Metadata Analysis

The `MetadataAnalyzer` extracts static signals from column definitions:

| Signal | Source | Example |
|--------|--------|---------|
| Column name patterns | Name matching | `*_at` → timestamp |
| Data type | Schema | `TIMESTAMP`, `INTEGER` |
| Nullability | Constraints | `NOT NULL` |
| Primary/Foreign keys | Constraints | PK/FK indicators |
| Column position | Schema | Early columns often important |
| Comments/descriptions | Metadata | Documentation hints |

### 2. Statistical Analysis

The `StatisticalAnalyzer` derives signals from profiling data:

| Signal | Metric | Interpretation |
|--------|--------|----------------|
| Cardinality | distinct_count | Low → categorical, High → identifier |
| Null rate | null_percentage | High → optional field |
| Value range | min/max | Bounds for range checks |
| Distribution | value_distribution | Top values for allowed_values |
| Patterns | detected_patterns | Email, UUID, phone formats |

### 3. Pattern Matching

The `PatternMatcher` identifies columns by naming conventions:

| Pattern | Suggested Checks |
|---------|------------------|
| `*_at`, `*_timestamp` | freshness, valid_range |
| `*_id`, `*_key` | uniqueness, completeness |
| `*_email` | format_email, completeness |
| `is_*`, `has_*` | completeness (boolean) |
| `*_amount`, `*_price` | non_negative, range |
| `*_status`, `*_type` | allowed_values |

### 4. Check Inference

The `CheckInferencer` combines all signals to recommend checks:

```python
# Example inference flow for a column
metadata = ColumnMetadata(
    name="user_email",
    data_type="VARCHAR(255)",
    nullable=True,
    name_patterns=["format:email"]
)

# Inferred checks:
# 1. format_email (0.95) - strong name pattern match
# 2. completeness (0.85) - common for email fields
```

### 5. Confidence Scoring

The `ConfidenceScorer` calculates reliability scores:

| Confidence Level | Score Range | Meaning |
|------------------|-------------|---------|
| High | 0.8 - 1.0 | Strong signals, low false positive risk |
| Medium | 0.5 - 0.8 | Reasonable signals, may need validation |
| Low | 0.3 - 0.5 | Weak signals, suggest but don't auto-apply |

Scoring factors:
- Multiple supporting signals boost confidence
- Primary/foreign key status adds weight
- Statistical data provides validation
- Missing stats slightly penalize score

### 6. Prioritization

The `CheckPrioritizer` filters and ranks recommendations:

1. Filter by minimum confidence threshold
2. Remove avoided check types
3. Boost preferred check types
4. Sort by priority and confidence
5. Apply per-column and per-table limits

## Supported Check Types

| Check Type | Description | Typical Columns |
|------------|-------------|-----------------|
| `completeness` | Non-null percentage | Required fields |
| `uniqueness` | Distinct value ratio | Primary keys, IDs |
| `freshness` | Data recency | Timestamps |
| `format_email` | Email format validation | Email columns |
| `format_uuid` | UUID format validation | UUID identifiers |
| `format_phone` | Phone number format | Phone columns |
| `non_negative` | Value >= 0 | Amounts, counts |
| `range` | Min/max bounds | Numeric columns |
| `allowed_values` | Enumerated values | Status, type columns |
| `distribution` | Statistical distribution | Metrics columns |
| `referential_integrity` | Foreign key validation | FK columns |
| `valid_json` | JSON structure validation | JSON columns |

## Pattern Learning

The system learns from your existing configurations:

```yaml
# Learned patterns stored in .baselinr_patterns.yaml
learned_patterns:
  - pattern: "*_at"
    pattern_type: suffix
    suggested_checks: [freshness, completeness]
    confidence: 0.95
    occurrence_count: 15
    
  - pattern: "is_*"
    pattern_type: prefix
    suggested_checks: [completeness]
    confidence: 0.88
    occurrence_count: 8
```

To export learned patterns:

```bash
# Learn from existing config
baselinr recommend --columns --learn --config config.yaml

# Export learned patterns for review
baselinr recommend --columns --export-patterns patterns.yaml
```

## Output Format

Recommendations are saved to `recommendations.yaml`:

```yaml
# Generated: 2025-01-15

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

      - column: event_timestamp
        data_type: timestamp
        confidence: 0.98
        signals:
          - "Timestamp column pattern"
          - "Most recent value: 2025-01-15"
        suggested_checks:
          - type: freshness
            confidence: 0.98
            config:
              max_age_hours: 2
          - type: valid_range
            confidence: 0.85
            config:
              min: "2024-01-01"
              max: "now + 1 hour"

low_confidence_suggestions:
  - schema: analytics
    table: user_events
    column: metadata_json
    data_type: json
    confidence: 0.45
    signals:
      - "JSON column detected"
    suggested_checks:
      - type: valid_json
        confidence: 0.60
    note: "Consider manual inspection"
```

## Integration with Existing Config

Column recommendations integrate with your existing baselinr configuration:

1. **Explicit configs take precedence** - Your manually configured checks are never overwritten
2. **Conflict warnings** - Alerts when recommendations conflict with existing checks
3. **Partial acceptance** - Apply some checks, reject others
4. **Column exclusion** - Add `exclude_from_recommendations: true` to skip columns

## Best Practices

1. **Start with recommend mode** - Review suggestions before auto-applying
2. **Use explain for understanding** - See reasoning behind each recommendation
3. **Tune confidence threshold** - Higher = fewer false positives, lower = broader coverage
4. **Define custom patterns** - Add organization-specific naming conventions
5. **Enable learning** - Let the system adapt to your practices
6. **Review low confidence** - These often reveal edge cases worth examining

## Troubleshooting

### No recommendations generated

- Ensure `smart_selection.columns.enabled: true`
- Check `confidence_threshold` isn't too high
- Verify profiling data exists if `use_profiling_data: true`

### Too many recommendations

- Increase `confidence_threshold`
- Reduce `max_checks_per_column`
- Add check types to `avoided_checks`

### Wrong check types suggested

- Add custom patterns to override defaults
- Use `avoided_checks` to exclude problematic types
- Adjust `preferred_checks` for your use case

## API Reference

### Python SDK

```python
from baselinr.smart_selection import (
    ColumnRecommendationEngine,
    RecommendationEngine,
)

# Create recommendation engine
engine = RecommendationEngine(
    source_engine=source_db,
    storage_engine=storage_db,
    smart_config=config.smart_selection,
)

# Generate recommendations with columns
report = engine.generate_recommendations(
    existing_tables=existing_tables,
    include_columns=True,
)

# Or analyze specific table columns directly
column_engine = engine._get_column_engine()
column_recs = column_engine.generate_column_recommendations(
    table_name="user_events",
    schema="analytics",
)

for rec in column_recs:
    print(f"{rec.column_name}: {len(rec.suggested_checks)} checks")
```

## Testing

The implementation includes comprehensive tests:

```bash
# Run all column selection tests
pytest tests/test_column_analysis.py tests/test_column_scoring.py \
       tests/test_column_learning.py tests/test_column_recommendation_integration.py -v

# Run specific test module
pytest tests/test_column_analysis.py -v

# Run with coverage
pytest tests/test_column_*.py --cov=baselinr.smart_selection
```

## Changelog

### Version 1.0.0 (Phase 2 Release)

- Added column analysis module with metadata and statistical analyzers
- Implemented pattern matching for naming conventions
- Added check type inference with 12 supported check types
- Implemented confidence scoring and check prioritization
- Added pattern learning from existing configurations
- Extended CLI with `--columns`, `--table`, `--explain`, `--dry-run` flags
- Added 76 unit tests covering all new functionality
