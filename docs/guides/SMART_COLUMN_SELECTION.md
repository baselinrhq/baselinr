# Smart Column Selection and Check Type Recommendations

> **Phase 2 of Intelligent Selection for Baselinr**

This document describes the Smart Column Selection feature, which automatically suggests appropriate data quality checks based on column characteristics.

## Overview

Building on Phase 1's usage-based table selection, Phase 2 adds column-level intelligence that:

1. **Analyzes column metadata and statistical properties** to infer appropriate checks
2. **Generates specific, actionable check recommendations** per column
3. **Learns from existing column naming patterns** and data characteristics
4. **Allows users to review and approve suggestions** before applying
5. **Avoids over-monitoring** by recommending only high-value checks

## Quick Start

```bash
# Generate column-level check recommendations
baselinr recommend --columns --config config.yaml

# Recommend for a specific table
baselinr recommend --columns --table analytics.user_events

# Show detailed reasoning for recommendations
baselinr recommend --columns --explain

# Preview changes without applying
baselinr recommend --columns --dry-run

# Apply recommendations to config
baselinr recommend --columns --apply
```

## Configuration

Add column-level settings to your `smart_selection` configuration:

```yaml
smart_selection:
  enabled: true

  # Table selection (Phase 1)
  tables:
    mode: "recommend"
    # ... existing table selection config

  # Column selection (Phase 2) - NEW
  columns:
    enabled: true
    mode: "recommend"  # Options: recommend | auto | disabled

    # Inference settings
    inference:
      use_profiling_data: true      # Use existing profile stats if available
      confidence_threshold: 0.7      # Minimum confidence to recommend
      max_checks_per_column: 3       # Avoid over-monitoring

      # Column prioritization
      prioritize:
        primary_keys: true
        foreign_keys: true
        timestamp_columns: true
        high_cardinality_strings: false  # Might be noisy

      # Check type preferences
      preferred_checks:
        - completeness
        - freshness
        - uniqueness

      avoided_checks:
        - custom_sql  # Don't auto-generate complex checks

    # Pattern overrides (teach the system your conventions)
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

    # Learning settings
    learning:
      enabled: true
      min_occurrences: 2
      storage_path: ".baselinr_patterns.yaml"
```

## How It Works

### 1. Column Analysis

The system extracts two types of signals from each column:

**Metadata Signals:**
- Column name and naming patterns (e.g., `created_at`, `user_id`, `email_address`)
- Data type (timestamp, numeric, string, boolean, JSON)
- Nullability constraints
- Primary key / foreign key status
- Column position (early columns often more important)
- Comments/descriptions if available

**Statistical Signals (from profiling data):**
- Cardinality (distinct value count)
- Null percentage
- Min/max values for numerics and timestamps
- Common value distribution
- String length patterns
- Format patterns (email, phone, UUID)
- Temporal patterns for timestamp columns

### 2. Check Type Inference

The system uses rule-based inference to map column characteristics to appropriate checks:

| Column Type | Signals | Suggested Checks |
|-------------|---------|------------------|
| **Timestamp** | `*_at`, `*_date`, `timestamp`, `created`, `updated` | Freshness, Completeness, Valid Range |
| **Identifier** | `*_id`, `*_key`, `uuid`, Primary Key | Uniqueness, Completeness, Format |
| **Numeric** | `amount`, `price`, `quantity`, `count` | Range, Distribution, Non-negative |
| **Email** | `email`, `*_email` | Format (email regex), Completeness |
| **Phone** | `phone`, `*_phone`, `mobile` | Format (phone pattern), Completeness |
| **Boolean** | `is_*`, `has_*`, `*_flag`, `active` | Completeness, Value Distribution |
| **Categorical** | Low cardinality strings, `status`, `type` | Allowed Values, Completeness |
| **JSON** | JSON/JSONB columns | Valid JSON, Schema Validation |

### 3. Confidence Scoring

Each recommendation receives a confidence score based on:

| Level | Score Range | Description |
|-------|-------------|-------------|
| **High** | 0.8 - 1.0 | Strong signals, low risk of false positive |
| **Medium** | 0.5 - 0.8 | Reasonable signals, might need validation |
| **Low** | 0.3 - 0.5 | Weak signals, suggest but don't auto-apply |

Confidence is boosted by:
- Multiple supporting signals (name + type + stats)
- Primary key or foreign key status
- Strong pattern matches
- Statistical confirmation

### 4. Pattern Learning

The system learns from your existing configurations:

```yaml
# Learned patterns (auto-generated)
learned_patterns:
  - pattern: "*_at"
    type: suffix
    suggested_checks: [freshness, completeness]
    confidence: 0.95
    source_columns: [created_at, updated_at, deleted_at]

  - pattern: "is_*"
    type: prefix
    suggested_checks: [completeness]
    confidence: 0.88
    source_columns: [is_active, is_verified, is_deleted]
```

## Output Format

### Recommendation Report

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

## CLI Usage Examples

### Basic Recommendations

```bash
# Recommend checks for all columns in recommended tables
baselinr recommend --columns --config config.yaml

# Output:
# Analyzing 15 recommended tables...
# Generated 247 column check recommendations
#   - High confidence: 156 (63%)
#   - Medium confidence: 71 (29%)
#   - Low confidence: 20 (8%)
```

### Detailed Explanation

```bash
baselinr recommend --columns --explain --table analytics.user_events

# Output:
# Table: analytics.user_events
# 45 columns analyzed, 23 checks recommended
#
# HIGH CONFIDENCE RECOMMENDATIONS:
# ✓ event_id (varchar)
#   → uniqueness check (confidence: 0.98)
#     Reason: Primary key pattern, 100% distinct values
#   → completeness check (confidence: 0.95)
#     Reason: Critical identifier field
#
# ✓ event_timestamp (timestamp)
#   → freshness check (confidence: 0.98)
#     Reason: Timestamp column, updated continuously
```

### Apply Recommendations

```bash
# Preview changes first
baselinr recommend --columns --dry-run

# Apply to configuration
baselinr recommend --columns --apply
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
│   ├── pattern_learner.py      # Learn from existing configs
│   └── pattern_store.py        # Persist learned patterns
├── config.py                   # Configuration schemas
├── recommender.py              # Orchestration engine
└── __init__.py
```

### Key Classes

| Class | Purpose |
|-------|---------|
| `MetadataAnalyzer` | Extracts column metadata from database schema |
| `StatisticalAnalyzer` | Analyzes profiling data for statistical signals |
| `PatternMatcher` | Matches column names against pattern rules |
| `CheckInferencer` | Maps column characteristics to check types |
| `ConfidenceScorer` | Calculates confidence scores for recommendations |
| `CheckPrioritizer` | Ranks and filters checks to avoid over-monitoring |
| `PatternLearner` | Learns patterns from existing configurations |
| `PatternStore` | Persists and manages learned patterns |
| `ColumnRecommendationEngine` | Orchestrates the column analysis pipeline |

### Data Flow

```
┌─────────────────┐
│  Database       │
│  Schema         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Metadata        │     │ Statistical     │
│ Analyzer        │     │ Analyzer        │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────────────────────────────┐
│           Pattern Matcher               │
│    (name patterns, type patterns)       │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│           Check Inferencer              │
│    (rules engine, check mapping)        │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────┐     ┌─────────────────┐
│ Confidence      │     │ Check           │
│ Scorer          │     │ Prioritizer     │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────────────────────────────┐
│        Recommendation Report            │
└─────────────────────────────────────────┘
```

## Supported Check Types

| Check Type | Description | Typical Columns |
|------------|-------------|-----------------|
| `completeness` | Non-null ratio | All columns |
| `uniqueness` | Distinct value ratio | IDs, keys |
| `freshness` | Data recency | Timestamps |
| `format_email` | Email format validation | Email columns |
| `format_phone` | Phone format validation | Phone columns |
| `format_uuid` | UUID format validation | UUID columns |
| `non_negative` | Values >= 0 | Amounts, counts |
| `range` | Min/max bounds | Numeric columns |
| `distribution` | Statistical distribution | Metrics |
| `allowed_values` | Enum validation | Status, type columns |
| `valid_json` | JSON structure validation | JSON columns |
| `referential_integrity` | Foreign key validation | FK columns |

## Best Practices

### 1. Start Conservative

Begin with high confidence threshold (0.8+) and gradually lower it as you validate recommendations:

```yaml
columns:
  inference:
    confidence_threshold: 0.8  # Start high
```

### 2. Use Explain Mode

Always review recommendations before applying:

```bash
baselinr recommend --columns --explain
```

### 3. Teach the System

Add pattern overrides for your specific conventions:

```yaml
columns:
  patterns:
    - match: "*_cents"  # Your monetary convention
      checks:
        - type: non_negative
        - type: range
          config:
            min: 0
            max: 100000000  # $1M in cents
```

### 4. Avoid Over-Monitoring

Limit checks per column to prevent alert fatigue:

```yaml
columns:
  inference:
    max_checks_per_column: 3
```

### 5. Prioritize Key Columns

Focus on primary keys and foreign keys first:

```yaml
columns:
  inference:
    prioritize:
      primary_keys: true
      foreign_keys: true
```

## Troubleshooting

### No Recommendations Generated

1. Ensure `smart_selection.columns.enabled: true`
2. Check that tables exist in recommendations
3. Verify database connection has schema access

### Low Confidence Scores

1. Run profiling to collect statistical data
2. Add pattern overrides for custom naming conventions
3. Check for unusual column naming patterns

### Too Many Recommendations

1. Increase `confidence_threshold`
2. Decrease `max_checks_per_column`
3. Add patterns to `avoided_checks`

## Integration with Existing Config

Column recommendations integrate seamlessly:

- **Explicit configs take precedence**: User-defined column checks are never overwritten
- **Merge mode**: Recommendations add to existing checks, don't replace
- **Exclusion support**: Use `exclude_from_recommendations` to skip columns
- **Partial acceptance**: Accept some recommendations, reject others

## Related Documentation

- [Smart Table Selection](SMART_TABLE_SELECTION.md) - Phase 1 table selection
- [Data Validation](DATA_VALIDATION.md) - Manual check configuration
- [Column Level Configs](COLUMN_LEVEL_CONFIGS.md) - Column-specific settings
- [Profiling Enrichment](PROFILING_ENRICHMENT.md) - Statistical data collection
