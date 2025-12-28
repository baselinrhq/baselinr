# Troubleshooting Guide

Common issues and solutions for Baselinr.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Configuration Issues](#configuration-issues)
- [Connection Issues](#connection-issues)
- [Profiling Issues](#profiling-issues)
- [Drift Detection Issues](#drift-detection-issues)
- [Performance Issues](#performance-issues)
- [Storage Issues](#storage-issues)
- [CLI Issues](#cli-issues)
- [SDK Issues](#sdk-issues)
- [Getting Help](#getting-help)

## Installation Issues

### "Command not found: baselinr"

The CLI command is not in your PATH.

**Solutions:**

1. Reinstall Baselinr:
   ```bash
   pip install --force-reinstall -e .
   ```

2. Use Python module directly:
   ```bash
   python -m baselinr.cli profile --config config.yml
   ```

3. Check Python path:
   ```bash
   which python
   pip show baselinr
   ```

4. Activate virtual environment:
   ```bash
   source venv/bin/activate  # Linux/Mac
   .\venv\Scripts\Activate.ps1  # Windows
   ```

### "ModuleNotFoundError: No module named 'baselinr'"

The package is not installed or not in your Python path.

**Solutions:**

1. Install Baselinr:
   ```bash
   pip install -e .
   ```

2. Verify installation:
   ```bash
   python -c "import baselinr; print(baselinr.__version__)"
   ```

3. Check Python environment:
   ```bash
   python --version
   which python  # Linux/Mac
   where python  # Windows
   ```

### Permission Errors (Windows)

If you get permission errors during installation:

**Solutions:**

1. Run PowerShell as Administrator

2. Use user installation:
   ```bash
   pip install --user -e .
   ```

3. Use virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -e .
   ```

### Missing Dependencies

If you get import errors for optional dependencies:

**Solutions:**

1. Install with optional dependencies:
   ```bash
   pip install -e ".[snowflake]"  # For Snowflake
   pip install -e ".[dagster]"    # For Dagster
   pip install -e ".[all]"        # For everything
   ```

2. Install specific package:
   ```bash
   pip install snowflake-connector-python  # For Snowflake
   pip install dagster                     # For Dagster
   ```

## Configuration Issues

### "pydantic.errors.ValidationError"

Your configuration file has errors.

**Solutions:**

1. Check YAML syntax (indentation matters):
   ```yaml
   # Correct
   source:
     type: postgres
     host: localhost
   
   # Incorrect (wrong indentation)
   source:
   type: postgres
   host: localhost
   ```

2. Validate configuration:
   ```bash
   python -c "
   import logging
   logging.basicConfig(level=logging.DEBUG)
   from baselinr.config.loader import ConfigLoader
   ConfigLoader.load_from_file('config.yml')
   "
   ```

3. Check required fields:
   - `environment`: Must be set
   - `source`: Must include `type` and `database`
   - `storage`: Must include `connection`

4. Verify database type is valid:
   - Valid types: `postgres`, `snowflake`, `sqlite`, `mysql`, `bigquery`, `redshift`

### Configuration File Not Found

The configuration file path is incorrect.

**Solutions:**

1. Use absolute path:
   ```bash
   baselinr profile --config /full/path/to/config.yml
   ```

2. Use relative path correctly:
   ```bash
   baselinr profile --config ./config.yml
   baselinr profile --config examples/config.yml
   ```

3. Check current directory:
   ```bash
   pwd  # Linux/Mac
   cd   # Windows
   ```

## Connection Issues

### "Connection refused" or "Connection timeout"

Unable to connect to the database.

**Solutions:**

1. Check database is running:
   ```bash
   # PostgreSQL
   psql -h localhost -U user -d database
   
   # Docker
   docker ps
   docker-compose logs postgres
   ```

2. Verify connection parameters:
   - Host: Check if `localhost` or IP is correct
   - Port: Verify port number (5432 for PostgreSQL, 5439 for Redshift)
   - Database: Ensure database exists
   - Username/Password: Verify credentials

3. Check firewall/network:
   ```bash
   # Test connection
   telnet hostname port
   nc -zv hostname port  # Linux/Mac
   Test-NetConnection hostname -Port port  # Windows
   ```

4. Use connection string directly:
   ```bash
   # Test with psql (PostgreSQL)
   psql "postgresql://user:password@host:port/database"
   ```

### Snowflake Connection Issues

Specific issues with Snowflake connections.

**Solutions:**

1. Install Snowflake connector:
   ```bash
   pip install -e ".[snowflake]"
   ```

2. Verify required fields:
   - `account`: Snowflake account identifier
   - `warehouse`: Warehouse name
   - `database`: Database name
   - `username` and `password`: Credentials

3. Check optional fields:
   - `role`: Role name (recommended)
   - `schema`: Schema name

4. Test connection:
   ```python
   from baselinr.connectors.snowflake import SnowflakeConnector
   from baselinr.config.schema import ConnectionConfig
   
   config = ConnectionConfig(
       type="snowflake",
       account="myaccount",
       warehouse="compute_wh",
       database="my_database",
       username="user",
       password="pass"
   )
   connector = SnowflakeConnector(config)
   engine = connector.get_engine()
   ```

### "SSL connection required"

Database requires SSL connection.

**Solutions:**

1. Enable SSL in connection config:
   ```yaml
   source:
     type: postgres
     host: hostname
     # Add SSL parameters in extra_params
     extra_params:
       sslmode: require
   ```

2. For Snowflake, SSL is automatic

3. For Redshift, use SSL port 5439

### BigQuery Connection Issues

Issues connecting to BigQuery.

**Solutions:**

1. Set up credentials:
   ```yaml
   source:
     type: bigquery
     database: project.dataset
     extra_params:
       credentials_path: /path/to/key.json
   ```

2. Set environment variable:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
   ```

3. Verify credentials file exists and is valid

## Profiling Issues

### "Table not found" or "Schema not found"

The specified table or schema doesn't exist.

**Solutions:**

1. Verify table exists:
   ```sql
   -- PostgreSQL
   SELECT * FROM information_schema.tables 
   WHERE table_schema = 'public' AND table_name = 'customers';
   ```

2. Check schema name in your ODCS contracts:
   ```yaml
   # contracts/customers.odcs.yaml
   kind: DataContract
   apiVersion: v3.1.0
   dataset:
     - name: customers
       physicalName: public.customers  # Make sure schema name is correct
   ```

3. List available tables:
   ```python
   from baselinr.connectors.factory import create_connector
   from baselinr.config.loader import ConfigLoader
   
   config = ConfigLoader.load_from_file("config.yml")
   connector = create_connector(config.source)
   engine = connector.get_engine()
   
   # PostgreSQL
   from sqlalchemy import inspect
   inspector = inspect(engine)
   print(inspector.get_table_names(schema='public'))
   ```

### Profiling Takes Too Long

Profiling is slow for large tables.

**Solutions:**

1. Enable sampling via ODCS contracts:
   ```yaml
   # contracts/large_table.odcs.yaml
   kind: DataContract
   apiVersion: v3.1.0
   dataset:
     - name: large_table
       physicalName: public.large_table
   customProperties:
     - property: baselinr.sampling
       value:
         enabled: true
         method: random
         fraction: 0.01  # Sample 1%
         max_rows: 1000000  # Cap at 1M rows
   ```

2. Use partition-aware profiling via ODCS contracts:
   ```yaml
   # contracts/partitioned_table.odcs.yaml
   kind: DataContract
   apiVersion: v3.1.0
   dataset:
     - name: partitioned_table
       physicalName: public.partitioned_table
       columns:
         - column: date
           partitionStatus: true
   customProperties:
     - property: baselinr.partition.partitioned_table
       value:
         strategy: latest  # Profile only latest partition
   ```

3. Enable parallelism:
   ```yaml
   execution:
     max_workers: 4  # Parallel profiling
   ```

4. Reduce metrics computed:
   ```yaml
   profiling:
     metrics:
       - count
       - null_ratio
       # Remove expensive metrics like histograms for large tables
   ```

### "Out of memory" or Memory Issues

Profiling uses too much memory.

**Solutions:**

1. Enable sampling for large tables

2. Reduce parallelism:
   ```yaml
   execution:
     max_workers: 1  # Sequential processing
   ```

3. Increase system memory or use smaller sample sizes

4. Profile tables individually instead of all at once

### No Results Stored

Profiling runs but no results appear in storage.

**Solutions:**

1. Check storage connection:
   ```yaml
   storage:
     connection:
       type: postgres
       host: localhost
       # ... verify connection works
     create_tables: true
   ```

2. Verify tables were created:
   ```sql
   SELECT * FROM baselinr_runs ORDER BY profiled_at DESC LIMIT 10;
   SELECT * FROM baselinr_results LIMIT 10;
   ```

3. Check for errors in logs:
   ```bash
   baselinr profile --config config.yml --verbose
   ```

4. Ensure `dry_run` is False (default)

## Drift Detection Issues

### "No baseline run found"

No baseline run is available for comparison.

**Solutions:**

1. Ensure you have at least 2 profiling runs:
   ```bash
   # Run profiling twice
   baselinr profile --config config.yml
   # Wait a bit or make changes to data
   baselinr profile --config config.yml
   
   # Now detect drift (--dataset flag specifies table name)
   baselinr drift --config config.yml --dataset customers
   ```

2. Check runs exist:
   ```bash
   baselinr query runs --config config.yml --table customers
   ```

3. Specify baseline explicitly:
   ```bash
   baselinr drift --config config.yml --dataset customers --baseline-run-id <run-id>
   ```

### Too Many False Positives

Drift detection triggers too often.

**Solutions:**

1. Adjust thresholds:
   ```yaml
   drift_detection:
     absolute_threshold:
       low_threshold: 10.0    # Increase from 5.0
       medium_threshold: 20.0  # Increase from 15.0
       high_threshold: 40.0    # Increase from 30.0
   ```

2. Enable type-specific thresholds:
   ```yaml
   drift_detection:
     enable_type_specific_thresholds: true
     type_specific_thresholds:
       numeric:
         mean:
           low: 15.0  # More lenient for numeric means
   ```

3. Use statistical strategy instead:
   ```yaml
   drift_detection:
     strategy: statistical
     statistical:
       sensitivity: low  # Less sensitive
   ```

4. Change baseline strategy:
   ```yaml
   drift_detection:
     baselines:
       strategy: moving_average  # Use average instead of last run
       windows:
         moving_average: 7  # Average over 7 runs
   ```

### No Drift Detected When Expected

Drift detection doesn't catch changes.

**Solutions:**

1. Lower thresholds:
   ```yaml
   drift_detection:
     absolute_threshold:
       low_threshold: 2.0   # Lower from 5.0
       medium_threshold: 5.0  # Lower from 15.0
   ```

2. Verify data actually changed:
   ```bash
   # Query metrics directly
   baselinr query run-details --config config.yml --run-id <run-id>
   ```

3. Check correct baseline is being used:
   ```bash
   baselinr drift --config config.yml --dataset customers --verbose
   ```

## Performance Issues

### Slow Profiling

Profiling is taking longer than expected.

**Solutions:**

1. Enable parallelism:
   ```yaml
   execution:
     max_workers: 4
   ```

2. Use sampling for large tables

3. Profile fewer tables per run

4. Enable incremental profiling:
   ```yaml
   incremental:
     enabled: true
     change_detection:
       enabled: true
   ```

5. Check database connection performance and network latency

### High Database Load

Profiling causes database performance issues.

**Solutions:**

1. Reduce parallelism to limit concurrent queries

2. Profile during off-peak hours

3. Use sampling to reduce data scanned

4. Enable incremental profiling to skip unchanged tables

5. Use read replicas if available

## Storage Issues

### Tables Not Created

Storage tables are not automatically created.

**Solutions:**

1. Ensure `create_tables` is enabled:
   ```yaml
   storage:
     create_tables: true
   ```

2. Create tables manually:
   ```bash
   baselinr migrate apply --config config.yml
   ```

3. Check database permissions (CREATE TABLE permission required)

### Migration Errors

Schema migrations fail.

**Solutions:**

1. Check migration status:
   ```bash
   baselinr migrate status --config config.yml
   ```

2. Validate schema:
   ```bash
   baselinr migrate validate --config config.yml
   ```

3. Apply migrations:
   ```bash
   baselinr migrate apply --config config.yml
   ```

4. Check for conflicts with existing schema

## CLI Issues

### Command Hangs or Freezes

CLI command appears to hang.

**Solutions:**

1. Check if profiling is actually running (large tables take time)

2. Enable verbose output:
   ```bash
   baselinr profile --config config.yml --verbose
   ```

3. Check database connection is active

4. Kill and restart if necessary

### Verbose Output Not Showing

Verbose flag doesn't show expected output.

**Solutions:**

1. Check command syntax:
   ```bash
   baselinr plan --config config.yml --verbose
   ```

2. Some commands may not support verbose flag yet

3. Check logs in database or files if configured

## SDK Issues

### Client Initialization Fails

BaselinrClient fails to initialize.

**Solutions:**

1. Verify config file exists and is valid:
   ```python
   from baselinr.config.loader import ConfigLoader
   config = ConfigLoader.load_from_file("config.yml")
   print(config.environment)
   ```

2. Check config parameter format:
   ```python
   # Correct
   client = BaselinrClient(config_path="config.yml")
   client = BaselinrClient(config=config_dict)
   
   # Incorrect - don't provide both
   client = BaselinrClient(config_path="config.yml", config=config_dict)
   ```

3. Verify configuration is valid BaselinrConfig or dict

### Query Methods Return Empty Results

Query methods don't return expected data.

**Solutions:**

1. Verify profiling has been run:
   ```python
   runs = client.query_runs(days=7)
   print(f"Found {len(runs)} runs")
   ```

2. Check filters aren't too restrictive:
   ```python
   # Too restrictive
   runs = client.query_runs(table="nonexistent", days=1)
   
   # Better
   runs = client.query_runs(days=30)
   ```

3. Ensure storage connection is correct and tables exist

## Getting Help

If you're still experiencing issues:

1. **Check Documentation:**
   - [Configuration Reference](../reference/CONFIG_REFERENCE.md)
   - [API Reference](../reference/API_REFERENCE.md)
   - [Installation Guide](../getting-started/INSTALL.md)

2. **Review Examples:**
   - Check `examples/` directory for working configurations
   - Review `examples/config.yml` for reference

3. **Enable Debug Logging:**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

4. **Open an Issue:**
   - GitHub: https://github.com/baselinrhq/baselinr/issues
   - Include:
     - Error message and traceback
     - Configuration file (redact sensitive info)
     - Python version
     - Database type and version
     - Steps to reproduce

---

## Related Documentation

- [Installation Guide](../getting-started/INSTALL.md) - Installation troubleshooting
- [Configuration Reference](../reference/CONFIG_REFERENCE.md) - Complete configuration reference
- [Best Practices Guide](BEST_PRACTICES.md) - Recommended patterns
- [Performance Tuning Guide](PERFORMANCE_TUNING.md) - Performance optimization

