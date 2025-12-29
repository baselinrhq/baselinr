# 🧩 Baselinr

[![PyPI version](https://badge.fury.io/py/baselinr.svg)](https://badge.fury.io/py/baselinr)
[![CI](https://github.com/baselinrhq/baselinr/actions/workflows/cli-e2e.yml/badge.svg)](https://github.com/baselinrhq/baselinr/actions/workflows/cli-e2e.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/baselinrhq/baselinr/blob/main/LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**Open-source data quality monitoring that sets itself up.**

---

## 💡 The Problem

Setting up data quality monitoring is painful. You have to:
- Manually decide which tables matter
- Figure out what "good" looks like for each column  
- Write validation rules from scratch
- Constantly tune thresholds to avoid alert fatigue

Most teams either skip it entirely or spend weeks configuring tools that still miss issues.

## ✨ The Solution

Baselinr profiles your data, learns what "normal" looks like, detects drift and anomalies, runs validation checks, and uses AI to trace issues back to their root cause.

**The twist:** plug in your own LLM API key (OpenAI, Anthropic, etc.) and Baselinr recommends *what* to monitor, *which* validations to run, and *why* something broke—so you're not starting from scratch.

Want full manual control instead? That works too. Define everything yourself with YAML configs. Your choice.

---

## 🎬 See It In Action

> **🎮 [Try the Live Demo →](https://demo.baselinr.io)** — No installation required

<!-- TODO: Replace with actual GIF showing:
1. Running `baselinr profile` and seeing results
2. Drift detection catching an issue
3. Quality Studio dashboard overview
-->

![Quality Studio Demo](https://via.placeholder.com/800x450.png?text=GIF+Placeholder:+Quality+Studio+Demo)
*Quality Studio: Configure monitoring, view drift alerts, and analyze data quality—all through a web UI*

### CLI in Action

```bash
# Profile your tables
$ baselinr profile --config config.yml

Profiling 3 tables...
✓ public.customers     12 columns   45,230 rows   2.3s
✓ public.orders        8 columns    128,445 rows  3.1s  
✓ public.products      15 columns   1,204 rows    0.8s

Completed: 3 tables, 35 columns profiled
```

```bash
# Detect drift from your last run
$ baselinr drift --config config.yml --dataset customers

Drift Report: customers
═══════════════════════════════════════════════════════════

Column            Metric          Change    Severity
─────────────────────────────────────────────────────────
email             null_ratio      +12.3%    ⚠️  MEDIUM
signup_date       distinct_count  +45.2%    🔴 HIGH
status            mean            -2.1%     ✅ LOW

2 columns with significant drift detected
```

---

## 🚀 Quick Start (5 minutes)

### 1. Install

```bash
pip install baselinr
```

### 2. Create a minimal config

```yaml
# config.yml
source:
  type: postgres
  host: localhost
  database: mydb
  username: user
  password: password

storage:
  connection:
    type: postgres
    host: localhost
    database: mydb
    username: user
    password: password
  create_tables: true

# Point to your contracts directory (recommended)
contracts:
  directory: ./contracts
```

### 2b. Create contract files (one per table)

```yaml
# contracts/customers.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
id: customers-contract
status: active

servers:
  development:
    type: postgres
    host: localhost
    database: mydb
    schema: public

dataset:
  - name: customers
    physicalName: public.customers
    type: table
```

> **Note:** You can also use `profiling.tables` in your config for a simpler setup without contracts. See [example configs](#-example-configurations) below.

### 3. Profile your data

```bash
baselinr profile --config config.yml
```

### 4. Run it again later, then check for drift

```bash
baselinr drift --config config.yml --dataset customers
```

### 5. Launch the UI (optional)

```bash
baselinr ui --config config.yml
# Opens Quality Studio at http://localhost:3000
```

That's it. You now have data profiling with historical tracking and drift detection.

---

## 📊 What You Get

| Capability | Description |
|------------|-------------|
| **Automated Profiling** | Column-level metrics: nulls, distinct values, distributions, histograms |
| **Drift Detection** | Statistical comparison between runs with configurable thresholds |
| **Anomaly Detection** | Learns "normal" ranges and flags outliers automatically |
| **Data Validation** | Rule-based checks for format, range, uniqueness, referential integrity |
| **Root Cause Analysis** | Correlates anomalies with pipeline runs and upstream changes |
| **Quality Studio UI** | No-code web interface for configuration and monitoring |

### Supported Databases

PostgreSQL • Snowflake • BigQuery • Redshift • MySQL • SQLite

### Integrations

Dagster • Airflow • dbt

---

## 🛠️ Development Status

> **⚠️ Alpha Release** — Actively developed, APIs may change

Baselinr is in early alpha. The core profiling, drift detection, and UI are functional and tested, but we're still iterating on the API and adding features.

**What works well today:**
- ✅ Data profiling with 20+ metrics
- ✅ Drift detection with multiple strategies
- ✅ Quality Studio web UI
- ✅ PostgreSQL, Snowflake, BigQuery, MySQL, SQLite, Redshift
- ✅ Dagster and Airflow integrations
- ✅ CLI and Python SDK

**What we're working on:**
- 🚧 Improved smart table/column recommendations
- 🚧 More statistical tests for drift detection  
- 🚧 Slack/email alerting (webhook support exists)
- 🚧 Documentation improvements

We'd love your feedback! [Open an issue](https://github.com/baselinrhq/baselinr/issues) or try the [live demo](https://demo.baselinr.io).

---

## 📖 Documentation

- **[Getting Started Guide](docs/getting-started/)** — Installation and first steps
- **[User Guides](docs/guides/)** — Drift detection, validation, integrations
- **[Architecture](docs/architecture/)** — How it works under the hood
- **[Python SDK](docs/guides/PYTHON_SDK.md)** — Programmatic access

---

## 🔧 Example Configurations

<details>
<summary><strong>Smart Table Selection (auto-discover what to monitor)</strong></summary>

```yaml
profiling:
  tables:
    # Monitor all tables in a schema
    - select_schema: true
      schema: analytics
      exclude_patterns:
        - "*_temp"
        - "*_backup"
    
    # Pattern matching
    - pattern: "fact_*"
      schema: warehouse
    
    # Specific high-priority tables
    - table: customers
      schema: public
```

</details>

<details>
<summary><strong>Drift Detection with Statistical Tests</strong></summary>

```yaml
drift_detection:
  strategy: statistical
  statistical:
    tests:
      - ks_test      # Kolmogorov-Smirnov for distributions
      - psi          # Population Stability Index
      - chi_square   # For categorical columns
    sensitivity: medium
```

</details>

<details>
<summary><strong>Validation Rules (in ODCS Contracts)</strong></summary>

Validation rules are defined in ODCS contract files, not in the main config:

```yaml
# contracts/customers.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
dataset:
  - name: customers
    columns:
      - name: email
        quality:
          - type: validity
            dimension: validity
            severity: error
            specification:
              rule: format
              pattern: "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$"

# Contract-level quality rules
quality:
  - type: validity
    dimension: validity
    severity: error
    specification:
      column: amount
      rule: range
      min: 0
      max: 1000000
  
  - type: validity
    dimension: referential_integrity
    severity: error
    specification:
      column: customer_id
      rule: referential
      reference_table: customers
      reference_column: id
```

Enable validation in your config:
```yaml
validation:
  enabled: true
  providers:
    - type: builtin
```

</details>

<details>
<summary><strong>Anomaly Detection</strong></summary>

```yaml
storage:
  enable_expectation_learning: true
  learning_window_days: 30
  min_samples: 5
  enable_anomaly_detection: true
  anomaly_enabled_methods:
    - control_limits
    - iqr
    - ewma
    - seasonality
```

</details>

<details>
<summary><strong>Dagster Integration</strong></summary>

```python
from baselinr.integrations.dagster import build_baselinr_definitions

defs = build_baselinr_definitions(
    config_path="config.yml",
    asset_prefix="baselinr",
    job_name="baselinr_profile_all",
)
```

</details>

<details>
<summary><strong>Python SDK</strong></summary>

```python
from baselinr import BaselinrClient

client = BaselinrClient(config_path="config.yml")

# Profile tables
results = client.profile()
for result in results:
    print(f"{result.dataset_name}: {len(result.columns)} columns")

# Detect drift
drift = client.detect_drift("customers")
print(f"Found {len(drift.column_drifts)} drifting columns")
```

</details>

---

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Development setup
git clone https://github.com/baselinrhq/baselinr.git
cd baselinr
pip install -e ".[dev]"
pytest
```

---

## 📝 License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Baselinr</strong> — Data quality monitoring that sets itself up 🧩
  <br>
  <a href="https://baselinr.io">Website</a> •
  <a href="https://demo.baselinr.io">Live Demo</a> •
  <a href="https://github.com/baselinrhq/baselinr/issues">Issues</a>
</p>
