# Baselinr Quick Start Guide

Get Baselinr up and running in 5 minutes!

## Prerequisites

- Python 3.10 or higher
- Docker and Docker Compose (for the full example)
- OR a PostgreSQL database

## Option 1: Docker Environment (Recommended)

This is the easiest way to get started with Baselinr.

### Step 1: Start the Docker Environment

```bash
cd docker
docker-compose up -d
```

This will start:
- PostgreSQL with sample data (customers, products, orders tables)
- Dagster daemon
- Dagster web UI

Wait about 30 seconds for everything to initialize.

### Step 2: Install Baselinr

```bash
# From the profile_mesh directory
pip install -e ".[dagster]"
```

### Step 3: Run Your First Profile

```bash
baselinr profile --config examples/config.yml
```

You should see output like:

```
[1/4] Loading configuration...
✓ Configuration loaded (environment: development)

[2/4] Profiling tables...
✓ Profiled 3 tables:
  - customers: 10 columns, 10 rows
  - products: 8 columns, 10 rows
  - orders: 7 columns, 10 rows

[3/4] Writing results to storage...
✓ Results written to storage

[4/4] Checking for drift...
ℹ Drift detection skipped: Need at least 2 runs for drift detection
```

### Step 4: Run a Second Profile to See Drift Detection

```bash
# Run profiling again
baselinr profile --config examples/config.yml

# Now detect drift
baselinr drift --config examples/config.yml --dataset customers
```

### Step 5: Explore Dagster UI

Open http://localhost:3000 in your browser to see:
- Profiling assets for each table
- Job runs and schedules
- Asset lineage graph

## Option 2: Your Own PostgreSQL Database

### Step 1: Install Baselinr

```bash
pip install -e .
```

### Step 2: Create Configuration

Create a `my_config.yml` file:

```yaml
environment: development

source:
  type: postgres
  host: your-db-host
  port: 5432
  database: your-database
  username: your-username
  password: your-password
  schema: public

storage:
  connection:
    type: postgres
    host: your-db-host
    port: 5432
    database: your-database
    username: your-username
    password: your-password
  results_table: baselinr_results
  runs_table: baselinr_runs
  create_tables: true

profiling:
  tables:
    - table: your_table_name
```

### Step 3: Run Profiling

```bash
baselinr profile --config my_config.yml
```

## Option 3: SQLite (Minimal Setup)

For the absolute quickest test without any external dependencies:

### Step 1: Create a SQLite Database

```python
# create_sample.py
import sqlite3

conn = sqlite3.connect('sample.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT,
    age INTEGER,
    email TEXT
)
''')

cursor.executemany('INSERT INTO users VALUES (?,?,?,?)', [
    (1, 'Alice', 30, 'alice@example.com'),
    (2, 'Bob', 25, 'bob@example.com'),
    (3, 'Charlie', 35, 'charlie@example.com'),
])

conn.commit()
conn.close()
```

Run it:
```bash
python create_sample.py
```

### Step 2: Create Configuration

```yaml
# config_sqlite.yml
environment: development

source:
  type: sqlite
  filepath: ./sample.db

storage:
  connection:
    type: sqlite
    filepath: ./sample.db
  results_table: baselinr_results
  runs_table: baselinr_runs
  create_tables: true

profiling:
  tables:
    - table: users
```

### Step 3: Run Profiling

```bash
pip install -e .
baselinr profile --config config_sqlite.yml
```

## Next Steps

### 1. Explore the Results

Query the results in your database:

```sql
-- View all profiling runs
SELECT * FROM baselinr_runs ORDER BY profiled_at DESC;

-- View metrics for a specific table
SELECT column_name, metric_name, metric_value
FROM baselinr_results
WHERE dataset_name = 'customers'
  AND run_id = '<latest-run-id>'
ORDER BY column_name, metric_name;
```

### 2. Set Up Drift Monitoring

Run profiling multiple times and compare:

```bash
# Profile now
baselinr profile --config examples/config.yml

# Make some changes to your data...

# Profile again
baselinr profile --config examples/config.yml

# Detect drift
baselinr drift --config examples/config.yml --dataset customers
```

### 3. Integrate with Dagster

See the Dagster UI at http://localhost:3000 to:
- Schedule regular profiling jobs
- View profiling history
- Set up alerts on drift detection

### 4. Customize Your Configuration

Edit `examples/config.yml` to:
- Add more tables to profile
- Adjust sampling ratios for large tables
- Configure which metrics to compute
- Change drift detection thresholds

## Common Issues

### "Connection refused" Error

If you get a connection error with Docker:
- Make sure Docker is running
- Wait 30 seconds after `docker-compose up -d`
- Check logs: `docker-compose logs postgres`

### "Module not found" Error

Make sure you've installed Baselinr:
```bash
pip install -e .
```

### Docker Not Available

Use Option 2 (your own PostgreSQL) or Option 3 (SQLite).

## Get Help

- Check the full README.md
- Look at examples in the `examples/` directory
- Review the configuration schema in `baselinr/config/schema.py`

Happy profiling! 🧩

