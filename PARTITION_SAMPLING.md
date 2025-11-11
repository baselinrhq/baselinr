# Partition-Aware Profiling and Sampling

ProfileMesh now supports advanced partition-aware profiling and flexible sampling strategies to efficiently profile large datasets.

## 🎯 Overview

Instead of the simple `sample_ratio` field, ProfileMesh now provides:
1. **Partition-aware profiling** - Profile specific partitions only
2. **Adaptive sampling** - Multiple sampling methods with configurable parameters
3. **Combined strategies** - Use both partition filtering and sampling together

## 📋 Configuration Schema

### Basic Table (No Partitioning or Sampling)

```yaml
profiling:
  tables:
    - table: customers
      schema: public
```

This profiles the entire table - the default behavior.

---

### Partition-Aware Profiling

Profile only specific partitions of your data:

```yaml
profiling:
  tables:
    - table: events
      schema: analytics
      partition:
        key: event_date              # Partition column name
        strategy: latest             # Options: latest | recent_n | sample | all
        metadata_fallback: true      # Auto-infer partition key if not specified
```

**Partition Strategies:**

- **`latest`** - Profile only the most recent partition
  ```yaml
  partition:
    key: event_date
    strategy: latest
  ```

- **`recent_n`** - Profile the N most recent partitions
  ```yaml
  partition:
    key: event_date
    strategy: recent_n
    recent_n: 7  # Last 7 days
  ```

- **`sample`** - Sample from partition values (planned, not yet implemented)

- **`all`** - Profile all partitions (explicit default)

---

### Sampling

Apply sampling to reduce data volume:

```yaml
profiling:
  tables:
    - table: large_table
      schema: public
      sampling:
        enabled: true
        method: random               # Options: random | stratified | topk
        fraction: 0.05               # 5% sample
        max_rows: 1000000            # Cap at 1M rows
```

**Sampling Methods:**

- **`random`** - Simple random sampling
- **`stratified`** - Stratified sampling (preserves distribution)
- **`topk`** - Top-K sampling (planned)

**Sampling Parameters:**

- `enabled` - Turn sampling on/off (default: false)
- `method` - Sampling algorithm
- `fraction` - Fraction of rows to sample (0.0-1.0)
- `max_rows` - Maximum rows to sample (optional cap)

---

### Combined Partition + Sampling

For ultimate efficiency on large tables:

```yaml
profiling:
  tables:
    - table: clickstream
      schema: analytics
      partition:
        key: date
        strategy: latest
      sampling:
        enabled: true
        method: stratified
        fraction: 0.01              # 1% sample
        max_rows: 500000
```

This example:
1. Filters to the latest partition (e.g., today's data)
2. Then samples 1% of that partition
3. Caps at 500,000 rows maximum

---

## 🔧 Features

### Automatic Partition Key Inference

If you enable `metadata_fallback`, ProfileMesh will try to infer the partition key:

```yaml
partition:
  strategy: latest
  metadata_fallback: true  # Will look for columns named: date, event_date, etc.
```

Common patterns it looks for:
- `date`, `event_date`, `partition_date`
- `created_at`, `updated_at`
- `timestamp`, `dt`, `ds`
- Any DATE or TIMESTAMP columns

### Warehouse-Specific SQL

ProfileMesh generates warehouse-appropriate SQL:

**PostgreSQL:**
```sql
SELECT * FROM events 
WHERE event_date = (SELECT MAX(event_date) FROM events)
TABLESAMPLE SYSTEM (1.0);
```

**Snowflake:**
```sql
SELECT * FROM events 
WHERE event_date = (SELECT MAX(event_date) FROM events)
SAMPLE (1.0);
```

**SQLite:**
```sql
SELECT * FROM events 
WHERE date = (SELECT MAX(date) FROM events)
ORDER BY RANDOM() LIMIT 500000;
```

---

## 📊 Examples

### Example 1: Daily Partitioned Table

Profile only today's data:

```yaml
tables:
  - table: daily_events
    schema: analytics
    partition:
      key: ds  # Common partition column name
      strategy: latest
```

### Example 2: Large Historical Table

Sample for efficiency:

```yaml
tables:
  - table: historical_transactions
    schema: finance
    sampling:
      enabled: true
      method: random
      fraction: 0.001  # 0.1% sample
      max_rows: 100000
```

### Example 3: Recent Week's Data with Sampling

```yaml
tables:
  - table: user_events
    schema: analytics
    partition:
      key: event_date
      strategy: recent_n
      recent_n: 7
    sampling:
      enabled: true
      method: stratified
      fraction: 0.1
```

### Example 4: Full Table (Default)

No special configuration needed:

```yaml
tables:
  - table: small_lookup_table
    schema: public
```

---

## 🚀 CLI Usage

### Preview Plan

See how partitioning and sampling will be applied:

```bash
profilemesh plan --config config.yml
```

Output will show:
```
1. analytics.events
   Status: ready
   Partition: latest on event_date
   Sampling: stratified (1.00%), max 500,000 rows
```

### Run Profiling

```bash
profilemesh profile --config config.yml
```

Results metadata will include:
- Which partition strategy was used
- Which partitions were profiled
- Sampling method and fraction applied
- Actual row count profiled

---

## 📈 Performance Benefits

### Before (sample_ratio)

Profile 10% of a 1B row table:
- Scans: 100M rows
- Time: ~10 minutes

### After (partition + sampling)

Profile latest partition (10M rows) with 1% sample:
- Scans: 100K rows (1000x reduction!)
- Time: ~6 seconds

### Example Speedup

For a table with daily partitions (365 partitions, 10M rows each):

**Full table with sampling:**
```yaml
sampling:
  enabled: true
  fraction: 0.001  # 0.1%
# Profiles: 3.65M rows (0.1% of 3.65B)
```

**Latest partition only:**
```yaml
partition:
  key: date
  strategy: latest
# Profiles: 10M rows (just today)
```

**Latest partition with sampling:**
```yaml
partition:
  key: date
  strategy: latest
sampling:
  enabled: true
  fraction: 0.01  # 1%
# Profiles: 100K rows (1% of 10M)
```

---

## 🔄 Migration Guide

### Old Configuration

```yaml
profiling:
  tables:
    - table: events
      schema: public
      sample_ratio: 0.1
  default_sample_ratio: 1.0
```

### New Configuration

**Full table (no sampling):**
```yaml
profiling:
  tables:
    - table: events
      schema: public
```

**With sampling:**
```yaml
profiling:
  tables:
    - table: events
      schema: public
      sampling:
        enabled: true
        method: random
        fraction: 0.1
```

**With partition awareness:**
```yaml
profiling:
  tables:
    - table: events
      schema: public
      partition:
        key: event_date
        strategy: latest
      sampling:
        enabled: true
        fraction: 0.1
```

---

## 🎓 Best Practices

### 1. Start with Partition Filtering

For time-series data, profile only recent partitions:

```yaml
partition:
  key: date
  strategy: recent_n
  recent_n: 7  # Last week
```

### 2. Add Sampling for Very Large Partitions

If even one partition is huge:

```yaml
partition:
  key: date
  strategy: latest
sampling:
  enabled: true
  fraction: 0.01
  max_rows: 1000000  # Safety cap
```

### 3. Use Stratified Sampling for Diverse Data

When data has important subgroups:

```yaml
sampling:
  enabled: true
  method: stratified  # Preserves distribution
  fraction: 0.05
```

### 4. Profile Small Tables Fully

No need for complexity on small tables:

```yaml
tables:
  - table: lookup_table  # Just specify the table
    schema: public
```

---

## 🔮 Future Enhancements

Planned features:

- **Cost-aware profiling** - Estimate query cost before profiling
- **Incremental profiling** - Profile only new partitions
- **Adaptive sampling** - Auto-adjust based on data characteristics
- **Multi-column partitioning** - Support compound partition keys
- **Custom partition strategies** - Plugin your own logic

---

## 📝 See Also

- [README.md](README.md) - Main documentation
- [examples/config_advanced.yml](examples/config_advanced.yml) - All features demonstrated
- [DEVELOPMENT.md](DEVELOPMENT.md) - Architecture details
- [profilemesh/profiling/query_builder.py](profilemesh/profiling/query_builder.py) - Implementation

