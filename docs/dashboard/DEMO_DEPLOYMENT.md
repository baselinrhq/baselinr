# Quality Studio Demo Deployment - Phased Approach

This document outlines the phased approach for deploying a demo version of the Baselinr Quality Studio to Cloudflare Pages with mock data mode.

## Overview

The demo will be a fully functional version of the Quality Studio that runs entirely on Cloudflare Pages using pre-generated mock data. This approach eliminates the need for a database backend while providing a realistic demonstration of all Quality Studio features.

**Demo URL**: `https://demo.baselinr.io` (or your chosen subdomain)

## Goals

- ✅ Zero-cost hosting (Cloudflare Pages free tier)
- ✅ Fast load times (static assets + edge functions)
- ✅ Realistic demo data showcasing all features
- ✅ No database dependencies
- ✅ Easy to maintain and update

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Cloudflare Pages (Frontend)                 │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Next.js Static Export + Pages Functions          │  │
│  │  - Static HTML/CSS/JS assets                      │  │
│  │  - API routes as Cloudflare Pages Functions       │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│         Cloudflare Pages Functions (Backend)             │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Demo Data Service                                 │  │
│  │  - Serves pre-generated JSON data                  │  │
│  │  - Filters/sorts data in-memory                   │  │
│  │  - No database queries                              │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Pre-generated Demo Data (JSON)               │
│  - runs.json (100+ profiling runs)                       │
│  - metrics.json (column-level metrics)                   │
│  - drift_events.json (drift detection events)             │
│  - tables.json (table metadata)                          │
│  - validation_results.json (validation outcomes)         │
│  - lineage.json (lineage relationships)                   │
└─────────────────────────────────────────────────────────┘
```

## Phase 1: Demo Data Generation & Export

**Goal**: Create a script that generates realistic demo data and exports it to JSON files.

### Tasks

1. **Create demo data generator script**
   - Location: `baselinr/dashboard/backend/generate_demo_data.py`
   - Extend existing `sample_data_generator.py` to export to JSON
   - Generate comprehensive dataset:
     - 100+ profiling runs across multiple warehouses
     - Column-level metrics for all runs
     - 30+ drift events with varying severity
     - Table metadata and relationships
     - Validation results (pass/fail)
     - Lineage relationships (if applicable)

2. **Create demo data directory structure**
   ```
   dashboard/backend/demo_data/
   ├── runs.json
   ├── metrics.json
   ├── drift_events.json
   ├── tables.json
   ├── validation_results.json
   ├── lineage.json
   └── metadata.json (generation timestamp, version, etc.)
   ```

3. **Data requirements**
   - **Runs**: Mix of successful, failed, and in-progress runs
   - **Metrics**: Realistic distributions (null rates, distinct counts, etc.)
   - **Drift Events**: Mix of low/medium/high severity
   - **Tables**: Multiple schemas and warehouses
   - **Time Range**: Data spanning last 30-60 days

### Deliverables

- ✅ `generate_demo_data.py` script
- ✅ `demo_data/` directory with JSON files
- ✅ Documentation on data structure

### Estimated Time: 4-6 hours

---

## Phase 2: Demo Data Service Implementation

**Goal**: Create a service that loads and serves demo data with filtering/sorting capabilities.

### Tasks

1. **Create DemoDataService class**
   - Location: `baselinr/dashboard/backend/demo_data.py`
   - Load all JSON files on initialization
   - Implement filtering methods:
     - `get_runs()` - with warehouse, schema, table, date filters
     - `get_drift_alerts()` - with severity, table filters
     - `get_table_metrics()` - table-specific metrics
     - `get_validation_results()` - validation filtering
     - `get_lineage_graph()` - lineage relationships

2. **Implement in-memory filtering**
   - Date range filtering
   - Text search (table names, schemas)
   - Sorting and pagination
   - Aggregations (counts, summaries)

3. **Add demo mode detection**
   - Environment variable: `DEMO_MODE=true`
   - Feature flag in code

### Deliverables

- ✅ `demo_data.py` with DemoDataService class
- ✅ Unit tests for filtering logic
- ✅ Performance benchmarks (should be &lt;100ms for most queries)

### Estimated Time: 6-8 hours

---

## Phase 3: Backend Integration

**Goal**: Modify backend to support demo mode alongside normal database mode.

### Tasks

1. **Update DatabaseClient**
   - Location: `baselinr/dashboard/backend/database.py`
   - Add demo mode detection
   - Route to DemoDataService when in demo mode
   - Maintain backward compatibility

2. **Update main.py**
   - Add demo mode environment variable check
   - Configure CORS for demo domain
   - Add demo mode indicator endpoint

3. **Create demo-specific routes** (optional)
   - `/api/demo/info` - demo metadata
   - `/api/demo/reset` - reset demo state (if needed)

### Deliverables

- ✅ Updated `database.py` with demo mode support
- ✅ Updated `main.py` with demo configuration
- ✅ Backward compatibility maintained

### Estimated Time: 4-6 hours

---

## Phase 4: Cloudflare Pages Functions Setup

**Goal**: Convert FastAPI routes to Cloudflare Pages Functions.

### Tasks

1. **Create Pages Functions structure**
   ```
   dashboard/frontend/functions/
   ├── api/
   │   ├── runs.ts
   │   ├── drift.ts
   │   ├── tables.ts
   │   ├── metrics.ts
   │   ├── validation.ts
   │   ├── lineage.ts
   │   └── ...
   └── demo/
       └── info.ts
   ```

2. **Convert API routes**
   - Each FastAPI endpoint → Cloudflare Pages Function
   - Use DemoDataService (ported to TypeScript or call Python)
   - Maintain same response format

3. **Handle demo data loading**
   - Option A: Bundle JSON files with deployment
   - Option B: Load from Cloudflare KV/R2 (if needed)
   - Option C: Inline in function (for small datasets)

### Deliverables

- ✅ Cloudflare Pages Functions for all API endpoints
- ✅ Demo data accessible to functions
- ✅ Same API contract as FastAPI version

### Estimated Time: 8-12 hours

---

## Phase 5: Frontend Configuration

**Goal**: Configure Next.js for Cloudflare Pages deployment.

### Tasks

1. **Update next.config.js**
   - Configure for static export OR serverless
   - Set up API URL rewrites for demo mode
   - Add demo mode environment variable

2. **Update API client**
   - Location: `dashboard/frontend/lib/api.ts`
   - Detect demo mode
   - Use relative API paths for Pages Functions

3. **Add demo mode indicator**
   - Banner/notice in UI showing "Demo Mode"
   - Disable write operations (if any)
   - Add link to production docs

### Deliverables

- ✅ Updated Next.js configuration
- ✅ Demo mode UI indicators
- ✅ API client working with Pages Functions

### Estimated Time: 4-6 hours

---

## Phase 6: Cloudflare Deployment Setup

**Goal**: Set up Cloudflare Pages project and deployment pipeline.

### Tasks

1. **Create wrangler.toml**
   - Configure Pages project
   - Set environment variables
   - Configure build settings

2. **Create deployment scripts**
   - Build script for frontend
   - Deploy script using Wrangler CLI
   - CI/CD integration (GitHub Actions)

3. **Set up subdomain**
   - Configure `demo.baselinr.io` (or chosen subdomain)
   - SSL certificate (automatic with Cloudflare)
   - Custom domain routing

### Deliverables

- ✅ `wrangler.toml` configuration
- ✅ Deployment scripts
- ✅ CI/CD pipeline (optional)
- ✅ Demo accessible at subdomain

### Estimated Time: 4-6 hours

---

## Phase 7: Documentation & Website Integration

**Goal**: Add demo links and documentation to the website.

### Tasks

1. **Update website navbar**
   - Add "Try Demo" button/link
   - Link to demo subdomain

2. **Update website footer**
   - Add demo link in Resources section

3. **Create demo documentation page**
   - Location: `docs/dashboard/DEMO.md`
   - Explain demo features
   - Link to demo
   - Note limitations

4. **Update README**
   - Add demo link in main README
   - Add demo section in Quality Studio docs

5. **Add demo badge/banner**
   - Optional: Add to homepage
   - Link to demo

### Deliverables

- ✅ Demo links in navbar and footer
- ✅ Demo documentation page
- ✅ Updated README with demo info

### Estimated Time: 2-4 hours

---

## Phase 8: Testing & Polish

**Goal**: Test demo thoroughly and add polish.

### Tasks

1. **End-to-end testing**
   - Test all pages load correctly
   - Test all API endpoints
   - Test filtering and search
   - Test on mobile devices

2. **Performance optimization**
   - Optimize JSON file sizes
   - Add caching headers
   - Optimize bundle sizes

3. **UI polish**
   - Add demo mode indicators
   - Add helpful tooltips
   - Ensure responsive design

4. **Error handling**
   - Graceful error messages
   - Fallback UI states
   - Loading states
 
### Deliverables

- ✅ Fully tested demo
- ✅ Performance optimized
- ✅ Polished UI

### Estimated Time: 6-8 hours

---

## Total Estimated Time: 38-56 hours

## Quick Start Commands

### Generate Demo Data
```bash
cd baselinr/dashboard/backend
python generate_demo_data.py
```

### Build Frontend
```bash
cd baselinr/dashboard/frontend
npm run build
```

### Deploy to Cloudflare
```bash
wrangler pages deploy dashboard/frontend/out --project-name=baselinr-demo
```

## Environment Variables

```bash
# Demo mode flag
DEMO_MODE=true

# API URL (for frontend)
NEXT_PUBLIC_API_URL=/api

# Cloudflare Pages
CF_PAGES_PROJECT=baselinr-demo
CF_PAGES_BRANCH=main
```

## Maintenance

### Updating Demo Data

1. Regenerate demo data: `python generate_demo_data.py`
2. Commit updated JSON files
3. Redeploy to Cloudflare Pages

### Monitoring

- Cloudflare Analytics (built-in)
- Error tracking (optional: Sentry)
- Performance monitoring (Cloudflare Web Analytics)

## Future Enhancements

- [ ] Add interactive demo scenarios
- [ ] Add demo data refresh mechanism
- [ ] Add demo tour/walkthrough
- [ ] Add demo feedback form
- [ ] Add analytics to track demo usage


