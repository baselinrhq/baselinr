# Quality Studio Demo

**🎮 [Try the Live Demo →](https://demo.baselinr.io)**

Complete guide for the Baselinr Quality Studio demo deployment on Cloudflare Pages.

## Overview

The Quality Studio demo is a fully functional version that runs entirely on Cloudflare Pages using pre-generated data, with no database dependencies. This provides a fast, zero-cost demo environment for showcasing all features.

**Live Demo URL**: https://demo.baselinr.io

## Documentation

### Getting Started

- **[Demo Mode Quick Start](DEMO_MODE.md)** - Enable and use demo mode locally
- **[Demo Deployment Guide](DEMO_DEPLOYMENT.md)** - Complete phased deployment approach

### Technical Details

- **[Demo Data Service](DEMO_DATA_SERVICE.md)** - DemoDataService API documentation and usage
- **[Demo Data Structure](DEMO_DATA.md)** - JSON data format and structure

## Quick Links

### For Users

- [How to enable demo mode](DEMO_MODE.md#quick-start)
- [API endpoints available](DEMO_MODE.md#api-endpoints)
- [Example queries](DEMO_MODE.md#examples)

### For Developers

- [Implementation phases](DEMO_DEPLOYMENT.md#overview)
- [Service architecture](DEMO_DATA_SERVICE.md#architecture)
- [Testing guide](DEMO_DATA_SERVICE.md#testing)
- [Performance benchmarks](DEMO_DATA_SERVICE.md#performance)

### For Deployment

- [Cloudflare Pages setup](DEMO_DEPLOYMENT.md#phase-4-cloudflare-pages-functions-setup)
- [Environment configuration](DEMO_MODE.md#environment-variables)
- [CORS configuration](DEMO_MODE.md#features)

## Features

### ✅ What's Included

- **120 profiling runs** across 4 warehouses
- **582 column-level metrics** with realistic distributions
- **54 drift detection events** with varying severity
- **95 unique tables** across multiple schemas
- **156 validation results** with 81% pass rate
- **Full lineage graph** with 16 nodes and 14 edges

### ✅ What Works

- All data endpoints (runs, tables, drift, validation)
- Filtering, sorting, and pagination
- Dashboard metrics and KPIs
- Drift detection and alerts
- Validation results and summaries
- Table overview and metrics
- Quality scores and trends
- Performance: &lt;5ms response times (Cloudflare Pages Functions)

### ❌ What's Disabled

- RCA routes (requires database)
- Chat routes (requires database)
- Write operations (read-only demo)
- Configuration saving (demo is read-only)

## Demo Limitations

The demo runs in **read-only mode** with the following limitations:

- **No data persistence**: All changes are temporary and reset on page refresh
- **Pre-generated data**: Uses static JSON files, not a live database
- **No write operations**: Cannot save configurations or make changes
- **No chat/RCA**: AI-powered features require database backend
- **Sample data only**: Data is realistic but not from a real warehouse

These limitations are intentional to provide a fast, zero-cost demo experience.

## Architecture

The demo uses a serverless architecture on Cloudflare Pages:

```
Next.js Frontend (Static Export)
    ↓
Cloudflare Pages Functions
    ↓
DemoDataService (TypeScript)
    ↓
JSON Files (static assets in /demo_data/)
```

**Deployment**:
- **Hosting**: Cloudflare Pages (free tier)
- **Functions**: Cloudflare Pages Functions (serverless)
- **Data**: Static JSON files served from `/demo_data/`
- **Custom Domain**: demo.baselinr.io

## Performance

- **Initialization**: 4.5ms
- **Average query**: 0.59ms
- **Max query**: 4.5ms
- **10-40x faster** than database mode

## Data Generation

Demo data is generated using `generate_demo_data.py`:

```bash
cd dashboard/backend
python generate_demo_data.py
```

This creates fresh demo data with:
- Realistic distributions
- Validated consistency
- Complete coverage of all features

## Testing

### Integration Tests

```bash
cd dashboard/backend
python test_demo_mode_integration.py
```

### Unit Tests

```bash
pytest test_demo_data_service.py -v
```

### Performance Benchmarks

```bash
python benchmark_demo_service.py
```

## Deployment Status

### Phase 1: Demo Data Generation ✓

- [x] Created `generate_demo_data.py`
- [x] Generated 7 JSON files with demo data
- [x] Validated data consistency
- [x] Documentation complete

### Phase 2: Demo Data Service ✓

- [x] Implemented `DemoDataService` class (18 methods)
- [x] Comprehensive unit tests (40+ tests)
- [x] Performance benchmarks (&lt;5ms queries)
- [x] API documentation complete

### Phase 3: Backend Integration ✓

- [x] Updated `main.py` with demo mode support
- [x] Added `/api/demo/info` endpoint
- [x] Extended CORS for demo domain
- [x] Integration tests passing

### Phase 4: Cloudflare Pages Functions ✓

- [x] Convert routes to Pages Functions
- [x] Deploy with demo data
- [x] Configure custom domain
- [x] Implement demo-data-service for Cloudflare Pages

### Phase 5: Frontend Configuration ✓

- [x] Update Next.js for Cloudflare Pages (static export)
- [x] Add demo mode indicators
- [x] Configure API client for Pages Functions

### Phase 6: Cloudflare Deployment ✓

- [x] Deploy to Cloudflare Pages
- [x] Configure custom domain (demo.baselinr.io)
- [x] Set up environment variables
- [x] Verify all endpoints working

### Phase 7: Documentation & Website Integration ✓

- [x] Update website navbar with demo link
- [x] Update website footer with demo link
- [x] Create/update demo documentation
- [x] Update README with demo info

## Support

For questions or issues:

1. Check the relevant documentation above
2. Run integration tests to verify setup
3. Review logs for error messages
4. See [Troubleshooting](DEMO_MODE.md#troubleshooting)

## Related Documentation

- [Dashboard Architecture](ARCHITECTURE.md)
- [Dashboard Integration](DASHBOARD_INTEGRATION.md)
- [Backend Documentation](backend/README.md)
- [Frontend Documentation](frontend/README.md)

