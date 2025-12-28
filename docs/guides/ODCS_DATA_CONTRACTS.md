# ODCS Data Contracts Guide

This guide explains how to use Open Data Contract Standard (ODCS) contracts with Baselinr.

## Overview

Baselinr supports the [Open Data Contract Standard (ODCS)](https://bitol-io.github.io/open-data-contract-standard/) v3.1.0 for defining data contracts. This integration provides a standardized way to define:

- Dataset schemas and column definitions
- Data quality rules and validation
- Service Level Agreements (SLAs)
- Data ownership and stakeholders
- Access roles and permissions

## Architecture

Baselinr uses a **hybrid architecture** where:

- **Global config (`baselinr.yml`)** - Tool-specific settings (connections, execution, hooks, monitoring)
- **ODCS Contracts (`*.odcs.yaml`)** - Dataset definitions, quality rules, and SLAs

This separation provides:
- **Portability**: Contracts can be shared across tools
- **Clarity**: Clear distinction between "what the data is" vs "how the tool runs"
- **Standards compliance**: Industry-standard contract format

## Directory Structure

```
project/
├── baselinr.yml              # Tool configuration
└── contracts/                # ODCS data contracts
    ├── customers.odcs.yaml
    ├── orders.odcs.yaml
    └── analytics/
        └── metrics.odcs.yaml
```

## Configuration

### Enable Contracts

Add the `contracts` section to your `baselinr.yml`:

```yaml
contracts:
  directory: ./contracts          # Path to contracts directory
  file_patterns:
    - "*.odcs.yaml"
    - "*.odcs.yml"
  recursive: true                 # Search subdirectories
  validate_on_load: true          # Validate contracts on load
  strict_validation: false        # Treat warnings as errors
```

## Writing Contracts

### Basic Contract Structure

```yaml
kind: DataContract
apiVersion: v3.1.0
id: customers-contract
version: 1.0.0
status: active

info:
  title: Customers Dataset
  description: Core customer data
  owner: data-team@company.com
  domain: sales

servers:
  production:
    type: postgres
    host: prod-db.company.com
    database: production
    schema: public
  development:
    type: postgres
    host: localhost
    database: development

dataset:
  - name: customers
    physicalName: public.customers
    type: table
    columns:
      - name: customer_id
        logicalType: integer
        isPrimaryKey: true
        isNullable: false
      - name: email
        logicalType: string
        isNullable: false
        classification: pii

quality:
  - type: validity
    dimension: completeness
    specification:
      column: email
      rule: not_null
    severity: error

servicelevels:
  - property: freshness
    value: 24
    unit: hours

stakeholders:
  - username: data-team
    role: Data Owner
    email: data-team@company.com
```

### Column Types

Supported logical types:
- `string`, `text`, `integer`, `bigint`, `smallint`, `tinyint`
- `float`, `double`, `decimal`, `numeric`
- `boolean`, `date`, `time`, `timestamp`, `timestamptz`
- `binary`, `array`, `map`, `struct`, `json`, `uuid`
- `geography`, `geometry`, `variant`, `object`

### Quality Rules

Define quality rules at contract, dataset, or column level:

```yaml
quality:
  # Not null check
  - type: validity
    dimension: completeness
    specification:
      column: customer_id
      rule: not_null
    severity: error
    
  # Unique check
  - type: validity
    dimension: uniqueness
    specification:
      column: email
      rule: unique
    severity: error
    
  # Format validation
  - type: validity
    dimension: validity
    specification:
      column: email
      rule: format
      pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
    severity: error
    
  # Range check
  - type: validity
    dimension: validity
    specification:
      column: amount
      rule: range
      minValue: 0
      maxValue: 1000000
    severity: warning
    
  # Enum validation
  - type: validity
    dimension: validity
    specification:
      column: status
      rule: enum
      values: [active, inactive, suspended]
    severity: error
    
  # Referential integrity
  - type: validity
    dimension: consistency
    specification:
      column: customer_id
      rule: referential
      referenceTable: customers
      referenceColumn: id
    severity: error
```

### Service Level Agreements

Define SLAs for your data:

```yaml
servicelevels:
  - property: freshness
    value: 24
    unit: hours
    description: Data should be updated daily
    
  - property: availability
    value: 99.9
    unit: percent
    description: Target availability
    
  - property: latency
    value: 5
    unit: minutes
    description: Max processing delay
    
  - property: retention
    value: 7
    unit: years
    description: Data retention requirement
```

### Data Classification

Classify columns with PII or sensitive data:

```yaml
columns:
  - name: email
    classification: pii
    
  - name: ssn
    classification: restricted
    
  - name: credit_card
    classification: pci
```

Supported classifications: `public`, `internal`, `confidential`, `restricted`, `pii`, `phi`, `pci`

## CLI Commands

### List Contracts

```bash
baselinr contracts list --config baselinr.yml
```

### Validate Contracts

```bash
baselinr contracts validate --config baselinr.yml
baselinr contracts validate --config baselinr.yml --strict
```

### Show Contract Details

```bash
baselinr contracts show --config baselinr.yml --contract customers-contract
baselinr contracts show --config baselinr.yml --contract customers-contract --format yaml
```

### List Validation Rules

```bash
baselinr contracts rules --config baselinr.yml
baselinr contracts rules --config baselinr.yml --contract customers-contract
```

## Python SDK

### Load Contracts

```python
from baselinr import BaselinrClient

client = BaselinrClient(config_path="baselinr.yml")

# Get all contracts
contracts = client.contracts
print(f"Loaded {len(contracts)} contracts")

# Get specific contract
contract = client.get_contract("customers-contract")
print(f"Contract: {contract.info.title}")

# Get dataset names
datasets = client.get_contract_datasets()
print(f"Datasets: {datasets}")
```

### Validate Contracts

```python
# Validate all contracts
result = client.validate_contracts()
if result['valid']:
    print("All contracts valid!")
else:
    for error in result['errors']:
        print(f"Error: [{error['contract']}] {error['message']}")
```

### Get Validation Rules

```python
# Get rules from all contracts
rules = client.get_validation_rules_from_contracts()
for rule in rules:
    print(f"{rule.type} on {rule.table}.{rule.column}")
```

### Get Dataset Metadata

```python
# Get metadata from contracts
metadata = client.get_dataset_metadata_from_contracts()
for ds in metadata:
    print(f"{ds.name}: {len(ds.columns)} columns, owner: {ds.owner}")
```

## Dashboard UI

Access the contracts UI at `/config/contracts` in the dashboard:

- View all loaded contracts
- Validate contracts
- See quality rules and SLAs
- View stakeholders and ownership

## Best Practices

1. **One contract per domain** - Group related tables in a single contract
2. **Use meaningful IDs** - `customers-contract` not `contract-1`
3. **Document ownership** - Always specify `info.owner`
4. **Define SLAs** - Set clear expectations for data freshness
5. **Classify sensitive data** - Mark PII columns with `classification`
6. **Version your contracts** - Use semantic versioning
7. **Store contracts in version control** - Track changes over time

## Reference

- [ODCS Specification](https://bitol-io.github.io/open-data-contract-standard/)
- [ODCS v3.1.0 Changelog](https://bitol-io.github.io/open-data-contract-standard/v3.1.0/changelog/)
- [Example Contracts](../examples/contracts/)

