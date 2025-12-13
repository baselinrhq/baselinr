# Baselinr Quality Studio Integration Guide

This document explains how the Quality Studio integrates with Baselinr core functionality.

## Overview

The Baselinr Quality Studio is a web-based no-code interface that provides configuration management and visualization capabilities. It reads profiling data from the Baselinr storage database and presents it through an interactive UI, while also allowing you to configure your entire data quality setup through visual forms.

```
Baselinr Core              Quality Studio
(Data Collection)         (Configuration & Visualization)
─────────────────         ─────────────────────────────

Baselinr CLI              Quality Studio Backend (FastAPI)
    ↓                                    ↓
Profiling Engine    →  PostgreSQL  ←  Quality Studio Frontend (Next.js)
    ↓                     Storage              ↓
Storage Writer                           User Browser
```

## Database Integration

### Shared Database
Both Phase 1 and Phase 2 use the same PostgreSQL database:

```
postgresql://baselinr:baselinr@localhost:5433/baselinr
```

### Tables Used

**Phase 1 writes to:**
- `baselinr_runs` - Run metadata
- `baselinr_results` - Column metrics
- `baselinr_events` - Drift events

**Quality Studio reads from:**
- All the above tables ✅

## Workflow Integration

### 1. Profile Data (Phase 1)
```bash
cd profile_mesh
baselinr profile --config examples/config.yml
```

This creates entries in the database that the Quality Studio will visualize.

### 2. View Results (Quality Studio)
```bash
# Start dashboard
cd profile_mesh/dashboard/backend
python main.py &

cd profile_mesh/dashboard/frontend
npm run dev
```

Visit http://localhost:3000 to see your profiling results.

## Configuration

### Phase 1 Storage Config
In your `config.yml`:
```yaml
storage:
  type: postgres
  connection:
    host: localhost
    port: 5433
    database: baselinr
    user: baselinr
    password: baselinr
```

### Phase 2 Dashboard Config
In `dashboard/backend/.env`:
```env
BASELINR_DB_URL=postgresql://baselinr:baselinr@localhost:5433/baselinr
```

**Important**: Both must point to the same database!

## Docker Integration

### Current Setup
Both Phase 1 and Phase 2 can share the PostgreSQL container:

```yaml
# profile_mesh/docker/docker-compose.yml
services:
  postgres:
    ports:
      - "5433:5432"  # Accessible to both Phase 1 & 2
```

### Adding Dashboard to Docker (Future)

```yaml
# Add to docker-compose.yml
  dashboard-backend:
    build: ../dashboard/backend
    ports:
      - "8000:8000"
    environment:
      - BASELINR_DB_URL=postgresql://baselinr:baselinr@postgres:5432/baselinr
    depends_on:
      - postgres
  
  dashboard-frontend:
    build: ../dashboard/frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - dashboard-backend
```

## Event Bus Integration (Future)

The dashboard currently polls the database for data. Future enhancement:

```python
# In Baselinr Phase 1
from baselinr.events import EventBus

event_bus = EventBus()
# Emit events that dashboard can listen to

# In Dashboard (future WebSocket integration)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Stream events to frontend in real-time
    pass
```

## Metrics Integration (Phase 1)

Baselinr Phase 1 already has Prometheus metrics. The dashboard complements this:

- **Prometheus**: Low-level profiling metrics (rows profiled, duration, etc.)
- **Dashboard**: High-level business metrics (drift events, table health, trends)

Both can coexist and provide different views of the system.

## Development Workflow

### Typical Usage

1. **Run profiling**:
   ```bash
   baselinr profile --config config.yml
   ```

2. **View in dashboard**:
   - Visit http://localhost:3000
   - See newly profiled data
   - Analyze drift events
   - Export results

3. **Check Prometheus metrics** (if enabled):
   - Visit http://localhost:9090
   - Query raw metrics

4. **View in Dagster** (if using):
   - Visit http://localhost:3000 (Dagster UI)
   - Schedule profiling jobs

## Multi-Environment Support

### Local Development
```bash
# Phase 1
baselinr profile --config config.yml

# Phase 2
cd dashboard
# .env points to localhost:5433
```

### Staging
```bash
# Phase 1
export BASELINR_STORAGE__HOST=staging-db.example.com
baselinr profile --config config.yml

# Phase 2
export BASELINR_DB_URL=postgresql://user:pass@staging-db.example.com/baselinr
python main.py
```

### Production
```bash
# Use production database URLs in both Phase 1 & 2 configs
```

## Security Considerations

### Current (MVP)
- Both Phase 1 and 2 share database credentials
- Dashboard is for internal use only
- No authentication required

### Future
- [ ] Separate read-only database user for dashboard
- [ ] OAuth2/JWT for dashboard access
- [ ] API key for backend-frontend communication
- [ ] VPN/firewall for production access

## Troubleshooting

### Dashboard shows no data
**Problem**: Empty dashboard after fresh install  
**Solutions**:
1. Run Baselinr profiling first: `baselinr profile --config config.yml`
2. Or generate sample data: `python dashboard/backend/sample_data_generator.py`

### Database connection mismatch
**Problem**: Phase 1 writes to one DB, Phase 2 reads from another  
**Solution**: Verify both use same `BASELINR_DB_URL`

### Port conflicts
**Problem**: Port 3000 already in use (Dagster also uses 3000)  
**Solution**: Change dashboard port:
```bash
# Frontend
PORT=3001 npm run dev
```

## API Access from Phase 1

You can programmatically query dashboard data from Baselinr:

```python
import requests

# Get recent runs
response = requests.get("http://localhost:8000/api/runs?limit=10")
runs = response.json()

# Get drift alerts
response = requests.get("http://localhost:8000/api/drift?severity=high")
alerts = response.json()
```

## Monitoring Stack

Complete monitoring setup:

```
Baselinr Phase 1:
- Prometheus metrics (port 9753)
- Structured JSON logs

Baselinr Phase 2:
- Dashboard UI (port 3000)
- Backend API (port 8000)

Docker Stack:
- Prometheus (port 9090)
- Grafana (port 3001)
```

## Summary

The dashboard seamlessly integrates with Baselinr Phase 1 by:
1. ✅ Reading from the same PostgreSQL database
2. ✅ Using the same table schema
3. ✅ Supporting all warehouse types
4. ✅ Complementing existing Dagster/Prometheus monitoring
5. ✅ Providing user-friendly visualization layer

**No changes to Phase 1 are required!** The dashboard is purely additive.

## Quick Start (Combined)

```bash
# 1. Start PostgreSQL (if using Docker)
cd profile_mesh/docker
docker compose up -d postgres

# 2. Run profiling (Phase 1)
cd profile_mesh
baselinr profile --config examples/config.yml

# 3. Start dashboard (Phase 2)
cd dashboard/backend
python main.py &

cd ../frontend
npm run dev

# 4. Visit dashboard
open http://localhost:3000
```

---

For detailed dashboard setup, see [Dashboard Quick Start](QUICKSTART.md)  
For architecture details, see `dashboard/ARCHITECTURE.md`

