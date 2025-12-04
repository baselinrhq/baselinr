# Smart Column Selection and Check Type Recommendations

## Overview

Smart Column Selection is Phase 2 of baselinr's intelligent selection feature. Building upon Phase 1's usage-based table selection, this feature automatically suggests appropriate data quality checks at the column level by analyzing column characteristics, metadata, and statistical properties.

## Key Features

- **Automatic Check Inference**: Analyzes column names, types, constraints, and statistics to suggest relevant data quality checks
- **Confidence Scoring**: Each recommendation includes a confidence score to help prioritize which suggestions to apply
- **Pattern Learning**: Learns from existing configurations to improve future recommendations
- **Extensible Rules**: Supports custom pattern rules for domain-specific conventions
- **Non-Intrusive**: All recommendations are opt-in; explicit configurations always take precedence

## Quick Start

### Generate Column Recommendations

```bash
# Recommend checks for all columns in configured tables
baselinr recommend --columns --config config.yaml

# Recommend for a specific table
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
```

## Configuration

### Enabling Column Selection

Add the `columns` section to your `smart_selection` configuration:

```yaml
smart_selection:
  enabled: true
  
  tables:
    mode: "recommend"  # Phase 1 table selection
    
  columns:
    enabled: true
    mode: "recommend"  # Options: recommend, auto, disabled
    
    inference:
      use_profiling_data: true      # Use existing profile stats
      confidence_threshold: 0.7      # Minimum confidence to recommend
      max_checks_per_column: 3       # Avoid over-monitoring
      
      prioritize:
        primary_keys: true           # Boost PK columns
        foreign_keys: true           # Boost FK columns
        timestamp_columns: true      # Boost temporal columns
        high_cardinality_strings: false
        
      preferred_checks:
        - completeness
        - freshness
        - uniqueness
        
      avoided_checks:
        - custom_sql               # Don't auto-generate complex checks
        
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
            
    learning:
      enabled: true
      min_occurrences: 2           # Min patterns to learn
      storage_path: ".baselinr_patterns.yaml"
```

## Check Type Inference Rules

### Timestamp/Date Columns

**Detected by:**
- Column names: `*_at`, `*_date`, `*_time`, `timestamp`, `created`, `updated`, `deleted`
- Data types: `TIMESTAMP`, `DATE`, `DATETIME`

**Suggested checks:**
- `freshness` - Especially for `updated_at`, `created_at`, `loaded_at`
- `completeness` - Critical temporal markers should not be null
- `valid_range` - No future dates for historical data

### Identifier Columns

**Detected by:**
- Column names: `*_id`, `*_key`, `uuid`, `guid`
- Primary key constraints
- Foreign key constraints

**Suggested checks:**
- `uniqueness` - For primary keys
- `completeness` - IDs should rarely be null
- `format_uuid` - For UUID/GUID columns
- `referential_integrity` - For foreign keys

### Numeric Columns

**Detected by:**
- Column names: `amount`, `price`, `quantity`, `count`, `total`, `balance`, `revenue`
- Data types: `INTEGER`, `DECIMAL`, `FLOAT`, `NUMERIC`

**Suggested checks:**
- `range` - Based on historical min/max with buffer
- `distribution` - Detect shifts in mean/median/stddev
- `non_negative` - For counts, amounts, prices
- `completeness` - For business-critical metrics

### String Columns

**Detected by:**
- Column names: `email`, `phone`, `url`, `address`, `status`, `type`
- Cardinality analysis from profiling data

**Suggested checks:**
- `format_email` - Email pattern validation
- `format_phone` - Phone number patterns
- `format_url` - URL format validation
- `allowed_values` - For low-cardinality categorical columns
- `length` - String length constraints

### Boolean/Flag Columns

**Detected by:**
- Column names: `is_*`, `has_*`, `*_flag`, `active`, `deleted`
- Data types: `BOOLEAN`, `BIT`

**Suggested checks:**
- `completeness` - Booleans should rarely be null
- `distribution` - Detect unexpected skew

### JSON Columns

**Detected by:**
- Data types: `JSON`, `JSONB`
- Column names containing `json`, `metadata`, `payload`

**Suggested checks:**
- `valid_json` - Validate JSON structure
- `completeness` - If JSON content is required

## Confidence Scoring

Recommendations are scored based on multiple signals:

| Confidence Level | Score Range | Description |
|-----------------|-------------|-------------|
| **High** | 0.8 - 1.0 | Strong signals, low false positive risk |
| **Medium** | 0.5 - 0.8 | Reasonable signals, may need validation |
| **Low** | 0.3 - 0.5 | Weak signals, suggest but don't auto-apply |

### Scoring Factors

- **Name Pattern Match**: Clear naming patterns increase confidence
- **Type Alignment**: Data type matches expected type for check
- **Constraint Support**: Primary/foreign key constraints boost confidence
- **Statistical Evidence**: Profiling data confirms the pattern
- **Multiple Signals**: More supporting signals increase confidence

## Recommendation Output Format

Recommendations are saved to `recommendations.yaml`:

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
            
      - column: event_type
        data_type: varchar
        confidence: 0.88
        signals:
          - "Low cardinality: 12 distinct values"
          - "Column name suggests categorical data"
        suggested_checks:
          - type: allowed_values
            confidence: 0.90
            config:
              values: ["click", "view", "purchase", ...]
              
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

Smart Column Selection can learn from your existing configurations:

### How It Works

1. Analyzes column names and their configured checks in your config
2. Identifies common naming patterns (prefixes, suffixes, exact matches)
3. Associates patterns with check types
4. Stores learned patterns for future recommendations

### Learned Pattern Example

```yaml
learned_patterns:
  - pattern: "*_at"
    pattern_type: suffix
    suggested_checks: [freshness, completeness]
    confidence: 0.95
    source_columns: [created_at, updated_at, deleted_at]
    occurrence_count: 15
    
  - pattern: "is_*"
    pattern_type: prefix
    suggested_checks: [completeness]
    confidence: 0.88
    source_columns: [is_active, is_verified, is_deleted]
    occurrence_count: 8
```

### Using Learned Patterns

Learned patterns are automatically loaded and merged with built-in rules. They can be exported to your configuration:

```bash
# Export learned patterns to config format
baselinr recommend --columns --export-patterns
```

## Architecture

### Module Structure

```
baselinr/smart_selection/
├── column_analysis/
│   ├── __init__.py
│   ├── metadata_analyzer.py    # Extract column metadata signals
│   ├── statistical_analyzer.py # Analyze profiling statistics
│   ├── pattern_matcher.py      # Match naming patterns
│   └── check_inferencer.py     # Map signals to check types
├── scoring/
│   ├── __init__.py
│   ├── confidence_scorer.py    # Calculate confidence scores
│   └── check_prioritizer.py    # Rank and filter recommendations
├── learning/
│   ├── __init__.py
│   ├── pattern_learner.py      # Learn patterns from configs
│   └── pattern_store.py        # Persist learned patterns
├── config.py                   # Configuration schema
└── recommender.py              # Main recommendation engine
```

### Data Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ MetadataAnalyzer│────►│ PatternMatcher   │────►│ CheckInferencer │
│ (column info)   │     │ (naming patterns)│     │ (check mapping) │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
┌─────────────────┐                              ┌────────▼────────┐
│StatisticalAnalyz│─────────────────────────────►│ConfidenceScorer │
│ (profiling data)│                              │ (score checks)  │
└─────────────────┘                              └────────┬────────┘
                                                          │
                                                 ┌────────▼────────┐
                                                 │ CheckPrioritizer│
                                                 │ (rank & filter) │
                                                 └────────┬────────┘
                                                          │
                                                 ┌────────▼────────┐
                                                 │  Recommendations │
                                                 └─────────────────┘
```

## Supported Check Types

| Check Type | Description | Typical Use Case |
|------------|-------------|------------------|
| `completeness` | Non-null percentage | Required fields |
| `uniqueness` | Distinct value ratio | Primary keys, identifiers |
| `freshness` | Data recency | Timestamp columns |
| `range` | Min/max bounds | Numeric values |
| `non_negative` | Value >= 0 | Counts, amounts |
| `distribution` | Statistical metrics | Numeric monitoring |
| `allowed_values` | Enum validation | Categorical columns |
| `format_email` | Email pattern | Email fields |
| `format_phone` | Phone pattern | Phone fields |
| `format_url` | URL pattern | URL fields |
| `format_uuid` | UUID pattern | UUID identifiers |
| `valid_json` | JSON structure | JSON columns |
| `referential_integrity` | Foreign key checks | FK relationships |
| `length` | String length bounds | Text fields |

## Best Practices

### Start Conservative

- Begin with `mode: recommend` to review suggestions
- Focus on high-confidence recommendations first
- Gradually lower `confidence_threshold` as trust builds

### Avoid Over-Monitoring

- Set `max_checks_per_column: 3` to limit noise
- Use `avoided_checks` to exclude expensive checks
- Review low-confidence suggestions manually

### Leverage Profiling Data

- Run profiling before generating recommendations
- Enable `use_profiling_data: true` for better accuracy
- Statistical signals significantly improve confidence

### Custom Patterns

- Add domain-specific patterns in configuration
- Use learned patterns for team conventions
- Export patterns to share across projects

## Troubleshooting

### No Recommendations Generated

1. Ensure `smart_selection.columns.enabled: true`
2. Check that tables exist and are accessible
3. Verify `confidence_threshold` isn't too high

### Low Confidence Scores

1. Run profiling to provide statistical signals
2. Add custom patterns for domain-specific names
3. Check if column names follow common conventions

### Too Many Recommendations

1. Increase `confidence_threshold`
2. Reduce `max_checks_per_column`
3. Add patterns to `avoided_checks`

## API Reference

### ColumnRecommendationEngine

```python
from baselinr.smart_selection import ColumnRecommendationEngine

engine = ColumnRecommendationEngine(
    source_engine=source_engine,
    storage_engine=storage_engine,  # Optional, for profiling data
    smart_config=smart_config,
)

# Generate recommendations for a table
recommendations = engine.generate_column_recommendations(
    table_name="user_events",
    schema_name="analytics",
)

for rec in recommendations:
    print(f"{rec.column_name}: {len(rec.suggested_checks)} checks")
    for check in rec.suggested_checks:
        print(f"  - {check.check_type}: {check.confidence:.2f}")
```

### PatternMatcher

```python
from baselinr.smart_selection.column_analysis import PatternMatcher

matcher = PatternMatcher()

# Match column name against patterns
matches = matcher.match_column("user_email")
for match in matches:
    print(f"{match.pattern_name}: {match.confidence}")
```

### PatternLearner

```python
from baselinr.smart_selection.learning import PatternLearner, PatternStore

learner = PatternLearner(min_occurrences=2)
patterns = learner.learn_from_config(config_dict)

store = PatternStore(storage_path=".baselinr_patterns.yaml")
store.add_patterns(patterns)
store.save()
```

## Migration from Manual Configuration

If you have existing column configurations, Smart Column Selection will:

1. **Respect explicit configs**: Your configurations always take precedence
2. **Skip configured columns**: Won't recommend checks for already-configured columns
3. **Learn from patterns**: Use your naming conventions to improve recommendations
4. **Merge recommendations**: Apply suggestions only to unconfigured columns

## Related Documentation

- [Smart Table Selection](./SMART_TABLE_SELECTION.md) - Phase 1 table selection
- [Data Validation](./DATA_VALIDATION.md) - Manual validation rules
- [Configuration Reference](../schemas/SCHEMA_REFERENCE.md) - Full config schema
