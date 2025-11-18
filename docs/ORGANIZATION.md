# Documentation Organization

This document explains how the Baselinr documentation is organized.

## Structure

All documentation has been consolidated into the `docs/` directory to keep the repository root clean and organized.

```
docs/
├── README.md                    # Documentation index and navigation
│
├── getting-started/              # New user guides
│   ├── QUICKSTART.md           # 5-minute getting started
│   └── INSTALL.md              # Installation instructions
│
├── guides/                      # Feature and usage guides
│   ├── DRIFT_DETECTION.md      # Drift detection guide
│   ├── PARTITION_SAMPLING.md   # Partition and sampling strategies
│   └── PROMETHEUS_METRICS.md   # Metrics and monitoring setup
│
├── architecture/                 # System design and architecture
│   ├── PROJECT_OVERVIEW.md     # High-level project overview
│   ├── EVENTS_AND_HOOKS.md     # Event system architecture
│   └── EVENTS_IMPLEMENTATION_SUMMARY.md  # Implementation details
│
├── dashboard/                    # Dashboard documentation
│   ├── QUICKSTART.md           # Dashboard quick start
│   ├── README.md               # Dashboard overview
│   ├── ARCHITECTURE.md         # Dashboard architecture
│   ├── SETUP_COMPLETE.md       # Setup verification
│   ├── DASHBOARD_INTEGRATION.md # Integration guide
│   ├── backend/                 # Backend-specific docs
│   │   ├── README.md
│   │   ├── FIX_MISSING_TABLES.md
│   │   └── FIX_MULTIPLE_TABLES.md
│   └── frontend/                # Frontend-specific docs
│       ├── README.md
│       └── README_NODEJS.md
│
├── development/                  # Development and contribution
│   ├── DEVELOPMENT.md          # Development guide
│   └── BUILD_COMPLETE.md       # Build status
│
└── docker/                       # Docker-specific documentation
    └── README_METRICS.md       # Docker metrics setup
```

## Root Directory

The root directory now only contains:
- **README.md** - Main project documentation (links to docs/)
- Essential project files (setup.py, requirements.txt, etc.)

## Benefits

1. **Clean Root**: No documentation clutter in the root directory
2. **Easy Navigation**: Logical grouping by topic
3. **Better Discoverability**: Clear structure makes it easy to find what you need
4. **Scalable**: Easy to add new documentation without cluttering

## Finding Documentation

- **New to Baselinr?** → Start with `docs/getting-started/QUICKSTART.md`
- **Setting up dashboard?** → See `docs/dashboard/QUICKSTART.md`
- **Understanding architecture?** → Check `docs/architecture/PROJECT_OVERVIEW.md`
- **Need a specific guide?** → Browse `docs/guides/`
- **Contributing?** → Read `docs/development/DEVELOPMENT.md`

## Links Updated

All internal links in documentation files have been updated to reflect the new structure. The main README.md now includes a documentation section pointing to the `docs/` directory.

