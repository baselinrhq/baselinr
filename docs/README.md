# ProfileMesh Documentation

Welcome to the ProfileMesh documentation! This directory contains all documentation organized by topic.

## 📚 Documentation Structure

### 🚀 [Getting Started](getting-started/)
- **[Quick Start Guide](getting-started/QUICKSTART.md)** - Get up and running in 5 minutes
- **[Installation Guide](getting-started/INSTALL.md)** - Detailed installation instructions

### 📖 [Guides](guides/)
- **[Drift Detection](guides/DRIFT_DETECTION.md)** - Understanding and configuring drift detection
- **[Partition & Sampling](guides/PARTITION_SAMPLING.md)** - Advanced profiling strategies
- **[Parallelism & Batching](guides/PARALLELISM_AND_BATCHING.md)** - Optional parallel execution for faster profiling
- **[Incremental Profiling](guides/INCREMENTAL_PROFILING.md)** - Skip unchanged tables and control profiling costs
- **[Prometheus Metrics](guides/PROMETHEUS_METRICS.md)** - Setting up monitoring and metrics
- **[Retry & Recovery](guides/RETRY_AND_RECOVERY.md)** - Automatic retry for transient warehouse failures
- **[Retry Quick Start](guides/RETRY_QUICK_START.md)** - Quick reference for retry system
- **[Retry Implementation](guides/RETRY_IMPLEMENTATION_SUMMARY.md)** - Technical implementation details

### 🏗️ [Architecture](architecture/)
- **[Project Overview](architecture/PROJECT_OVERVIEW.md)** - High-level system architecture
- **[Events & Hooks](architecture/EVENTS_AND_HOOKS.md)** - Event system and hook architecture
- **[Events Implementation](architecture/EVENTS_IMPLEMENTATION_SUMMARY.md)** - Implementation details

### 🎨 [Dashboard](dashboard/)
- **[Dashboard Quick Start](dashboard/QUICKSTART.md)** - Dashboard setup guide
- **[Dashboard README](dashboard/README.md)** - Dashboard overview and features
- **[Dashboard Architecture](dashboard/ARCHITECTURE.md)** - Dashboard technical architecture
- **[Setup Complete](dashboard/SETUP_COMPLETE.md)** - Post-setup verification
- **[Dashboard Integration](dashboard/DASHBOARD_INTEGRATION.md)** - Integrating with ProfileMesh

#### Backend
- **[Backend README](dashboard/backend/README.md)** - Backend API documentation
- **[Fix Missing Tables](dashboard/backend/FIX_MISSING_TABLES.md)** - Troubleshooting guide
- **[Fix Multiple Tables](dashboard/backend/FIX_MULTIPLE_TABLES.md)** - Database schema fix

#### Frontend
- **[Frontend README](dashboard/frontend/README.md)** - Frontend development guide
- **[Node.js Setup](dashboard/frontend/README_NODEJS.md)** - Node.js installation troubleshooting

### 🛠️ [Development](development/)
- **[Development Guide](development/DEVELOPMENT.md)** - Contributing and development setup
- **[Build Complete](development/BUILD_COMPLETE.md)** - Build status and completion notes

### 🐳 [Docker](docker/)
- **[Metrics Setup](docker/README_METRICS.md)** - Docker metrics and monitoring setup

## 📝 Quick Links

- **Main README**: [../README.md](../README.md) - Project overview and quick start
- **Examples**: [../examples/](../examples/) - Configuration examples
- **Makefile**: [../Makefile](../Makefile) - Common commands

## 🔍 Finding What You Need

- **New to ProfileMesh?** → Start with [Getting Started](getting-started/QUICKSTART.md)
- **Setting up the dashboard?** → See [Dashboard Quick Start](dashboard/QUICKSTART.md)
- **Profiling many tables?** → Enable [Parallelism & Batching](guides/PARALLELISM_AND_BATCHING.md)
- **Configuring drift detection?** → Check [Drift Detection Guide](guides/DRIFT_DETECTION.md)
- **Understanding the architecture?** → Read [Project Overview](architecture/PROJECT_OVERVIEW.md)
- **Troubleshooting?** → Check the relevant component's README or fix guides

## 📄 Documentation Standards

All documentation follows these conventions:
- Markdown format (`.md`)
- Clear headings and structure
- Code examples with syntax highlighting
- Links to related documentation
- Step-by-step instructions where applicable

