# Smart Table Selection with Usage-Based Intelligence

## Overview

Smart Table Selection is an intelligent feature in Baselinr that automatically recommends tables to monitor based on database usage patterns, query frequency, and metadata analysis. This reduces configuration overhead by identifying the most important tables to profile without manual specification.

## Key Features

- **Automated Discovery**: Queries database metadata to identify actively-used tables
- **Usage-Based Scoring**: Ranks tables based on query frequency, recency, and write activity
- **Intelligent Recommendations**: Generates actionable suggestions with confidence scores
- **Transparent Reasoning**: Explains WHY each table was selected or excluded
- **Flexible Modes**: Supports recommendation-only or auto-apply modes
- **Configuration Override**: Works alongside explicit table configurations

## How It Works

### 1. Metadata Collection

The system queries database-specific system tables to collect:

- **Query Statistics**: Query count, frequency, and recency
- **Table Characteristics**: Row counts, table sizes, last modified timestamps
- **Write Activity**: Recent data updates and modifications
- **Table Types**: Distinguishes between tables, views, and materialized views

Supported databases:
- **Snowflake**: `ACCOUNT_USAGE.QUERY_HISTORY`, `TABLE_STORAGE_METRICS`
- **BigQuery**: `INFORMATION_SCHEMA.JOBS_BY_PROJECT`, `TABLE_STORAGE`
- **PostgreSQL**: `pg_stat_user_tables`, `pg_class`
- **Redshift**: `STL_QUERY`, `SVV_TABLE_INFO`
- **MySQL**: `INFORMATION_SCHEMA.TABLES` (limited query history)
- **SQLite**: `sqlite_master` (basic metadata only)

### 2. Scoring & Ranking

Tables are scored based on multiple factors:

- **Query Frequency** (40% weight): How often the table is queried
- **Query Recency** (25% weight): How recently the table was accessed
- **Write Activity** (20% weight): How recently data was modified
- **Table Size** (15% weight): Optimal size for monitoring (favors medium-sized tables)

Each factor is scored 0-100, then weighted to produce a total score. Tables also receive a confidence score (0.0-1.0) based on metadata completeness.

### 3. Recommendation Generation

The engine:
1. Filters tables based on criteria (minimum query count, row count thresholds, etc.)
2. Applies exclude patterns to skip temporary or backup tables
3. Sorts by score to identify top candidates
4. Generates human-readable reasons for each recommendation
5. Suggests appropriate profiling checks based on table characteristics

## Configuration

### Basic Setup

Add a `smart_selection` section to your Baselinr configuration:

```yaml
smart_selection:
  enabled: true
  mode: "recommend"  # or "auto" for automatic application
  
  criteria:
    min_query_count: 10          # Minimum queries in lookback period
    min_queries_per_day: 1       # Minimum average queries per day
    lookback_days: 30            # Days to analyze
    exclude_patterns:
      - "temp_*"
      - "*_backup"
      - "staging_*"
    
    # Size thresholds
    min_rows: 100
    max_rows: null  # No upper limit
    
    # Recency thresholds
    max_days_since_query: 60
    max_days_since_modified: null
    
    # Scoring weights (must sum to 1.0)
    weights:
      query_frequency: 0.4
      query_recency: 0.25
      write_activity: 0.2
      table_size: 0.15
  
  recommendations:
    output_file: "recommendations.yaml"
    auto_refresh_days: 7
    include_explanations: true
    include_suggested_checks: true
  
  auto_apply:
    confidence_threshold: 0.8  # Only auto-apply high confidence
    max_tables: 100            # Safety limit
    skip_existing: true        # Don't duplicate existing configs
  
  # Cache settings
  cache_metadata: true
  cache_ttl_seconds: 3600
```

### Configuration Options

#### Selection Criteria

| Option | Default | Description |
|--------|---------|-------------|
| `min_query_count` | 10 | Minimum number of queries in lookback period |
| `min_queries_per_day` | 1.0 | Minimum average queries per day |
| `lookback_days` | 30 | Number of days to analyze for usage patterns |
| `exclude_patterns` | [] | Wildcard patterns to exclude (e.g., `temp_*`) |
| `min_rows` | 100 | Minimum row count (optional) |
| `max_rows` | null | Maximum row count (optional) |
| `max_days_since_query` | null | Only include tables queried in last N days |
| `max_days_since_modified` | null | Only include tables modified in last N days |

#### Scoring Weights

Customize how different factors influence scoring:

```yaml
weights:
  query_frequency: 0.4   # How often table is queried
  query_recency: 0.25    # How recently queried
  write_activity: 0.2    # How recently updated
  table_size: 0.15       # Table size considerations
```

Weights must be positive and sum to approximately 1.0.

#### Modes

- **`recommend`**: Generate recommendations file for review
- **`auto`**: Automatically apply high-confidence recommendations
- **`disabled`**: Disable smart selection

## CLI Usage

### Generate Recommendations

```bash
# Basic usage
baselinr recommend --config config.yaml

# Limit to specific schema
baselinr recommend --config config.yaml --schema analytics

# Show detailed explanations
baselinr recommend --config config.yaml --explain

# Specify output file
baselinr recommend --config config.yaml --output my_recommendations.yaml
```

### Review Recommendations

The output file includes:

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
      - "Medium table with 5,000,000 rows"
    suggested_checks:
      - freshness
      - row_count
      - completeness
      - numeric_distribution
  
  - schema: analytics
    table: revenue_summary
    confidence: 0.88
    reasons:
      - "Actively queried: 423 queries (14.1 per day)"
      - "Last queried 1 day ago"
      - "Updated 2 days ago"
    suggested_checks:
      - freshness
      - numeric_distribution
    warnings:
      - "No queries in 1 days - verify if still in use"

excluded_tables:
  - schema: staging
    table: temp_load_2025
    reasons:
      - "Matches exclude pattern: temp_*"
  
  - schema: archive
    table: old_events_2020
    reasons:
      - "Last queried 147 days ago (threshold: 60 days)"
      - "No recent write activity"
```

### Apply Recommendations

```bash
# Apply with confirmation prompt
baselinr recommend --config config.yaml --apply

# This will:
# 1. Show summary of changes
# 2. Prompt for confirmation
# 3. Backup original config to config.yaml.backup
# 4. Add recommended tables to profiling.tables
```

### Refresh Recommendations

```bash
# Refresh based on latest metadata
baselinr recommend --config config.yaml --refresh
```

## Usage Patterns

### Pattern 1: Initial Setup

When starting with Baselinr on a new database:

```bash
# 1. Create basic config with connection details
cat > config.yaml <<EOF
source:
  type: snowflake
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
  mode: recommend
  criteria:
    lookback_days: 30
    min_queries_per_day: 1
EOF

# 2. Generate recommendations
baselinr recommend --config config.yaml --explain

# 3. Review recommendations.yaml

# 4. Apply recommendations
baselinr recommend --config config.yaml --apply

# 5. Run profiling
baselinr profile --config config.yaml
```

### Pattern 2: Periodic Review

Review and refresh recommendations monthly:

```bash
# Generate fresh recommendations
baselinr recommend --config config.yaml --refresh --output recommendations_$(date +%Y%m).yaml

# Compare with previous month
diff recommendations_202412.yaml recommendations_202501.yaml

# Selectively add new high-value tables
```

### Pattern 3: Schema-Specific Discovery

Focus on a specific schema:

```bash
# Analytics schema only
baselinr recommend --config config.yaml --schema analytics --explain

# Review and apply
baselinr recommend --config config.yaml --schema analytics --apply
```

### Pattern 4: Conservative Auto-Mode

Let the system automatically select high-confidence tables:

```yaml
smart_selection:
  enabled: true
  mode: auto
  criteria:
    min_query_count: 50  # Conservative
    min_queries_per_day: 5
    lookback_days: 30
  auto_apply:
    confidence_threshold: 0.9  # Very high confidence only
    max_tables: 50
```

## Best Practices

### 1. Start Conservative

Begin with strict criteria and expand as needed:

```yaml
criteria:
  min_query_count: 50      # Higher threshold
  min_queries_per_day: 5   # Active tables only
  lookback_days: 30
  max_tables: 25           # Limit initial scope
```

### 2. Use Exclude Patterns

Proactively exclude known table patterns:

```yaml
criteria:
  exclude_patterns:
    - "temp_*"
    - "*_backup"
    - "*_archive"
    - "staging_*"
    - "test_*"
    - "*_old"
    - "*_deprecated"
```

### 3. Tune Scoring Weights

Adjust weights based on your priorities:

```yaml
# Emphasize actively-used tables
weights:
  query_frequency: 0.6   # Prioritize usage
  query_recency: 0.2
  write_activity: 0.1
  table_size: 0.1

# Emphasize data freshness
weights:
  query_frequency: 0.3
  query_recency: 0.2
  write_activity: 0.4    # Prioritize updates
  table_size: 0.1
```

### 4. Review Before Auto-Apply

Always review recommendations in `recommend` mode before switching to `auto`:

```bash
# Step 1: Review
baselinr recommend --config config.yaml --explain

# Step 2: After reviewing, enable auto for high-confidence only
# Edit config: mode: "auto"
```

### 5. Combine with Explicit Configs

Smart selection works alongside explicit table configurations:

```yaml
profiling:
  tables:
    # Explicit critical tables (always included)
    - schema: analytics
      table: revenue_daily
    
    - schema: core
      table: customers

smart_selection:
  enabled: true
  mode: recommend
  auto_apply:
    skip_existing: true  # Won't duplicate above tables
```

## Troubleshooting

### Issue: No Recommendations Generated

**Cause**: Criteria too strict or insufficient permissions

**Solutions**:
1. Check criteria thresholds:
   ```yaml
   criteria:
     min_query_count: 5   # Lower threshold
     min_queries_per_day: 0.5
   ```

2. Verify database permissions:
   - Snowflake: `ACCOUNTADMIN` or `USAGE` on `ACCOUNT_USAGE` schema
   - BigQuery: `roles/bigquery.jobUser` for job history
   - PostgreSQL: Access to `pg_stat_user_tables`

3. Check lookback period:
   ```yaml
   criteria:
     lookback_days: 60  # Longer period
   ```

### Issue: Too Many Recommendations

**Cause**: Criteria too lenient

**Solutions**:
1. Increase thresholds:
   ```yaml
   criteria:
     min_query_count: 50
     min_queries_per_day: 2
   ```

2. Limit results:
   ```yaml
   auto_apply:
     max_tables: 50
     confidence_threshold: 0.85
   ```

3. Add more exclude patterns:
   ```yaml
   criteria:
     exclude_patterns:
       - "dev_*"
       - "*_temp"
   ```

### Issue: Low Confidence Scores

**Cause**: Limited metadata availability

**Solutions**:
1. Check database type - some databases (MySQL, SQLite) have limited query history
2. For Snowflake, ensure access to `ACCOUNT_USAGE` views (fallback to `INFORMATION_SCHEMA`)
3. Accept that confidence will be lower without query history:
   ```yaml
   auto_apply:
     confidence_threshold: 0.6  # Lower for databases without query logs
   ```

### Issue: Important Tables Excluded

**Cause**: Tables fail criteria checks

**Solutions**:
1. Review excluded_tables in recommendations file
2. Check specific exclusion reasons
3. Adjust criteria or add explicit config:
   ```yaml
   profiling:
     tables:
       - schema: analytics
         table: important_table  # Explicit override
   ```

## Performance Considerations

### Large Warehouses (1000+ tables)

For warehouses with many tables:

1. **Use Schema Filtering**:
   ```bash
   baselinr recommend --config config.yaml --schema analytics
   ```

2. **Increase Criteria Thresholds**:
   ```yaml
   criteria:
     min_query_count: 100  # Only very active tables
     min_queries_per_day: 10
   ```

3. **Limit Recommendations**:
   ```yaml
   auto_apply:
     max_tables: 100
   ```

### Metadata Query Performance

Smart selection queries metadata tables which may be expensive:

1. **Enable Caching**:
   ```yaml
   smart_selection:
     cache_metadata: true
     cache_ttl_seconds: 3600  # 1 hour
   ```

2. **Run During Off-Peak Hours**:
   ```bash
   # Schedule via cron
   0 2 * * * baselinr recommend --config config.yaml --refresh
   ```

3. **Use Fallback Queries**: System automatically falls back to simpler queries if primary metadata sources fail

## Database-Specific Notes

### Snowflake

- **Best Experience**: Full query history and table metrics
- **Requirements**: `ACCOUNTADMIN` role or `USAGE` on `ACCOUNT_USAGE` schema
- **Fallback**: `INFORMATION_SCHEMA.TABLES` (basic metadata only)

### BigQuery

- **Query History**: Requires project-level access to `INFORMATION_SCHEMA.JOBS_BY_PROJECT`
- **Limitations**: Query history per project, not per dataset
- **Recommendation**: Use dataset-specific recommendations

### PostgreSQL

- **Query Statistics**: Via `pg_stat_user_tables`
- **Note**: Scan counts used as proxy for query frequency (not individual queries)
- **Performance**: Very fast metadata collection

### Redshift

- **Query History**: `STL_QUERY` and `STL_SCAN` tables
- **Table Metrics**: `SVV_TABLE_INFO` for sizes and row counts
- **Note**: Query logs may need retention settings

### MySQL

- **Limited**: No built-in query history tracking
- **Metadata**: Basic table statistics from `INFORMATION_SCHEMA`
- **Recommendation**: Lower confidence thresholds or use explicit configs

### SQLite

- **Very Limited**: Only basic table metadata
- **No Query History**: Cannot track usage patterns
- **Best For**: Testing and development only

## API Usage

Use smart selection programmatically:

```python
from baselinr import BaselinrClient
from baselinr.smart_selection import SmartSelectionConfig, RecommendationEngine

# Via client
client = BaselinrClient(config_path="config.yaml")

# Generate recommendations (if client supports it in future)
# recommendations = client.generate_recommendations(schema="analytics")

# Or use engine directly
from baselinr.connectors.factory import create_connector

config = client.config
connector = create_connector(config.source, config.retry)

smart_config = SmartSelectionConfig(
    enabled=True,
    mode="recommend",
)

engine = RecommendationEngine(
    connection_config=config.source,
    smart_config=smart_config,
)

report = engine.generate_recommendations(
    engine=connector.engine,
    schema="analytics",
)

print(f"Found {report.total_recommended} recommendations")
for rec in report.recommended_tables[:5]:
    print(f"  - {rec.schema}.{rec.table} (confidence: {rec.confidence:.2f})")
```

## Future Enhancements

Planned features:
- **ML-based scoring**: Learn from profiling results and drift patterns
- **Cost-aware recommendations**: Factor in query costs and storage
- **Historical trending**: Track table importance over time
- **Cross-database recommendations**: Identify similar table patterns
- **Integration with dbt**: Use dbt lineage for smarter selection
- **Anomaly-based triggers**: Recommend tables with unusual patterns

## FAQ

**Q: Will smart selection replace my existing table configs?**
A: No, explicit configurations always take precedence. Smart selection is additive.

**Q: How often should I refresh recommendations?**
A: Weekly or monthly, depending on how rapidly your data landscape changes.

**Q: Can I use smart selection in production?**
A: Yes, in `recommend` mode for review. Use `auto` mode carefully with conservative settings.

**Q: What if I don't have access to query history?**
A: The system falls back to basic table metadata (sizes, row counts). Confidence scores will be lower.

**Q: How do I exclude a single table?**
A: Add it to `exclude_patterns` or use a schema-level/table-level config with profiling disabled.

**Q: Can I customize the scoring algorithm?**
A: Yes, adjust `weights` in criteria. For more customization, extend the `TableScorer` class.

## Support

For issues or questions:
- GitHub Issues: [baselinr/issues](https://github.com/yourusername/baselinr/issues)
- Documentation: [docs.baselinr.io](https://docs.baselinr.io)
- Examples: `examples/config_smart_selection.yml`
