# Baselinr Dashboard Backend

FastAPI backend that provides REST API endpoints for the Baselinr Dashboard frontend.

## Features

- RESTful API with FastAPI
- Connects to Baselinr storage database
- Pydantic models for request/response validation
- CORS enabled for frontend integration
- Async database operations
- Export functionality (JSON/CSV)

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file:

```env
BASELINR_DB_URL=postgresql://baselinr:baselinr@localhost:5433/baselinr
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000
```

## Running

### Development
```bash
python main.py
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Endpoints

### Health Check
- `GET /` - Health check

### Dashboard
- `GET /api/dashboard/metrics` - Aggregate metrics

### Runs
- `GET /api/runs` - List profiling runs
- `GET /api/runs/{run_id}` - Get run details

### Drift
- `GET /api/drift` - List drift alerts

### Tables
- `GET /api/tables/{table_name}/metrics` - Get table metrics

### Warehouses
- `GET /api/warehouses` - List warehouses

### Export
- `GET /api/export/runs` - Export runs data
- `GET /api/export/drift` - Export drift data

## Sample Data Generator

Generate sample data for testing:

```bash
python sample_data_generator.py
```

This creates:
- 100 profiling runs
- Column metrics
- Drift events

## Database Schema

Expects these tables from Baselinr Phase 1:

- `baselinr_runs`
- `baselinr_results`
- `baselinr_events`
- `baselinr_table_state` (new incremental metadata cache)

`baselinr_table_state` stores the last snapshot ID, decision, and staleness score per table. The incremental planner and Dagster sensors consult this table to decide whether to skip, partially profile, or fully scan each dataset.

### Incremental Profiling Configuration

Enable incremental profiling in your main Baselinr config:

```yaml
incremental:
  enabled: true
  change_detection:
    metadata_table: baselinr_table_state
  partial_profiling:
    allow_partition_pruning: true
    max_partitions_per_run: 64
  cost_controls:
    enabled: true
    max_rows_scanned: 100000000
    fallback_strategy: sample  # sample | defer | full
    sample_fraction: 0.05
```

With this block enabled the CLI, sensors, and dashboard metrics automatically:

1. Compare warehouse metadata (row counts, partition manifests, snapshot IDs) with `baselinr_table_state`.
2. Skip runs when nothing changed (`profile_skipped_no_change` events are emitted for observability).
3. Issue partial runs when detectors pinpoint specific partitions/batches.
4. Downgrade to sampling or defer when cost guardrails would be exceeded.
5. Persist the final decision, snapshot ID, and cost estimate back into `baselinr_table_state` so subsequent scheduler ticks stay in sync with the dashboard.

## Development

### Adding New Endpoints

1. Define Pydantic model in `models.py`
2. Add database query method in `database.py`
3. Create endpoint in `main.py`

### Testing

```bash
# TODO: Add pytest tests
pytest
```

## Troubleshooting

### Database Connection
```bash
# Test connection
psql "postgresql://baselinr:baselinr@localhost:5433/baselinr"
```

### Check Tables
```sql
\dt baselinr*
```

## Orchestration Integrations

Looking to run profiling plans from Dagster? See `docs/dashboard/backend/DAGSTER.md` for a full guide on the new `baselinr.integrations.dagster` package (assets, sensors, and helper definitions).

