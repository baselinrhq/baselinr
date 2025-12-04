# Smart Column Selection and Check Type Recommendations

## Overview

Smart Column Selection (Phase 2) extends baselinr's intelligent selection capabilities to the column level. Building on Phase 1's usage-based table selection, this feature automatically analyzes column characteristics and recommends appropriate data quality checks.

## Key Features

- **Automatic Check Inference**: Analyzes column metadata and statistics to suggest appropriate checks
- **Pattern-Based Recognition**: Identifies common column naming patterns (timestamps, IDs, emails, etc.)
- **Confidence Scoring**: Assigns confidence levels to recommendations based on signal strength
- **Pattern Learning**: Learns from existing configurations to improve future recommendations
- **Customizable Rules**: Supports user-defined patterns and check preferences

## Architecture

### Module Structure

```
baselinr/smart_selection/
├── column_analysis/
│   ├── __init__.py
│   ├── metadata_analyzer.py    # Extract column metadata signals
│   ├── statistical_analyzer.py # Analyze profiling statistics
│   ├── pattern_matcher.py      # Match naming patterns
│   └── check_inferencer.py     # Infer appropriate checks
├── scoring/
│   ├── __init__.py
│   ├── confidence_scorer.py    # Calculate confidence scores
│   └── check_prioritizer.py    # Rank and filter checks
├── learning/
│   ├── __init__.py
│   ├── pattern_learner.py      # Learn from existing configs
│   └── pattern_store.py        # Persist learned patterns
├── config.py                   # Extended configuration schema
└── recommender.py              # Recommendation engine
```

### Components

#### 1. Metadata Analyzer (`metadata_analyzer.py`)

Extracts static metadata signals from database columns using SQLAlchemy inspection:

- Column name and naming patterns
- Data type (with precision/scale for numerics)
- Nullability constraints
- Primary key / foreign key status
- Column position
- Default values and comments

```python
from baselinr.smart_selection.column_analysis import MetadataAnalyzer, ColumnMetadata

analyzer = MetadataAnalyzer(engine)
columns = analyzer.analyze_table("users", schema="public")
# Returns List[ColumnMetadata] with inferred semantic types
```

#### 2. Statistical Analyzer (`statistical_analyzer.py`)

Analyzes historical profiling data to derive dynamic column properties:

- Row count and null percentage
- Distinct value count and uniqueness ratio
- Min/max values for numerics
- Value distribution for categoricals
- String length patterns
- Temporal patterns for timestamps

```python
from baselinr.smart_selection.column_analysis import StatisticalAnalyzer

analyzer = StatisticalAnalyzer(storage_engine)
stats = analyzer.analyze_column("users", "email", lookback_days=30)
# Returns ColumnStatistics with cardinality, patterns, stability info
```

#### 3. Pattern Matcher (`pattern_matcher.py`)

Matches column names against predefined and custom patterns:

**Built-in Patterns:**
- Timestamps: `*_at`, `*_date`, `*_time`, `created`, `updated`
- Identifiers: `*_id`, `*_key`, `uuid`, `guid`
- Contact: `email`, `phone`, `address`
- Monetary: `amount`, `price`, `total`, `revenue`
- Boolean: `is_*`, `has_*`, `*_flag`
- Status: `status`, `state`, `type`

```python
from baselinr.smart_selection.column_analysis import PatternMatcher

matcher = PatternMatcher()
matches = matcher.match_column("created_at")
# Returns [PatternMatch(pattern_name="timestamp", confidence=0.9, ...)]
```

#### 4. Check Inferencer (`check_inferencer.py`)

Maps column characteristics to appropriate data quality checks:

| Column Type | Suggested Checks |
|-------------|-----------------|
| Timestamp | freshness, completeness, valid_range |
| Identifier (PK) | uniqueness, completeness |
| Identifier (FK) | referential_integrity, completeness |
| Email | format_email, completeness |
| Numeric (monetary) | non_negative, range, distribution |
| Categorical | allowed_values, completeness |
| Boolean | completeness |
| JSON | valid_json |

```python
from baselinr.smart_selection.column_analysis import CheckInferencer

inferencer = CheckInferencer()
result = inferencer.infer_checks(metadata, statistics)
# Returns ColumnRecommendation with suggested checks and confidence
```

#### 5. Confidence Scorer (`confidence_scorer.py`)

Calculates confidence scores based on:

- Number and strength of signals
- Primary/foreign key status (boosts confidence)
- Availability of statistical data
- Pattern match quality

**Confidence Levels:**
- **High (0.8-1.0)**: Strong signals, safe to auto-apply
- **Medium (0.5-0.8)**: Reasonable signals, review recommended
- **Low (0.3-0.5)**: Weak signals, manual verification needed

#### 6. Check Prioritizer (`check_prioritizer.py`)

Ranks and filters recommendations to avoid over-monitoring:

- Filters by minimum confidence threshold
- Limits checks per column (default: 5)
- Limits total checks per table (default: 50)
- Boosts preferred check types
- Filters avoided check types
- Prioritizes key columns

#### 7. Pattern Learner (`pattern_learner.py`)

Learns from existing configurations:

- Identifies suffix patterns (`*_at` → freshness)
- Identifies prefix patterns (`is_*` → completeness)
- Tracks which checks are commonly applied together
- Builds confidence from repeated observations

#### 8. Pattern Store (`pattern_store.py`)

Persists learned patterns for reuse:

- Stores patterns in `.baselinr_patterns.yaml`
- Merges new patterns with existing ones
- Exports patterns to config format
- Supports confidence boosting over time

## Configuration

### Column Selection Settings

```yaml
smart_selection:
  enabled: true
  
  # Table selection (Phase 1)
  tables:
    mode: "recommend"
    # ... existing settings
  
  # Column selection (Phase 2) - NEW
  columns:
    enabled: true
    mode: "recommend"  # Options: recommend, auto, disabled
    
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
            confidence: 0.9
          - type: distribution
            confidence: 0.8
    
    # Pattern learning settings
    learning:
      enabled: true
      min_occurrences: 2
      store_path: ".baselinr_patterns.yaml"
```

## CLI Usage

### Generate Column Recommendations

```bash
# Recommend checks for all columns in recommended tables
baselinr recommend --columns --config config.yaml

# Recommend for specific table
baselinr recommend --columns --table analytics.user_events

# Show detailed reasoning
baselinr recommend --columns --explain

# Preview changes without applying
baselinr recommend --columns --dry-run

# Apply high-confidence recommendations
baselinr recommend --columns --apply
```

### Example Output

```
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
○ user_agent (varchar)
  → completeness check (confidence: 0.65)
    Reason: Standard HTTP field

LOW CONFIDENCE SUGGESTIONS:
? metadata_json (json)
  → valid_json check (confidence: 0.45)
    Reason: JSON column detected, schema unknown
```

## Recommendation Output Format

The `recommendations.yaml` file includes column-level recommendations:

```yaml
# Generated: 2025-01-15

metadata:
  generated_at: "2025-01-15T10:30:00"
  lookback_days: 30
  database_type: postgresql
  column_summary:
    total_columns_analyzed: 247
    total_checks_recommended: 389
    confidence_distribution:
      high: 156
      medium: 71
      low: 20

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
    note: "Consider manual inspection to define schema"
```

## Supported Check Types

| Check Type | Description | Common Signals |
|------------|-------------|----------------|
| `completeness` | Validates non-null values | Required fields, identifiers |
| `uniqueness` | Validates distinct values | Primary keys, IDs |
| `freshness` | Validates data recency | Timestamp columns |
| `format_email` | Validates email format | Email columns |
| `format_phone` | Validates phone format | Phone columns |
| `format_url` | Validates URL format | URL columns |
| `format_uuid` | Validates UUID format | UUID columns |
| `non_negative` | Validates >= 0 | Counts, amounts, prices |
| `range` | Validates min/max bounds | Numeric columns with stats |
| `distribution` | Monitors value distribution | Numeric columns |
| `allowed_values` | Validates against enum | Categorical columns |
| `referential_integrity` | Validates FK references | Foreign key columns |
| `valid_json` | Validates JSON structure | JSON columns |
| `valid_date_range` | Validates date bounds | Date/timestamp columns |

## Pattern Learning

The system learns from your existing configurations to improve recommendations:

```yaml
# Learned patterns (stored in .baselinr_patterns.yaml)
learned_patterns:
  - pattern: "*_at"
    pattern_type: suffix
    suggested_checks: [freshness, completeness]
    confidence: 0.92
    occurrence_count: 15
    
  - pattern: "is_*"
    pattern_type: prefix
    suggested_checks: [completeness]
    confidence: 0.88
    occurrence_count: 8
```

To trigger learning from existing config:

```python
from baselinr.smart_selection.learning import PatternLearner, PatternStore

learner = PatternLearner()
patterns = learner.learn_from_config(existing_config)

store = PatternStore(".baselinr_patterns.yaml")
store.add_patterns(patterns)
store.save()
```

## Integration with Existing Features

### Phase 1 Table Selection

Column recommendations work seamlessly with table recommendations:

```bash
# First, get table recommendations
baselinr recommend --config config.yaml

# Then, add column recommendations to recommended tables
baselinr recommend --columns --config config.yaml
```

### Profiling Integration

When profiling data is available, the system uses it for better recommendations:

- Cardinality analysis for uniqueness checks
- Value distribution for allowed_values checks
- Stability analysis for distribution monitoring
- Pattern detection for format validation

### Configuration Merging

When applying recommendations:

- Existing explicit configs take precedence
- New recommendations merge with existing column configs
- Conflicts are warned but not overwritten
- `exclude_from_recommendations: true` respected

## Performance Considerations

- **Wide Tables**: For tables with 100+ columns, analysis is batched
- **Profiling Data**: Statistical analysis uses cached profile results
- **Pattern Compilation**: Regex patterns are compiled once and reused
- **Incremental Analysis**: Only new columns analyzed when possible

## Testing

The implementation includes comprehensive tests:

```bash
# Run column analysis tests
pytest tests/test_column_analysis.py -v

# Run scoring tests
pytest tests/test_column_scoring.py -v

# Run learning tests  
pytest tests/test_column_learning.py -v

# Run integration tests
pytest tests/test_column_recommendation_integration.py -v
```

## API Reference

### Key Classes

```python
from baselinr.smart_selection import (
    # Main engines
    ColumnRecommendationEngine,
    RecommendationEngine,
    
    # Output types
    ColumnCheckRecommendation,
    RecommendationReport,
)

from baselinr.smart_selection.column_analysis import (
    # Analyzers
    MetadataAnalyzer,
    StatisticalAnalyzer,
    PatternMatcher,
    CheckInferencer,
    
    # Data types
    ColumnMetadata,
    ColumnStatistics,
    PatternMatch,
    InferredCheck,
)

from baselinr.smart_selection.scoring import (
    ConfidenceScorer,
    CheckPrioritizer,
    PrioritizationConfig,
)

from baselinr.smart_selection.learning import (
    PatternLearner,
    PatternStore,
    LearnedPattern,
)
```

### Programmatic Usage

```python
from sqlalchemy import create_engine
from baselinr.smart_selection import ColumnRecommendationEngine
from baselinr.smart_selection.config import SmartSelectionConfig

# Create engine
source_engine = create_engine("postgresql://...")
storage_engine = create_engine("postgresql://...")

# Create recommendation engine
config = SmartSelectionConfig(columns={"enabled": True})
rec_engine = ColumnRecommendationEngine(
    source_engine=source_engine,
    storage_engine=storage_engine,
    smart_config=config,
)

# Generate recommendations for a table
recommendations = rec_engine.generate_column_recommendations(
    table_name="user_events",
    schema="analytics",
)

for rec in recommendations:
    print(f"{rec.column_name}: {len(rec.suggested_checks)} checks")
    for check in rec.suggested_checks:
        print(f"  - {check.check_type}: {check.confidence:.2f}")
```

## Changelog

### Version 1.0.0 (Phase 2)

- Initial implementation of column-level recommendations
- Metadata analyzer with semantic type inference
- Statistical analyzer for profiling data integration
- Pattern matcher with 20+ built-in patterns
- Check inferencer supporting 14 check types
- Confidence scorer with configurable weights
- Check prioritizer with preference/avoidance support
- Pattern learner for configuration-based learning
- Pattern store for persistence
- CLI integration with `--columns` flag
- Comprehensive test coverage (76 new tests)
