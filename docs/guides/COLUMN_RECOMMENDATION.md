# Smart Column Selection and Check Type Recommendations

## Overview

Phase 2 of intelligent selection for baselinr introduces **column-level intelligence** that automatically suggests appropriate data quality checks based on column characteristics. Building upon Phase 1's usage-based table selection, this feature analyzes column metadata and statistical properties to generate specific, actionable check recommendations per column.

## Key Features

- **Automatic Check Inference**: Analyzes column names, types, constraints, and statistics to suggest appropriate checks
- **Pattern Recognition**: Matches columns against common naming conventions (timestamps, IDs, emails, etc.)
- **Confidence Scoring**: Assigns confidence scores to recommendations based on signal strength
- **Pattern Learning**: Learns from existing configurations to improve future recommendations
- **CLI Integration**: New `--columns` flag for the `recommend` command

## New Modules

### Column Analysis Module (`baselinr/smart_selection/column_analysis/`)

| File | Purpose |
|------|---------|
| `metadata_analyzer.py` | Extracts column metadata signals (names, types, constraints, keys) using SQLAlchemy inspection |
| `statistical_analyzer.py` | Analyzes historical profiling data for cardinality, distributions, and patterns |
| `pattern_matcher.py` | Matches column names against predefined and custom naming convention patterns |
| `check_inferencer.py` | Maps column characteristics to appropriate check types using rule-based logic |

### Scoring Module (`baselinr/smart_selection/scoring/`)

| File | Purpose |
|------|---------|
| `confidence_scorer.py` | Calculates confidence scores for recommendations based on signal strength |
| `check_prioritizer.py` | Ranks and filters checks to avoid over-monitoring |

### Learning Module (`baselinr/smart_selection/learning/`)

| File | Purpose |
|------|---------|
| `pattern_learner.py` | Learns naming patterns and check preferences from existing configurations |
| `pattern_store.py` | Persists and manages learned patterns in YAML format |

## Supported Check Types

| Check Type | Triggered By |
|------------|--------------|
| `completeness` | Primary keys, non-nullable columns, required fields |
| `uniqueness` | Primary keys, columns with high cardinality |
| `freshness` | Timestamp columns (`*_at`, `*_date`, `updated_*`, `created_*`) |
| `format_email` | Email columns (`*email*`, `*_email`) |
| `format_phone` | Phone columns (`*phone*`, `*_phone`) |
| `format_url` | URL columns (`*url*`, `*_url`, `*_link`) |
| `format_uuid` | UUID columns (`*uuid*`, `*_guid`) |
| `non_negative` | Monetary/count columns (`*amount*`, `*price*`, `*count*`) |
| `range` | Numeric columns with observed min/max values |
| `allowed_values` | Low cardinality categorical columns |
| `referential_integrity` | Foreign key columns |
| `valid_json` | JSON/JSONB columns |

## Configuration

### Column Selection Settings

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
        - custom_sql

    # Custom pattern overrides
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

    # Pattern learning settings
    learning:
      enabled: true
      min_occurrences: 2
      storage_path: ".baselinr_patterns.yaml"
```

## CLI Usage

### Generate Column Recommendations

```bash
# Recommend checks for all columns in recommended/configured tables
baselinr recommend --columns --config config.yaml

# Recommend for a specific table
baselinr recommend --columns --table analytics.user_events --config config.yaml

# Show detailed reasoning for recommendations
baselinr recommend --columns --explain --config config.yaml

# Preview changes without applying
baselinr recommend --columns --dry-run --config config.yaml

# Apply column recommendations to config
baselinr recommend --columns --apply --config config.yaml
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

### Explain Mode Output

```
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
◐ user_email (varchar)
  → format_email check (confidence: 0.72)
    Reason: Email pattern match in column name
```

## Recommendation Output Format

When saved to `recommendations.yaml`:

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
        confidence: 0.85
        signals:
          - "Email pattern match"
        suggested_checks:
          - type: format_email
            confidence: 0.92
            config:
              pattern: "email"

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
    note: "Consider manual inspection to define schema validation"
```

## Pattern Learning

The system can learn from your existing configurations to improve recommendations:

```yaml
# Learned patterns stored in .baselinr_patterns.yaml
learned_patterns:
  - pattern: "*_at"
    pattern_type: suffix
    suggested_checks:
      - freshness
      - completeness
    confidence: 0.95
    occurrence_count: 15
    source_columns:
      - created_at
      - updated_at
      - deleted_at

  - pattern: "is_*"
    pattern_type: prefix
    suggested_checks:
      - completeness
    confidence: 0.88
    occurrence_count: 8
```

## Confidence Scoring

Confidence scores are calculated based on:

| Factor | Weight | Description |
|--------|--------|-------------|
| Metadata signals | 30% | Column name, type, constraints |
| Statistical signals | 30% | Cardinality, null rate, distributions |
| Pattern matches | 25% | Naming convention matches |
| Consistency | 15% | Historical stability of values |

**Confidence Levels:**
- **High (0.8-1.0)**: Strong signals, safe to auto-apply
- **Medium (0.5-0.8)**: Reasonable signals, user validation recommended
- **Low (0.3-0.5)**: Weak signals, manual review required

## Check Prioritization

To avoid over-monitoring, checks are prioritized by:

1. **Column Importance**: Primary keys > Foreign keys > Timestamps > Regular columns
2. **Check Value**: Uniqueness/Completeness > Freshness > Format validation > Distribution
3. **Confidence Score**: Higher confidence checks ranked first
4. **User Preferences**: Preferred checks boosted, avoided checks filtered

Default limits:
- Maximum 5 checks per column
- Maximum 50 checks per table
- Minimum 0.5 confidence threshold

## Integration with Existing Config

Column recommendations integrate seamlessly with existing configurations:

- **Explicit configs take precedence**: User-defined column checks are never overwritten
- **Conflict warnings**: Alerts when recommendations conflict with existing checks
- **Exclusion support**: Columns can be excluded via `exclude_from_recommendations`
- **Partial acceptance**: Accept some recommendations, reject others

## Tests

The implementation includes comprehensive unit tests:

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_column_analysis.py` | 28 | Metadata, patterns, statistics, inference |
| `test_column_scoring.py` | 15 | Confidence scoring, prioritization |
| `test_column_learning.py` | 20 | Pattern learning, storage |
| `test_column_recommendation_integration.py` | 13 | End-to-end flows |

Run tests:
```bash
pytest tests/test_column_analysis.py tests/test_column_scoring.py \
       tests/test_column_learning.py tests/test_column_recommendation_integration.py -v
```

## Architecture

```
baselinr/smart_selection/
├── column_analysis/
│   ├── __init__.py
│   ├── metadata_analyzer.py    # SQLAlchemy-based metadata extraction
│   ├── statistical_analyzer.py # Profiling data analysis
│   ├── pattern_matcher.py      # Naming convention matching
│   └── check_inferencer.py     # Check type inference rules
├── scoring/
│   ├── __init__.py
│   ├── confidence_scorer.py    # Confidence calculation
│   └── check_prioritizer.py    # Check ranking and filtering
├── learning/
│   ├── __init__.py
│   ├── pattern_learner.py      # Learn from existing configs
│   └── pattern_store.py        # Persist learned patterns
├── config.py                   # Extended with column settings
├── recommender.py              # Integrated column recommendations
└── __init__.py                 # Updated exports
```

## Future Enhancements

Potential future improvements:

- **Industry profiles**: Pre-built patterns for finance, healthcare, e-commerce
- **Composite checks**: Cross-column validations (e.g., `start_date < end_date`)
- **Severity levels**: Recommend error vs. warning severity
- **ML-based inference**: Learn check patterns from accepted/rejected recommendations
- **External rule libraries**: Integration with community-contributed rule sets

## Migration from Phase 1

No migration required. Phase 2 is additive:

- All Phase 1 table recommendations continue to work unchanged
- Column recommendations are opt-in via `--columns` flag
- Existing configurations are not modified unless `--apply` is used
- The `columns` section in `smart_selection` config is optional

## Troubleshooting

### No column recommendations generated

1. Ensure `smart_selection.columns.enabled: true` in config
2. Check that tables exist and are accessible
3. Verify confidence threshold isn't too high

### Low confidence scores

1. Run profiling first to generate statistics: `baselinr run --config config.yaml`
2. Lower `confidence_threshold` in config
3. Add custom patterns for domain-specific columns

### Pattern learning not working

1. Ensure `learning.enabled: true` in config
2. Check that `.baselinr_patterns.yaml` is writable
3. Verify `min_occurrences` threshold is met

## References

- [Smart Table Selection (Phase 1)](SMART_TABLE_SELECTION.md)
- [Configuration Reference](../schemas/SCHEMA_REFERENCE.md)
- [Data Validation Guide](DATA_VALIDATION.md)
