# Schema Change Detection

Baselinr includes comprehensive schema change detection that automatically tracks and alerts on schema modifications to your data tables.

## Overview

Schema change detection maintains an internal registry of table schemas and compares them across profiling runs to detect:

- **New columns**: Columns that have been added to a table
- **Dropped columns**: Columns that have been removed from a table
- **Renamed columns**: Columns that have been renamed (detected heuristically)
- **Type changes**: Changes to column data types
- **Partition changes**: Changes to table partitioning (Snowflake-specific)

## How It Works

### Schema Registry

Baselinr maintains a `baselinr_schema_registry` table that stores schema snapshots for each profiling run. Each column is tracked with:

- Column name and type
- Column hash (based on name, type, and nullable status)
- First seen and last seen timestamps
- Run ID association

### Change Detection Process

1. **Schema Registration**: After profiling completes, the current schema is registered in the schema registry
2. **Comparison**: The current schema is compared to the previous schema snapshot
3. **Change Detection**: Various algorithms detect different types of changes:
   - Direct comparison for added/removed columns
   - Heuristic matching for renamed columns (name similarity + type matching)
   - Type comparison for type changes
   - Warehouse-specific queries for partition changes
4. **Event Emission**: Detected changes are emitted as `SchemaChangeDetected` events

## Configuration

### Basic Configuration

Enable schema change detection in your `config.yml`:

```yaml
schema_change:
  enabled: true
  similarity_threshold: 0.7  # For rename detection (0.0-1.0)
```

### Suppression Rules

Suppress schema change events for specific tables or change types:

```yaml
schema_change:
  enabled: true
  similarity_threshold: 0.7
  suppression:
    # Suppress all changes for a specific table
    - table: "staging_table"
    
    # Suppress only column additions globally
    - change_type: "column_added"
    
    # Suppress column additions for a specific table
    - table: "orders"
      change_type: "column_added"
    
    # Suppress all changes for a table in a specific schema
    - table: "customers"
      schema: "public"
```

### Suppression Rule Matching

Suppression rules match when:
- Table name matches (if specified)
- Schema name matches (if specified)
- Change type matches (if specified)

All specified conditions must match for suppression to apply.

## Change Types

### Column Added

Detected when a new column appears in the current schema that wasn't in the previous schema.

**Event Fields:**
- `change_type`: `"column_added"`
- `column`: New column name
- `new_type`: Column data type
- `change_severity`: `"low"`

### Column Removed

Detected when a column from the previous schema is missing in the current schema.

**Event Fields:**
- `change_type`: `"column_removed"`
- `column`: Removed column name
- `old_type`: Previous column data type
- `change_severity`: `"high"`

### Column Renamed

Detected heuristically when:
1. A column is removed and a new column is added
2. The names are similar (similarity > threshold, default 0.7)
3. The types are compatible

**Event Fields:**
- `change_type`: `"column_renamed"`
- `column`: New column name
- `old_column_name`: Previous column name
- `old_type`: Previous column type
- `new_type`: New column type
- `change_severity`: `"medium"`

**Similarity Calculation:**
- Uses Levenshtein distance (edit distance)
- Includes prefix/suffix matching bonuses
- Default threshold: 0.7 (configurable)

### Type Changed

Detected when a column exists in both schemas but has a different type.

**Event Fields:**
- `change_type`: `"type_changed"`
- `column`: Column name
- `old_type`: Previous type
- `new_type`: New type
- `change_severity`: Determined automatically:
  - `"low"`: Compatible changes (int→bigint, varchar→text)
  - `"medium"`: Other type changes
  - `"breaking"`: Incompatible changes (numeric→string, string→numeric)

### Partition Changed

Detected when table partitioning changes (Snowflake-specific).

**Event Fields:**
- `change_type`: `"partition_changed"`
- `partition_info`: Dict with partition metadata
- `change_severity`: `"high"`

**Note**: Partition change detection requires appropriate Snowflake permissions to query `INFORMATION_SCHEMA.TABLE_STORAGE_METRICS`.

## Event Handling

Schema change events are emitted via the event bus and can be handled by any registered hooks:

```python
from baselinr.events import SchemaChangeDetected

# Events are automatically emitted during profiling
# Handle them via event hooks (see EVENTS_AND_HOOKS.md)
```

### Event Structure

```python
SchemaChangeDetected(
    event_type="SchemaChangeDetected",
    timestamp=datetime.utcnow(),
    table="customers",
    change_type="column_added",
    column="new_field",
    new_type="VARCHAR(255)",
    change_severity="low",
    metadata={...}
)
```

## Examples

### Example 1: Basic Detection

```yaml
# config.yml
schema_change:
  enabled: true
```

Run profiling:
```bash
baselinr profile --config config.yml
```

If a column is added, you'll see a `SchemaChangeDetected` event with `change_type="column_added"`.

### Example 2: Suppress Column Additions

```yaml
# config.yml
schema_change:
  enabled: true
  suppression:
    # Suppress all column additions
    - change_type: "column_added"
```

### Example 3: Table-Specific Suppression

```yaml
# config.yml
schema_change:
  enabled: true
  suppression:
    # Suppress all changes for staging tables
    - table: "staging_orders"
    - table: "staging_customers"
    
    # But still alert on type changes for production tables
    - table: "production_orders"
      change_type: "column_added"  # Only suppress additions
```

### Example 4: Custom Similarity Threshold

```yaml
# config.yml
schema_change:
  enabled: true
  similarity_threshold: 0.8  # Stricter rename detection
```

Higher thresholds require more similarity to detect renames (fewer false positives, more false negatives).

## Database Migration

The schema registry table is created automatically via migration v2. To manually apply:

```bash
baselinr migrate apply --config config.yml --target 2
```

## Best Practices

1. **Enable for Production**: Always enable schema change detection in production environments
2. **Configure Suppression**: Suppress noisy tables (e.g., staging tables that change frequently)
3. **Monitor High Severity**: Pay special attention to `"high"` and `"breaking"` severity changes
4. **Review Renames**: Heuristic rename detection may have false positives/negatives - review carefully
5. **Partition Monitoring**: For Snowflake, ensure appropriate permissions for partition change detection

## Troubleshooting

### No Events Emitted

- Check that `schema_change.enabled: true` in config
- Verify `profiling.enable_schema_tracking: true` (default: true)
- Ensure event hooks are configured and enabled

### False Positive Renames

- Increase `similarity_threshold` to require more similarity
- Review the similarity calculation logic if needed

### Missing Partition Changes

- For Snowflake, verify permissions to query `INFORMATION_SCHEMA.TABLE_STORAGE_METRICS`
- Check logs for permission errors

### Migration Issues

- Ensure storage database is accessible
- Check migration status: `baselinr migrate status --config config.yml`
- Apply migrations if needed: `baselinr migrate apply --config config.yml`

## Related Documentation

- [Events and Hooks](../architecture/EVENTS_AND_HOOKS.md) - Event system overview
- [Profiling Enrichment](PROFILING_ENRICHMENT.md) - Related enrichment features
- [Schema Reference](../schemas/SCHEMA_REFERENCE.md) - Database schema details

