# Smart Column Selection and Check Type Recommendations

## Overview

Smart Column Selection (Phase 2) extends baselinr's intelligent selection capabilities to the column level. Building on Phase 1's usage-based table selection, this feature automatically suggests appropriate data quality checks based on column characteristics, reducing manual configuration effort while ensuring comprehensive monitoring.

## Key Features

- **Automatic Check Inference**: Analyzes column metadata and statistics to recommend appropriate data quality checks
- **Pattern Recognition**: Matches column names against common naming conventions to infer semantic meaning
- **Confidence Scoring**: Assigns confidence levels to recommendations for user review
- **Pattern Learning**: Learns from existing configurations to improve future recommendations
- **CLI Integration**: New command-line options for generating and applying recommendations

## Architecture

### Module Structure

```
baselinr/smart_selection/
├── column_analysis/           # Column analysis components
│   ├── __init__.py
│   ├── metadata_analyzer.py   # Extracts static column metadata
│   ├── statistical_analyzer.py # Analyzes profiling statistics
│   ├── pattern_matcher.py     # Matches naming patterns
│   └── check_inferencer.py    # Infers appropriate checks
├── scoring/                   # Scoring and prioritization
│   ├── __init__.py
│   ├── confidence_scorer.py   # Calculates confidence scores
│   └── check_prioritizer.py   # Ranks and filters checks
├── learning/                  # Pattern learning
│   ├── __init__.py
│   ├── pattern_learner.py     # Learns from existing configs
│   └── pattern_store.py       # Persists learned patterns
├── config.py                  # Extended configuration schema
└── recommender.py             # Orchestration engine
```

### Component Overview

#### 1. Metadata Analyzer (`metadata_analyzer.py`)

Extracts static column information from the database:

- **Column Properties**: Name, data type, nullability, position
- **Key Status**: Primary key, foreign key, references
- **Type Inference**: Semantic type classification (timestamp, identifier, numeric, etc.)
- **Pattern Detection**: Name pattern matching for semantic hints

```python
from baselinr.smart_selection.column_analysis import MetadataAnalyzer, ColumnMetadata

analyzer = MetadataAnalyzer(engine)
columns: List[ColumnMetadata] = analyzer.analyze_table("users", schema="public")
```

#### 2. Statistical Analyzer (`statistical_analyzer.py`)

Analyzes historical profiling data for dynamic insights:

- **Cardinality Analysis**: Distinct value counts, uniqueness ratios
- **Null Analysis**: Null counts, null percentages
- **Distribution Metrics**: Min/max, mean, stddev for numerics
- **Pattern Detection**: Format patterns in string data
- **Stability Analysis**: Value consistency over time

```python
from baselinr.smart_selection.column_analysis import StatisticalAnalyzer, ColumnStatistics

analyzer = StatisticalAnalyzer(storage_engine)
stats: ColumnStatistics = analyzer.analyze_column("users", "email", lookback_days=30)
```

#### 3. Pattern Matcher (`pattern_matcher.py`)

Matches column names against predefined and custom patterns:

**Built-in Patterns:**
- **Timestamps**: `*_at`, `*_date`, `*_time`, `timestamp`, `created`, `updated`
- **Identifiers**: `*_id`, `*_key`, `uuid`, `guid`
- **Email**: `*email*`, `*_email`, `email_*`
- **Phone**: `*phone*`, `*_phone`, `phone_*`
- **Boolean**: `is_*`, `has_*`, `*_flag`, `active`, `deleted`
- **Status/Category**: `*_status`, `*_type`, `*_state`, `*_category`
- **Monetary**: `*_amount`, `*_price`, `*_cost`, `*_revenue`, `*_balance`

```python
from baselinr.smart_selection.column_analysis import PatternMatcher, PatternMatch

matcher = PatternMatcher()
matches: List[PatternMatch] = matcher.match_column("created_at")
```

#### 4. Check Inferencer (`check_inferencer.py`)

Maps column characteristics to appropriate data quality checks:

**Supported Check Types:**
| Check Type | Description | Typical Triggers |
|------------|-------------|------------------|
| `completeness` | Null value monitoring | Non-nullable columns, critical fields |
| `uniqueness` | Duplicate detection | Primary keys, unique identifiers |
| `freshness` | Data recency checks | Timestamp columns (created_at, updated_at) |
| `format_email` | Email format validation | Email pattern in name |
| `format_phone` | Phone format validation | Phone pattern in name |
| `format_uuid` | UUID format validation | UUID/GUID identifiers |
| `non_negative` | Non-negative constraint | Price, amount, count columns |
| `range` | Value range validation | Numeric columns with known bounds |
| `allowed_values` | Categorical validation | Low-cardinality string columns |
| `distribution` | Distribution monitoring | Numeric columns with statistics |
| `referential_integrity` | Foreign key validation | Foreign key columns |
| `valid_json` | JSON structure validation | JSON/JSONB columns |
| `string_length` | String length constraints | Varchar columns |

```python
from baselinr.smart_selection.column_analysis import CheckInferencer, ColumnRecommendation

inferencer = CheckInferencer(confidence_threshold=0.7)
recommendation: ColumnRecommendation = inferencer.infer_checks(metadata, statistics)
```

#### 5. Confidence Scorer (`confidence_scorer.py`)

Calculates confidence scores based on:

- **Signal Strength**: Number and quality of supporting signals
- **Key Status**: Boost for primary/foreign keys
- **Statistical Support**: Higher confidence with profiling data
- **Pattern Match Quality**: Specificity of pattern matches

**Confidence Levels:**
- **High (0.8-1.0)**: Strong signals, low false positive risk
- **Medium (0.5-0.8)**: Reasonable signals, may need validation
- **Low (0.3-0.5)**: Weak signals, suggest but don't auto-apply

```python
from baselinr.smart_selection.scoring import ConfidenceScorer

scorer = ConfidenceScorer(boost_primary_keys=True)
score = scorer.score_recommendation(recommendation)
category = scorer.categorize_confidence(score)  # "high", "medium", "low"
```

#### 6. Check Prioritizer (`check_prioritizer.py`)

Ranks and filters recommendations to avoid over-monitoring:

- **Per-Column Limits**: Maximum checks per column (default: 5)
- **Per-Table Limits**: Maximum checks per table (default: 50)
- **Confidence Filtering**: Minimum confidence threshold
- **Preferred/Avoided Checks**: User preferences
- **Column Importance**: Prioritize key columns

```python
from baselinr.smart_selection.scoring import CheckPrioritizer, PrioritizationConfig

config = PrioritizationConfig(
    max_checks_per_column=3,
    min_confidence=0.7,
    preferred_checks=["completeness", "freshness"],
    avoided_checks=["distribution"]
)
prioritizer = CheckPrioritizer(config)
prioritized = prioritizer.prioritize_table_recommendations(recommendations)
```

#### 7. Pattern Learner (`pattern_learner.py`)

Learns naming patterns from existing configurations:

- **Suffix Patterns**: e.g., `*_at` → freshness check
- **Prefix Patterns**: e.g., `is_*` → completeness check
- **Exact Matches**: Specific column names
- **Occurrence Tracking**: Confidence based on frequency

```python
from baselinr.smart_selection.learning import PatternLearner, LearnedPattern

learner = PatternLearner(min_occurrences=2)
patterns: List[LearnedPattern] = learner.learn_from_config(existing_config)
```

#### 8. Pattern Store (`pattern_store.py`)

Persists learned patterns for reuse:

- **YAML/JSON Storage**: Human-readable format
- **Pattern Merging**: Updates existing patterns
- **Confidence Boosting**: Increases confidence with repetition
- **Export/Import**: Config-compatible format

```python
from baselinr.smart_selection.learning import PatternStore

store = PatternStore(storage_path=".baselinr_patterns.yaml")
store.add_patterns(learned_patterns)
store.save()

# Export to config format
config_patterns = store.export_to_config()
```

## Configuration

### Extended Smart Selection Config

```yaml
smart_selection:
  enabled: true

  # Phase 1: Table selection (unchanged)
  tables:
    mode: "recommend"
    # ... existing table config

  # Phase 2: Column selection (NEW)
  columns:
    enabled: true
    mode: "recommend"  # Options: recommend, auto, disabled

    inference:
      use_profiling_data: true        # Use existing profile stats
      confidence_threshold: 0.7       # Minimum confidence to recommend
      max_checks_per_column: 3        # Avoid over-monitoring

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
            confidence: 0.9
          - type: distribution
            confidence: 0.8

    # Pattern learning settings
    learning:
      enabled: true
      storage_path: ".baselinr_patterns.yaml"
      min_occurrences: 2
```

## CLI Usage

### Generate Column Recommendations

```bash
# Recommend checks for all columns in recommended tables
baselinr recommend --columns --config config.yaml

# Recommend for a specific table
baselinr recommend --columns --table analytics.user_events

# Show detailed reasoning
baselinr recommend --columns --explain

# Preview what would be applied
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

### Detailed Explain Output

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
    Reason: Email pattern in name
  → completeness check (confidence: 0.85)
    Reason: User identification field

MEDIUM CONFIDENCE RECOMMENDATIONS:
? event_type (varchar)
  → allowed_values check (confidence: 0.72)
    Reason: Low cardinality (12 distinct values)
    Note: Review allowed values list before applying
...
```

## Recommendation Output Format

The `recommendations.yaml` file includes column-level recommendations:

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
          - "Column name matches pattern: *_timestamp"
          - "Values updated frequently"
        suggested_checks:
          - type: freshness
            confidence: 0.98
            config:
              max_age_hours: 2

          - type: completeness
            confidence: 0.95
            config:
              min_completeness: 1.0

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

## Integration with Existing Config

Column recommendations integrate seamlessly with existing configurations:

1. **Explicit configs take precedence**: User-defined column configs are never overwritten
2. **Merging**: Recommendations merge with existing checks
3. **Conflict warnings**: Alerts when recommendations conflict with existing checks
4. **Exclusion support**: Columns can be excluded from recommendations

### Example Applied Config

After running `baselinr recommend --columns --apply`:

```yaml
profiling:
  tables:
    - table: user_events
      schema: analytics
      columns:
        - name: event_id
          # _comment: "High confidence (0.95) - Primary key pattern, unique values"
          checks:
            - type: uniqueness
              threshold: 1.0
            - type: completeness
              min_completeness: 1.0

        - name: event_timestamp
          # _comment: "High confidence (0.98) - Timestamp pattern"
          checks:
            - type: freshness
              max_age_hours: 2
            - type: completeness
              min_completeness: 1.0

        - name: user_email
          # _comment: "High confidence (0.92) - Email pattern"
          checks:
            - type: format_email
```

## Python SDK Usage

```python
from baselinr.smart_selection import (
    ColumnRecommendationEngine,
    RecommendationEngine,
)
from baselinr.smart_selection.config import SmartSelectionConfig

# Create configuration
config = SmartSelectionConfig(
    enabled=True,
    columns=ColumnSelectionConfig(
        enabled=True,
        mode="recommend",
        inference=ColumnInferenceConfig(
            confidence_threshold=0.7,
            max_checks_per_column=3,
        ),
    ),
)

# Create engine with storage for statistics
engine = RecommendationEngine(
    source_engine=source_engine,
    storage_engine=storage_engine,
    smart_config=config,
)

# Generate recommendations with columns
report = engine.generate_recommendations(include_columns=True)

# Access column recommendations
for table_rec in report.recommended_tables:
    print(f"Table: {table_rec.schema}.{table_rec.table}")
    for col_rec in table_rec.column_recommendations:
        print(f"  Column: {col_rec.column} ({col_rec.confidence:.2f})")
        for check in col_rec.suggested_checks:
            print(f"    - {check['type']}: {check['confidence']:.2f}")
```

## Testing

The implementation includes comprehensive unit tests:

```bash
# Run all column selection tests
pytest tests/test_column_analysis.py tests/test_column_scoring.py \
       tests/test_column_learning.py tests/test_column_recommendation_integration.py -v

# Test count: 76 tests covering:
# - Metadata analysis (3 tests)
# - Pattern matching (11 tests)
# - Statistics analysis (3 tests)
# - Check inference (10 tests)
# - Confidence scoring (6 tests)
# - Check prioritization (9 tests)
# - Pattern learning (6 tests)
# - Pattern storage (12 tests)
# - Integration scenarios (13 tests)
```

## Performance Considerations

- **Caching**: Column metadata is cached during analysis
- **Incremental Analysis**: Only analyze new/changed columns
- **Parallel Processing**: Multiple tables analyzed concurrently
- **Lazy Loading**: Statistics fetched only when needed
- **Configurable Limits**: Per-column and per-table check limits

## Best Practices

1. **Start with Recommend Mode**: Review suggestions before applying
2. **Use Explain**: Understand reasoning behind recommendations
3. **Set Appropriate Thresholds**: Higher confidence = fewer false positives
4. **Learn from Existing Configs**: Enable pattern learning for custom conventions
5. **Review Low Confidence**: Manual inspection for uncertain recommendations
6. **Iterate**: Refine patterns based on feedback

## Migration from Phase 1

If you're already using Phase 1 smart table selection:

1. Column selection is **opt-in** - existing configs work unchanged
2. Add `columns.enabled: true` to enable
3. Start with `mode: recommend` to preview
4. Gradually increase confidence threshold as trust builds

## Troubleshooting

### No Recommendations Generated

- Check if `smart_selection.columns.enabled` is `true`
- Verify confidence threshold isn't too high
- Ensure tables have been profiled (for statistics-based inference)

### Too Many Recommendations

- Increase `confidence_threshold`
- Decrease `max_checks_per_column`
- Add checks to `avoided_checks` list

### Missing Expected Checks

- Lower `confidence_threshold`
- Add custom patterns for domain-specific naming
- Enable `use_profiling_data` for statistics-based inference
