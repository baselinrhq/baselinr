# Data Validation Guide

Baselinr provides a comprehensive data validation system that allows you to define and execute data quality rules. This guide covers how to configure, execute, and integrate validation into your data quality workflows.

## Overview

**Where to configure**
- Global defaults: `validation` in `config.yml` (enablement, providers, global settings)
- Validation rules: ODCS contracts in `contracts/` directory (see [ODCS Data Contracts](ODCS_DATA_CONTRACTS.md))
- Column overrides: inside ODCS contract `dataset[].columns[]` sections

Precedence: Contract-level rules > Global defaults.

Data validation in Baselinr is built on a provider-based architecture, similar to the lineage system. The built-in provider offers common validators for format, range, enum, null checks, uniqueness, and referential integrity. Future providers (Great Expectations, Soda, etc.) can be integrated as optional dependencies.

## Key Concepts

- **Validation Rules**: Define what to validate (format, range, enum, etc.)
- **Validation Providers**: Execute validation rules (built-in, Great Expectations, Soda, etc.)
- **Validation Results**: Store pass/fail status, failure details, and sample failures
- **Events**: Validation failures emit events that integrate with alert hooks

## Configuration

### Basic Configuration

Enable validation in your `config.yml`. Define validation rules in ODCS contracts:

```yaml
validation:
  enabled: true
  providers:
    - type: builtin
```

```yaml
# contracts/customers.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: customers
    physicalName: public.customers
    columns:
      - column: email
        quality:
          - type: format
            rule: format
            specification:
              pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
            severity: error
```

**Important**: 
- Validation rules **must** be defined in ODCS contracts. The old `validation.rules[]` field is no longer supported.
- The `validation.providers[]` section is for provider configuration (e.g., Great Expectations suite config), not dataset rules
- Define quality rules in ODCS contracts using the `quality` field at contract, dataset, or column level

### Rule Types

#### Format Validation

Validates column values against regex patterns or predefined formats (email, URL, phone).

```yaml
- table: customers
  column: email
  type: format
  pattern: "email"  # Predefined: email, url, phone
  # OR
  pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"  # Custom regex
  severity: high
```

**Predefined Patterns:**
- `email`: Standard email format
- `url`: HTTP/HTTPS URLs
- `phone`: Phone numbers with international format support

#### Range Validation

Validates numeric values against min/max bounds or string lengths.

```yaml
- table: orders
  column: total_amount
  type: range
  min: 0
  max: 1000000
  severity: medium
```

#### Enum Validation

Validates that column values are in a list of allowed values.

```yaml
- table: orders
  column: status
  type: enum
  allowed_values: ["pending", "completed", "cancelled"]
  severity: high
```

#### Not-Null Validation

Validates that columns do not contain NULL values.

```yaml
- table: customers
  column: customer_id
  type: not_null
  severity: high
```

#### Uniqueness Validation

Validates that column values are unique.

```yaml
- table: customers
  column: email
  type: unique
  severity: high
```

#### Referential Integrity Validation

Validates foreign key relationships between tables.

```yaml
- table: order_items
  column: order_id
  type: referential
  references:
    table: orders
    column: id
    schema: public  # Optional, defaults to source schema
  severity: high
```

### Rule Configuration Options

All rules support these common options:

- `table` (required): Table name to validate
- `column` (required for most rules): Column name to validate
- `type` (required): Rule type (format, range, enum, not_null, unique, referential)
- `severity` (optional, default: "medium"): Severity level (low, medium, high)
- `enabled` (optional, default: true): Whether the rule is enabled

### Complete Example

```yaml
# config.yml
validation:
  enabled: true
  providers:
    - type: builtin
```

```yaml
# contracts/customers.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: customers
    physicalName: public.customers
    columns:
      - column: email
        quality:
          - type: format
            rule: format
            specification:
              pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
            severity: error
```

```yaml
# contracts/orders.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: orders
    physicalName: public.orders
    columns:
      - column: total_amount
        quality:
          - type: range
            rule: range
            specification:
              min: 0
              max: 1000000
            severity: medium
        
        # Enum validation
        - table: orders
          column: status
          type: enum
          allowed_values: ["pending", "completed", "cancelled"]
          severity: high
        
        # Not-null validation
        - table: customers
          column: customer_id
          type: not_null
          severity: high
        
        # Uniqueness validation
        - table: customers
          column: email
          type: unique
          severity: high
        
        # Referential integrity
        - table: order_items
          column: order_id
          type: referential
          references:
            table: orders
            column: id
          severity: high
```

## CLI Usage

### Execute Validation

Run all validation rules:

```bash
baselinr validate --config config.yml
```

Filter by table:

```bash
baselinr validate --config config.yml --table customers
```

Save results to JSON:

```bash
baselinr validate --config config.yml --output validation_results.json
```

### Output Format

The CLI displays validation results in a table format:

```
┏━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Table      ┃ Column  ┃ Rule Type ┃ Status   ┃ Failed Rows ┃ Failure Rate ┃ Severity┃
┡━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ customers  │ email   │ format    │ ✗ FAIL   │ 2           │ 5.00%        │ HIGH    │
│ orders     │ status  │ enum      │ ✓ PASS   │ -           │ -            │ HIGH    │
└────────────┴─────────┴───────────┴──────────┴─────────────┴──────────────┴─────────┘
```

## Python SDK Usage

### Basic Usage

```python
from baselinr import BaselinrClient

# Initialize client
client = BaselinrClient(config_path="config.yml")

# Execute validation
results = client.validate()

# Check results
for result in results:
    if not result.passed:
        print(f"Validation failed: {result.rule.table}.{result.rule.column}")
        print(f"  Reason: {result.failure_reason}")
        print(f"  Failed rows: {result.failed_rows} / {result.total_rows}")
```

### Advanced Usage

```python
from baselinr.validation.executor import ValidationExecutor
from baselinr.connectors.factory import create_connector
from baselinr.config.loader import ConfigLoader

# Load config
config = ConfigLoader.load_from_file("config.yml")

# Create connectors
source_connector = create_connector(config.source)
storage_connector = create_connector(config.storage.connection)

# Create executor
executor = ValidationExecutor(
    config=config,
    source_engine=source_connector.engine,
    storage_engine=storage_connector.engine
)

# Execute validation for specific table
results = executor.execute_validation(table_filter="customers")

# Process results
for result in results:
    if not result.passed:
        print(f"Rule: {result.rule.rule_type}")
        print(f"Table: {result.rule.table}")
        print(f"Column: {result.rule.column}")
        print(f"Failed: {result.failed_rows} / {result.total_rows}")
        print(f"Sample failures: {result.sample_failures}")
```

## Event Integration

Validation failures automatically emit `ValidationFailed` events that integrate with your alert hooks:

```yaml
hooks:
  enabled: true
  hooks:
    - type: logging
      log_level: WARNING
    
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_URL}
      channels:
        - data-quality-alerts
```

The `ValidationFailed` event includes:
- Table and column information
- Rule type and configuration
- Failure reason
- Sample failures (up to 10 rows)
- Total failures and failure rate
- Severity level

## Storage

Validation results are stored in the `baselinr_validation_results` table:

```sql
SELECT 
    table_name,
    column_name,
    rule_type,
    passed,
    failed_rows,
    failure_rate,
    severity,
    validated_at
FROM baselinr_validation_results
WHERE validated_at > NOW() - INTERVAL '7 days'
ORDER BY validated_at DESC;
```

## CI/CD Integration

Use validation in CI/CD pipelines to fail builds on data quality issues:

```bash
#!/bin/bash
# Fail build if any high-severity validations fail

baselinr validate --config config.yml --output results.json

# Check for high-severity failures
FAILED=$(jq '.results[] | select(.rule.severity == "high" and .passed == false)' results.json)

if [ -n "$FAILED" ]; then
    echo "High-severity validation failures detected!"
    exit 1
fi
```

## Best Practices

1. **Start with High-Severity Rules**: Focus on critical data quality issues first
2. **Use Appropriate Severity Levels**: 
   - `high`: Critical business rules (email format, referential integrity)
   - `medium`: Important but not critical (range checks)
   - `low`: Informational checks
3. **Combine with Drift Detection**: Use validation for explicit rules, drift detection for statistical anomalies
4. **Monitor Validation Trends**: Track failure rates over time to identify data quality degradation
5. **Sample Failures**: Review sample failures to understand root causes
6. **Enable Event Hooks**: Set up alerting for validation failures to catch issues early

## Database Support

Validation works with all supported databases:
- PostgreSQL
- Snowflake
- SQLite
- MySQL
- BigQuery
- Redshift

Note: Some validators may have database-specific behavior (e.g., regex syntax differences).

## Future Extensibility

The validation system is designed for extensibility:

- **Great Expectations Provider**: Integrate existing GX expectations
- **Soda Provider**: Use Soda checks
- **Custom Providers**: Implement your own validation provider

See the provider architecture in `baselinr/integrations/validation/base.py` for details on creating custom providers.

## Troubleshooting

### Validation Not Running

1. Check that validation is enabled: `validation.enabled: true`
2. Verify rules are configured correctly
3. Check logs for validation errors

### False Positives

1. Review rule configuration (patterns, ranges, allowed values)
2. Check sample failures to understand what's failing
3. Adjust severity levels if needed

### Performance Issues

1. Use table filters to validate specific tables
2. Consider sampling for large tables
3. Run validation asynchronously in production

## Related Documentation

- [Drift Detection Guide](DRIFT_DETECTION.md) - Statistical anomaly detection
- [Anomaly Detection Guide](ANOMALY_DETECTION.md) - Outlier detection
- [Events and Hooks](architecture/EVENTS_AND_HOOKS.md) - Alert system
- [Python SDK Guide](PYTHON_SDK.md) - Programmatic API

