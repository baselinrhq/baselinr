# Baselinr Documentation

Welcome to the Baselinr documentation! This directory contains all documentation organized by topic.

## 📚 Documentation Structure

### 🚀 [Getting Started](getting-started/)
- **[Quick Start Guide](getting-started/QUICKSTART.md)** - Get up and running in 5 minutes
- **[Installation Guide](getting-started/INSTALL.md)** - Detailed installation instructions

### 📖 [Guides](guides/)
- **[Data Validation](guides/DATA_VALIDATION.md)** ✨ **NEW** - Rule-based data quality validation with format, range, enum, null, uniqueness, and referential integrity checks
- **[Smart Table Selection](guides/SMART_TABLE_SELECTION.md)** ✨ **NEW** - Automatically recommend tables to monitor based on usage patterns and database metadata
- **[Smart Selection Quick Start](guides/SMART_SELECTION_QUICKSTART.md)** ✨ **NEW** - Get started with intelligent table selection in 5 minutes
- **[Root Cause Analysis](guides/ROOT_CAUSE_ANALYSIS.md)** ✨ **NEW** - Automatically correlate anomalies with pipeline runs, code changes, and upstream data issues
- **[Python SDK](guides/PYTHON_SDK.md)** - Complete guide to the Python SDK for programmatic access to Baselinr
- **[Airflow Integration](guides/AIRFLOW_INTEGRATION.md)** ✨ **NEW** - Complete guide to integrating Baselinr with Apache Airflow 2.x
- **[Airflow Quick Start](guides/AIRFLOW_QUICKSTART.md)** ✨ **NEW** - Get started with Airflow integration in 5 minutes
- **[Profiling Enrichment](guides/PROFILING_ENRICHMENT.md)** - Enhanced profiling metrics: null ratios, uniqueness, schema tracking, and data quality metrics
- **[Column-Level Configurations](guides/COLUMN_LEVEL_CONFIGS.md)** - Fine-grained control over profiling, drift, and anomaly detection per column
- **[Drift Detection](guides/DRIFT_DETECTION.md)** - Understanding and configuring drift detection, including type-specific thresholds
- **[Statistical Drift Detection](guides/STATISTICAL_DRIFT_DETECTION.md)** - Advanced statistical tests for drift detection (KS test, PSI, chi-square, etc.)
- **[Slack Alerts](guides/SLACK_ALERTS.md)** - Set up Slack notifications for drift detection events
- **[Partition & Sampling](guides/PARTITION_SAMPLING.md)** - Advanced profiling strategies
- **[Parallelism & Batching](guides/PARALLELISM_AND_BATCHING.md)** - Optional parallel execution for faster profiling
- **[Incremental Profiling](guides/INCREMENTAL_PROFILING.md)** - Skip unchanged tables and control profiling costs
- **[Prometheus Metrics](guides/PROMETHEUS_METRICS.md)** - Setting up monitoring and metrics
- **[Retry & Recovery](guides/RETRY_AND_RECOVERY.md)** - Automatic retry for transient warehouse failures
- **[Retry Quick Start](guides/RETRY_QUICK_START.md)** - Quick reference for retry system
- **[Retry Implementation](guides/RETRY_IMPLEMENTATION_SUMMARY.md)** - Technical implementation details

### 📋 [Schemas & CLI](schemas/)
- **[Query Examples](schemas/QUERY_EXAMPLES.md)** - Query command examples and patterns
- **[Status Command](schemas/STATUS_COMMAND.md)** - Status command reference and examples
- **[UI Command](schemas/UI_COMMAND.md)** - Start Quality Studio with `baselinr ui`
- **[Schema Reference](schemas/SCHEMA_REFERENCE.md)** - Database schema documentation
- **[Migration Guide](schemas/MIGRATION_GUIDE.md)** - Schema upgrade procedures

### 🏗️ [Architecture](architecture/)
- **[Project Overview](architecture/PROJECT_OVERVIEW.md)** - High-level system architecture
- **[Events & Hooks](architecture/EVENTS_AND_HOOKS.md)** - Event system and hook architecture
- **[Events Implementation](architecture/EVENTS_IMPLEMENTATION_SUMMARY.md)** - Implementation details

### 🎨 [Quality Studio](dashboard/)
- **[Quality Studio Quick Start](dashboard/QUICKSTART.md)** - Quality Studio setup guide
- **[Quality Studio README](dashboard/README.md)** - Quality Studio overview and features
- **[Quality Studio Architecture](dashboard/ARCHITECTURE.md)** - Quality Studio technical architecture
- **[Setup Complete](dashboard/SETUP_COMPLETE.md)** - Post-setup verification
- **[Quality Studio Integration](dashboard/DASHBOARD_INTEGRATION.md)** - Integrating with Baselinr

#### Backend
- **[Backend README](dashboard/backend/README.md)** - Backend API documentation
- **[Fix Missing Tables](dashboard/backend/FIX_MISSING_TABLES.md)** - Troubleshooting guide
- **[Fix Multiple Tables](dashboard/backend/FIX_MULTIPLE_TABLES.md)** - Database schema fix

#### Frontend
- **[Frontend README](dashboard/frontend/README.md)** - Frontend development guide
- **[Node.js Setup](dashboard/frontend/README_NODEJS.md)** - Node.js installation troubleshooting

### 🛠️ [Development](development/)
- **[Development Guide](development/DEVELOPMENT.md)** - Contributing and development setup
- **[Git Hooks](development/GIT_HOOKS.md)** - Pre-commit and pre-push hooks setup
- **[Build Complete](development/BUILD_COMPLETE.md)** - Build status and completion notes

### 🐳 [Docker](docker/)
- **[Metrics Setup](docker/README_METRICS.md)** - Docker metrics and monitoring setup

## 📝 Quick Links

- **Main README**: [../README.md](../README.md) - Project overview and quick start
- **Roadmap**: [../ROADMAP.md](../ROADMAP.md) - Planned features and future enhancements
- **Examples**: [../examples/](../examples/) - Configuration examples
- **Makefile**: [../Makefile](../Makefile) - Common commands

## 🔍 Finding What You Need

- **New to Baselinr?** → Start with [Getting Started](getting-started/QUICKSTART.md)
- **Want automated setup?** ✨ **NEW** → See [Smart Selection Quick Start](guides/SMART_SELECTION_QUICKSTART.md) for zero-touch configuration
- **Need data validation?** ✨ **NEW** → See [Data Validation Guide](guides/DATA_VALIDATION.md)
- **Want automatic table discovery?** ✨ **NEW** → See [Smart Table Selection](guides/SMART_TABLE_SELECTION.md)
- **Need root cause analysis?** ✨ **NEW** → See [Root Cause Analysis](guides/ROOT_CAUSE_ANALYSIS.md)
- **Using the Python SDK?** → See [Python SDK Guide](guides/PYTHON_SDK.md)
- **Setting up the Quality Studio?** → See [Quality Studio Quick Start](dashboard/QUICKSTART.md)
- **Setting up Slack alerts?** → See [Slack Alerts Guide](guides/SLACK_ALERTS.md)
- **Profiling many tables?** → Enable [Parallelism & Batching](guides/PARALLELISM_AND_BATCHING.md)
- **Using enrichment metrics?** → See [Profiling Enrichment](guides/PROFILING_ENRICHMENT.md)
- **Configuring column-level controls?** → See [Column-Level Configurations](guides/COLUMN_LEVEL_CONFIGS.md)
- **Configuring drift detection?** → Check [Drift Detection Guide](guides/DRIFT_DETECTION.md)
- **Using statistical tests?** → See [Statistical Drift Detection](guides/STATISTICAL_DRIFT_DETECTION.md)
- **Checking system status?** → See [Status Command](schemas/STATUS_COMMAND.md)
- **Starting the Quality Studio?** → See [UI Command](schemas/UI_COMMAND.md)
- **Querying metadata?** → See [Query Examples](schemas/QUERY_EXAMPLES.md)
- **Understanding the architecture?** → Read [Project Overview](architecture/PROJECT_OVERVIEW.md)
- **Troubleshooting?** → Check the relevant component's README or fix guides

## 📄 Documentation Standards

All documentation follows these conventions:
- Markdown format (`.md`)
- Clear headings and structure
- Code examples with syntax highlighting
- Links to related documentation
- Step-by-step instructions where applicable

