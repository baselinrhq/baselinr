# Smart Column Selection and Check Type Recommendations

## Overview

Phase 2 of intelligent selection for baselinr adds column-level intelligence that automatically suggests appropriate data quality checks based on column characteristics. This builds upon Phase 1's usage-based table selection.

## Key Features

### 1. Automatic Check Inference
The system analyzes column metadata and statistical properties to automatically recommend appropriate data quality checks:

- **Timestamp columns** → Freshness, completeness, valid date range checks
- **Identifier columns** → Uniqueness, completeness, format validation checks
- **Email columns** → Format validation (email regex), completeness checks
- **Numeric columns** → Range validation, non-negative constraints, distribution monitoring
- **Boolean columns** → Completeness, value distribution checks
- **Categorical columns** → Allowed values, completeness checks
- **JSON columns** → Valid JSON structure checks

### 2. Confidence Scoring
Each recommendation includes a confidence score (0.0-1.0) based on:
- Strength of signals (clear naming patterns = high confidence)
- Multiple supporting signals (name + type + stats = higher confidence)
- Column importance (primary key, foreign key = higher confidence)
- Statistical data availability

Confidence levels:
- **High (0.8-1.0)**: Strong signals, low risk of false positive
- **Medium (0.5-0.8)**: Reasonable signals, might need user validation
- **Low (0.3-0.5)**: Weak signals, suggest but don't auto-apply

### 3. Pattern Learning
The system can learn from existing configurations to improve future recommendations:
- Observes user's existing check configurations
- Identifies patterns in naming conventions and check preferences
- Builds a custom pattern library for the workspace
- Uses learned patterns to improve future recommendations

## Architecture

### New Modules

```
baselinr/smart_selection/
├── column_analysis/
│   ├── __init__.py
│   ├── metadata_analyzer.py    # Extract column metadata signals
│   ├── statistical_analyzer.py # Analyze profiling data
│   ├── pattern_matcher.py      # Match naming patterns
│   └── check_inferencer.py     # Map signals to check types
├── scoring/
│   ├── __init__.py
│   ├── confidence_scorer.py    # Calculate confidence scores
│   └── check_prioritizer.py    # Rank and filter recommendations
└── learning/
    ├── __init__.py
    ├── pattern_learner.py      # Learn from existing configs
    └── pattern_store.py        # Persist learned patterns
```

### Key Classes

#### Column Analysis

| Class | Description |
|-------|-------------|
| `MetadataAnalyzer` | Extracts metadata signals from database columns using SQLAlchemy inspection |
| `StatisticalAnalyzer` | Analyzes historical profiling data for statistical signals |
| `PatternMatcher` | Matches column names against naming convention patterns |
| `CheckInferencer` | Maps column characteristics to appropriate check types |
| `ColumnMetadata` | Data class representing column metadata |
| `ColumnStatistics` | Data class representing column statistical properties |
| `InferredCheck` | Data class representing a recommended check |

#### Scoring

| Class | Description |
|-------|-------------|
| `ConfidenceScorer` | Calculates confidence scores for recommendations |
| `CheckPrioritizer` | Ranks and filters checks to avoid over-monitoring |
| `PrioritizationConfig` | Configuration for prioritization behavior |

#### Learning

| Class | Description |
|-------|-------------|
| `PatternLearner` | Learns patterns from existing configurations |
| `PatternStore` | Persists and manages learned patterns |
| `LearnedPattern` | Data class representing a learned pattern |

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
    mode: "recommend"  # Options: recommend | auto | disabled
    
    # Inference settings
    inference:
      use_profiling_data: true       # Use existing profile stats
      confidence_threshold: 0.7      # Minimum confidence to recommend
      max_checks_per_column: 3       # Avoid over-monitoring
      
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
    
    # Pattern overrides
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
    
    # Pattern learning
    learning:
      enabled: true
      min_occurrences: 2
      min_confidence: 0.7
      storage_path: ".baselinr_patterns.yaml"
```

## CLI Commands

### New Options for `baselinr recommend`

```bash
# Recommend checks for all columns in recommended/configured tables
baselinr recommend --columns --config config.yaml

# Recommend for specific table
baselinr recommend --columns --table analytics.user_events

# Show detailed reasoning
baselinr recommend --columns --explain

# Apply column recommendations
baselinr recommend --columns --apply

# Preview what checks would be added without applying
baselinr recommend --columns --dry-run
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

### Detailed View

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
      
      - column: user_email
        data_type: varchar
        confidence: 0.92
        signals:
          - "Email pattern match"
          - "Format validation recommended"
        suggested_checks:
          - type: format_email
            confidence: 0.95
            config:
              pattern: "email"
          - type: completeness
            confidence: 0.90
            config:
              min_completeness: 0.99

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

## Supported Check Types

| Check Type | Description | Typical Columns |
|------------|-------------|-----------------|
| `completeness` | Validates non-null ratio | All critical columns |
| `uniqueness` | Validates distinct value ratio | Primary keys, identifiers |
| `freshness` | Validates data recency | Timestamp columns |
| `format_email` | Validates email format | Email columns |
| `format_phone` | Validates phone format | Phone columns |
| `format_uuid` | Validates UUID format | UUID columns |
| `format_url` | Validates URL format | URL columns |
| `non_negative` | Validates non-negative values | Amounts, counts, prices |
| `range` | Validates value range | Numeric columns |
| `distribution` | Monitors value distribution | Numeric metrics |
| `allowed_values` | Validates categorical values | Status, type columns |
| `referential_integrity` | Validates foreign key references | Foreign key columns |
| `valid_json` | Validates JSON structure | JSON columns |
| `valid_date_range` | Validates date boundaries | Date/timestamp columns |

## Pattern Matching Rules

The pattern matcher includes built-in rules for common naming conventions:

### Timestamp Patterns
- `*_at`, `*_date`, `*_time`, `timestamp`
- `created*`, `updated*`, `deleted*`, `modified*`

### Identifier Patterns
- `*_id`, `*_key`, `*_uuid`, `*_guid`
- `id`, `pk`, `primary_key`

### Format Patterns
- `*email*`, `*phone*`, `*url*`, `*address*`
- `*status*`, `*type*`, `*state*`

### Numeric Patterns
- `*amount*`, `*price*`, `*cost*`, `*revenue*`
- `*count*`, `*quantity*`, `*total*`, `*balance*`

### Boolean Patterns
- `is_*`, `has_*`, `can_*`, `should_*`
- `*_flag`, `*_enabled`, `*_active`

## Testing

The implementation includes comprehensive unit tests:

| Test File | Coverage |
|-----------|----------|
| `test_column_analysis.py` | Metadata analyzer, pattern matcher, check inferencer |
| `test_column_scoring.py` | Confidence scorer, check prioritizer |
| `test_column_learning.py` | Pattern learner, pattern store |
| `test_column_recommendation_integration.py` | End-to-end integration tests |

Run tests with:

```bash
pytest tests/test_column_analysis.py tests/test_column_scoring.py \
       tests/test_column_learning.py tests/test_column_recommendation_integration.py -v
```

## Best Practices

### 1. Start with `--dry-run`
Always preview recommendations before applying:
```bash
baselinr recommend --columns --dry-run
```

### 2. Use `--explain` for Review
Understand the reasoning behind each recommendation:
```bash
baselinr recommend --columns --explain --table your_table
```

### 3. Configure Confidence Threshold
Adjust based on your tolerance for false positives:
```yaml
smart_selection:
  columns:
    inference:
      confidence_threshold: 0.8  # Higher = fewer but more accurate recommendations
```

### 4. Enable Pattern Learning
Let the system learn from your existing configurations:
```yaml
smart_selection:
  columns:
    learning:
      enabled: true
      min_occurrences: 3  # Require 3+ occurrences to learn a pattern
```

### 5. Define Custom Patterns
Override or extend built-in patterns for your domain:
```yaml
smart_selection:
  columns:
    patterns:
      - match: "company_*_id"
        checks:
          - type: uniqueness
          - type: format_alphanumeric
        confidence: 0.95
```

## Backward Compatibility

- Column recommendations are **opt-in** via the `--columns` flag
- Existing configurations continue working unchanged
- Phase 1 table recommendations work independently
- Explicit column configs always take precedence over recommendations

## Performance Considerations

- Column analysis can be expensive for wide tables (100+ columns)
- Statistical analysis requires historical profiling data
- Use `--table` flag to analyze specific tables
- Recommendations are cached during a session

## Future Enhancements

Potential future improvements:
- Industry-specific pattern profiles (healthcare, finance, e-commerce)
- Composite check recommendations (e.g., start_date < end_date)
- Severity levels for recommended checks (error vs. warning)
- Integration with external data quality rule libraries
- Machine learning-based pattern detection
