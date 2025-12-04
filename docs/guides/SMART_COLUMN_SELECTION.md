# Smart Column Selection and Check Type Recommendations

## Overview

Smart Column Selection is Phase 2 of baselinr's intelligent selection capabilities. Building on Phase 1's usage-based table selection, this feature automatically analyzes column characteristics to recommend appropriate data quality checks.

**Key Benefits:**
- Reduces manual configuration effort by 80%+
- Provides consistent, best-practice check recommendations
- Learns from your existing configurations to improve over time
- Avoids over-monitoring with intelligent prioritization

## Quick Start

```bash
# Generate column-level check recommendations
baselinr recommend --columns --config config.yaml

# Analyze a specific table
baselinr recommend --columns --table analytics.user_events

# View detailed reasoning for recommendations
baselinr recommend --columns --explain

# Preview changes before applying
baselinr recommend --columns --dry-run

# Apply recommendations to your config
baselinr recommend --columns --apply
```

## How It Works

### 1. Column Analysis

The system analyzes columns using multiple signal sources:

**Metadata Signals:**
- Column names and naming patterns (e.g., `created_at`, `user_id`, `email`)
- Data types (timestamp, numeric, string, boolean, JSON)
- Nullability constraints
- Primary key / foreign key status
- Column position (early columns often more important)
- Comments/descriptions if available

**Statistical Signals (from profiling data):**
- Cardinality (distinct value count)
- Null percentage
- Min/max values for numerics and timestamps
- Value distribution patterns
- String length and format patterns

### 2. Check Type Inference

Based on column characteristics, the system recommends appropriate checks:

| Column Type | Common Checks |
|-------------|---------------|
| **Timestamps** (`*_at`, `*_date`) | Freshness, Completeness, Valid Range |
| **Identifiers** (`*_id`, `*_key`) | Uniqueness, Completeness, Format |
| **Email/Phone** | Format Validation, Completeness |
| **Numeric** (`amount`, `price`) | Range, Non-negative, Distribution |
| **Categorical** (`status`, `type`) | Allowed Values, Completeness |
| **Boolean** (`is_*`, `has_*`) | Completeness, Distribution |
| **JSON** | Valid JSON, Schema Validation |

### 3. Confidence Scoring

Each recommendation includes a confidence score:

- **High (0.8-1.0)**: Strong signals, low false positive risk
- **Medium (0.5-0.8)**: Reasonable signals, may need validation
- **Low (0.3-0.5)**: Weak signals, review before applying

Confidence is calculated from:
- Strength of naming pattern match
- Number of supporting signals
- Column importance (PK/FK status)
- Statistical data availability

### 4. Pattern Learning

The system learns from your existing configurations:

```bash
# Learn patterns from your config
baselinr recommend --columns --learn

# View learned patterns
cat .baselinr_patterns.yaml
```

Learned patterns improve future recommendations by capturing your organization's naming conventions and check preferences.

## Configuration

### Enable Column Selection

```yaml
smart_selection:
  enabled: true
  
  # Table-level settings (Phase 1)
  tables:
    mode: "recommend"
    # ... existing config
  
  # Column-level settings (Phase 2)
  columns:
    enabled: true
    mode: "recommend"  # recommend | auto | disabled
    
    inference:
      use_profiling_data: true
      confidence_threshold: 0.7
      max_checks_per_column: 3
      
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
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `enabled` | `false` | Enable column-level recommendations |
| `mode` | `"recommend"` | `recommend` (suggest), `auto` (apply), `disabled` |
| `confidence_threshold` | `0.7` | Minimum confidence to recommend |
| `max_checks_per_column` | `3` | Prevent over-monitoring |
| `use_profiling_data` | `true` | Use historical stats for inference |

## CLI Commands

### Generate Recommendations

```bash
# Basic column recommendations
baselinr recommend --columns --config config.yaml

# For a specific table
baselinr recommend --columns --table public.users

# With detailed explanations
baselinr recommend --columns --explain
```

### Review and Apply

```bash
# Preview what would be added
baselinr recommend --columns --dry-run

# Apply high-confidence recommendations
baselinr recommend --columns --apply

# Output to custom file
baselinr recommend --columns --output my-recommendations.yaml
```

## Output Format

### Recommendations File

```yaml
# recommendations.yaml
metadata:
  generated_at: "2025-01-15T10:30:00"
  column_summary:
    total_columns_analyzed: 45
    total_checks_recommended: 120
    confidence_distribution:
      high: 80
      medium: 30
      low: 10

recommended_tables:
  - schema: analytics
    table: user_events
    confidence: 0.95
    
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
          - "Column name matches pattern: *_timestamp"
          - "Values updated frequently"
        suggested_checks:
          - type: freshness
            confidence: 0.98
            config:
              max_age_hours: 2
          - type: completeness
            confidence: 0.95

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
    note: "Consider manual inspection"
```

## Supported Check Types

| Check Type | Description | Typical Columns |
|------------|-------------|-----------------|
| `completeness` | Non-null percentage | All columns |
| `uniqueness` | Distinct value ratio | IDs, keys |
| `freshness` | Data recency | Timestamps |
| `format_email` | Email format validation | Email fields |
| `format_phone` | Phone number format | Phone fields |
| `format_uuid` | UUID format validation | UUID columns |
| `non_negative` | Value >= 0 | Amounts, counts |
| `range` | Value within bounds | Numeric fields |
| `distribution` | Statistical distribution | Metrics |
| `allowed_values` | Enum validation | Status, type |
| `referential_integrity` | FK references exist | Foreign keys |
| `valid_json` | Valid JSON structure | JSON columns |
| `valid_date_range` | Date within bounds | Date fields |

## Pattern Matching

### Built-in Patterns

The system includes patterns for common column naming conventions:

**Timestamps:**
- `*_at`, `*_date`, `*_time`, `timestamp`
- `created`, `updated`, `deleted`, `modified`

**Identifiers:**
- `*_id`, `*_key`, `*_uuid`, `*_guid`
- Primary key columns

**Contact Information:**
- `*email*`, `*phone*`, `*mobile*`
- `*url*`, `*website*`

**Monetary:**
- `*amount*`, `*price*`, `*cost*`
- `*revenue*`, `*total*`, `*balance*`

**Categorical:**
- `*status*`, `*type*`, `*category*`
- `*state*`, `*level*`

**Boolean:**
- `is_*`, `has_*`, `can_*`
- `*_flag`, `active`, `enabled`

### Custom Patterns

Add custom patterns in your config:

```yaml
smart_selection:
  columns:
    patterns:
      # Match company-specific naming conventions
      - match: "cust_*"
        checks:
          - type: completeness
            confidence: 0.9
      
      # Regex pattern for complex matching
      - match: "^(revenue|cost|profit)_.*$"
        pattern_type: regex
        checks:
          - type: non_negative
          - type: distribution
```

## Integration with Phase 1

Column recommendations integrate seamlessly with table recommendations:

1. **Table Selection (Phase 1)**: Identifies which tables to monitor
2. **Column Analysis (Phase 2)**: For each selected table, recommends column checks

```bash
# Full workflow
baselinr recommend --config config.yaml           # Table recommendations
baselinr recommend --columns --config config.yaml  # Add column checks

# Or combined
baselinr recommend --columns --config config.yaml  # Tables + columns
```

## Best Practices

### 1. Start with High Confidence

Initially use a high confidence threshold to avoid false positives:

```yaml
smart_selection:
  columns:
    inference:
      confidence_threshold: 0.8
```

### 2. Review Before Applying

Always preview recommendations before applying:

```bash
baselinr recommend --columns --dry-run
baselinr recommend --columns --explain
```

### 3. Leverage Learning

Let the system learn from your existing configurations:

```yaml
smart_selection:
  columns:
    learning:
      enabled: true
      store_patterns: true
```

### 4. Customize for Your Domain

Add domain-specific patterns:

```yaml
smart_selection:
  columns:
    patterns:
      # Healthcare-specific
      - match: "*_icd_code"
        checks:
          - type: format
            pattern: "^[A-Z][0-9]{2}(\\.[0-9]{1,2})?$"
      
      # Finance-specific
      - match: "*_account_number"
        checks:
          - type: format
            pattern: "^[0-9]{10,12}$"
          - type: uniqueness
```

### 5. Limit Checks Per Column

Avoid over-monitoring:

```yaml
smart_selection:
  columns:
    inference:
      max_checks_per_column: 3
```

## Troubleshooting

### No Recommendations Generated

1. Ensure `smart_selection.columns.enabled: true`
2. Check that tables are configured or recommended
3. Verify database connection for metadata access
4. Lower `confidence_threshold` if too restrictive

### Low Confidence Scores

- Run profiling first to gather statistics
- Add custom patterns for your naming conventions
- Check that column types are correctly detected

### Too Many Recommendations

- Increase `confidence_threshold`
- Reduce `max_checks_per_column`
- Add patterns to `avoided_checks`
- Use `exclude_patterns` for non-critical columns

## Architecture

```
smart_selection/
├── column_analysis/
│   ├── metadata_analyzer.py    # Extract column metadata
│   ├── statistical_analyzer.py # Analyze profiling data
│   ├── pattern_matcher.py      # Match naming patterns
│   └── check_inferencer.py     # Map signals to checks
├── scoring/
│   ├── confidence_scorer.py    # Calculate confidence
│   └── check_prioritizer.py    # Rank and filter checks
├── learning/
│   ├── pattern_learner.py      # Learn from configs
│   └── pattern_store.py        # Persist patterns
├── config.py                   # Configuration schema
└── recommender.py              # Orchestration engine
```

## API Reference

### Python SDK

```python
from baselinr.smart_selection import (
    ColumnRecommendationEngine,
    RecommendationEngine,
)

# Create engine
engine = RecommendationEngine(
    source_engine=source_conn,
    storage_engine=storage_conn,
    smart_config=config,
)

# Generate recommendations with columns
report = engine.generate_recommendations(include_columns=True)

# Access column recommendations
for table in report.recommended_tables:
    print(f"Table: {table.schema}.{table.table}")
    for col_rec in table.column_recommendations:
        print(f"  Column: {col_rec.column}")
        print(f"  Confidence: {col_rec.confidence}")
        for check in col_rec.suggested_checks:
            print(f"    - {check['type']}")
```

### Direct Column Analysis

```python
from baselinr.smart_selection.column_analysis import (
    MetadataAnalyzer,
    PatternMatcher,
    CheckInferencer,
)

# Analyze column metadata
analyzer = MetadataAnalyzer(engine)
columns = analyzer.analyze_table("users", schema="public")

# Match patterns
matcher = PatternMatcher()
matches = matcher.match_column("created_at")

# Infer checks
inferencer = CheckInferencer()
recommendation = inferencer.infer_checks(columns[0])
```

## Related Documentation

- [Smart Table Selection](SMART_TABLE_SELECTION.md) - Phase 1 table selection
- [Data Validation](DATA_VALIDATION.md) - Configuring validation rules
- [Profiling Enrichment](PROFILING_ENRICHMENT.md) - Statistical profiling
- [Column Level Configs](COLUMN_LEVEL_CONFIGS.md) - Manual column configuration
