# Smart Table Selection - Quick Start Guide

Get started with intelligent, usage-based table selection in 5 minutes.

## What is Smart Table Selection?

Instead of manually specifying every table to monitor, Baselinr can automatically recommend tables based on:
- **Query frequency**: How often tables are accessed
- **Usage recency**: When tables were last queried
- **Data freshness**: When tables were last updated
- **Table characteristics**: Size, type, and metadata

## Quick Start

### Step 1: Basic Configuration

Create or update your `config.yaml`:

```yaml
source:
  type: snowflake  # or postgres, bigquery, redshift, etc.
  account: myaccount
  database: prod
  warehouse: compute_wh
  username: baselinr_user
  password: ${SNOWFLAKE_PASSWORD}

storage:
  connection:
    type: postgres
    host: localhost
    database: baselinr_metadata

smart_selection:
  enabled: true
  mode: "recommend"  # Start with recommend mode

profiling:
  tables: []  # Can be empty - smart selection will populate
```

### Step 2: Generate Recommendations

Run the recommend command:

```bash
baselinr recommend --config config.yaml --explain
```

You'll see output like:

```
📊 Generating smart table recommendations...
   Database: prod (snowflake)
   Lookback period: 30 days

✅ Analysis complete!
   Tables analyzed: 156
   Recommended: 23
   Excluded: 133

Confidence distribution:
   high (0.8+): 15 tables
   medium (0.6-0.8): 6 tables
   low (<0.6): 2 tables

Top recommendations:

1. analytics.user_events (confidence: 0.95, score: 92.3)
   • Heavily used: 1,247 queries (41.6 per day)
   • Last queried 2 hours ago
   • Updated daily
   • Medium table with 5,000,000 rows
   Suggested checks: freshness, row_count, completeness, numeric_distribution

2. analytics.revenue_summary (confidence: 0.88, score: 87.1)
   • Actively queried: 423 queries (14.1 per day)
   • Last queried 1 day ago
   • Large table with 12,500,000 rows
   Suggested checks: freshness, numeric_distribution

... and 21 more (see recommendations.yaml)

💾 Saved recommendations to: recommendations.yaml

✨ Next steps:
   1. Review recommendations in: recommendations.yaml
   2. Apply with: baselinr recommend --config config.yaml --apply
   3. Or manually add tables to your config file
```

### Step 3: Review Recommendations

Check `recommendations.yaml`:

```yaml
metadata:
  generated_at: "2025-01-15T10:30:00"
  lookback_days: 30
  database_type: "snowflake"
  summary:
    total_tables_analyzed: 156
    total_recommended: 23
    total_excluded: 133

recommended_tables:
  - schema: analytics
    table: user_events
    confidence: 0.95
    reasons:
      - "Heavily used: 1,247 queries (41.6 per day)"
      - "Last queried 2 hours ago"
      - "Updated daily"
    suggested_checks:
      - freshness
      - row_count
      - completeness
  
  # ... more recommendations ...
```

### Step 4: Apply Recommendations

When you're ready:

```bash
baselinr recommend --config config.yaml --apply
```

This will:
1. Show a summary of changes
2. Ask for confirmation
3. Backup your config to `config.yaml.backup`
4. Add recommended tables to `profiling.tables`

### Step 5: Run Profiling

```bash
baselinr profile --config config.yaml
```

Baselinr will now profile all recommended tables!

## Customization

### Adjust Criteria

Make recommendations more or less strict:

```yaml
smart_selection:
  criteria:
    min_query_count: 50      # More strict (default: 10)
    min_queries_per_day: 5   # More strict (default: 1)
    lookback_days: 60        # Longer period (default: 30)
    
    exclude_patterns:
      - "temp_*"
      - "*_backup"
      - "dev_*"
```

### Focus on Specific Schema

```bash
baselinr recommend --config config.yaml --schema analytics
```

### Adjust Scoring Weights

Prioritize different factors:

```yaml
smart_selection:
  criteria:
    weights:
      query_frequency: 0.6   # Emphasize usage (default: 0.4)
      query_recency: 0.2     # Default: 0.25
      write_activity: 0.1    # Default: 0.2
      table_size: 0.1        # Default: 0.15
```

## Auto Mode (Advanced)

Once comfortable with recommendations, enable auto mode:

```yaml
smart_selection:
  mode: "auto"
  
  auto_apply:
    confidence_threshold: 0.85  # Only auto-apply high confidence
    max_tables: 50              # Safety limit
```

Then just run:

```bash
baselinr profile --config config.yaml
```

Baselinr will automatically select and profile high-confidence tables!

## Combining with Explicit Configs

Smart selection works alongside explicit table configurations:

```yaml
profiling:
  tables:
    # Critical tables (always included)
    - schema: core
      table: customers
    - schema: analytics
      table: revenue_daily

smart_selection:
  enabled: true
  auto_apply:
    skip_existing: true  # Won't duplicate above tables
```

## Database-Specific Tips

### Snowflake

Best experience with full metadata:

```yaml
source:
  type: snowflake
  role: ACCOUNTADMIN  # Or role with ACCOUNT_USAGE access
```

Without `ACCOUNT_USAGE` access, it falls back to `INFORMATION_SCHEMA` (basic metadata only).

### PostgreSQL

Works well with pg_stat_user_tables:

```yaml
smart_selection:
  criteria:
    min_query_count: 20  # Scan counts used as proxy
```

### BigQuery

Limited to dataset level:

```bash
# Recommend per dataset
baselinr recommend --config config.yaml --schema my_dataset
```

### MySQL / SQLite

Limited query history:

```yaml
smart_selection:
  criteria:
    min_rows: 1000      # Focus on size-based selection
  auto_apply:
    confidence_threshold: 0.6  # Lower threshold
```

## Troubleshooting

### No Recommendations

Try more lenient criteria:

```yaml
smart_selection:
  criteria:
    min_query_count: 5
    min_queries_per_day: 0.5
    lookback_days: 60
```

### Too Many Recommendations

Try stricter criteria:

```yaml
smart_selection:
  criteria:
    min_query_count: 100
    min_queries_per_day: 5
  auto_apply:
    max_tables: 25
```

### Permission Errors

Snowflake:
```sql
-- Grant access to query history
GRANT USAGE ON DATABASE SNOWFLAKE TO ROLE baselinr_role;
GRANT USAGE ON SCHEMA ACCOUNT_USAGE TO ROLE baselinr_role;
```

PostgreSQL:
```sql
-- Should already have access to pg_stat_user_tables
```

## Next Steps

- **Review Periodically**: Run `baselinr recommend --refresh` monthly
- **Tune Criteria**: Adjust based on your recommendations
- **Combine Approaches**: Use both smart selection and explicit configs
- **Monitor Results**: Track profiling coverage and data quality

For more details, see the [full Smart Table Selection guide](SMART_TABLE_SELECTION.md).

## Common Patterns

### Pattern: Discovery Phase

```bash
# 1. Generate recommendations
baselinr recommend --config config.yaml --explain

# 2. Review top 10
head -n 50 recommendations.yaml

# 3. Start with high-confidence only
# Edit config: confidence_threshold: 0.9, max_tables: 10

# 4. Apply
baselinr recommend --config config.yaml --apply

# 5. Profile
baselinr profile --config config.yaml
```

### Pattern: Schema-by-Schema

```bash
# Analytics schema
baselinr recommend --config config.yaml --schema analytics --output recs_analytics.yaml

# Core schema
baselinr recommend --config config.yaml --schema core --output recs_core.yaml

# Review separately, then apply
```

### Pattern: Conservative Auto

```yaml
smart_selection:
  mode: "auto"
  criteria:
    min_query_count: 100
    min_queries_per_day: 10
  auto_apply:
    confidence_threshold: 0.95
    max_tables: 20
```

Then schedule:
```bash
# Cron: Daily at 2 AM
0 2 * * * cd /path/to/baselinr && baselinr profile --config config.yaml
```

## Resources

- [Full Documentation](SMART_TABLE_SELECTION.md)
- [Configuration Reference](../../examples/config_smart_selection.yml)
- [API Usage](SMART_TABLE_SELECTION.md#api-usage)
- [Database-Specific Notes](SMART_TABLE_SELECTION.md#database-specific-notes)
