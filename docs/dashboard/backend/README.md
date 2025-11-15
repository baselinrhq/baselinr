# ProfileMesh Dashboard Backend

FastAPI backend that provides REST API endpoints for the ProfileMesh Dashboard frontend.

## Features

- RESTful API with FastAPI
- Connects to ProfileMesh storage database
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
PROFILEMESH_DB_URL=postgresql://profilemesh:profilemesh@localhost:5433/profilemesh
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

Expects these tables from ProfileMesh Phase 1:

- `profilemesh_runs`
- `profilemesh_results`
- `profilemesh_events`

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
psql "postgresql://profilemesh:profilemesh@localhost:5433/profilemesh"
```

### Check Tables
```sql
\dt profilemesh*
```

## Orchestration Integrations

Looking to run profiling plans from Dagster? See `docs/dashboard/backend/DAGSTER.md` for a full guide on the new `profilemesh.integrations.dagster` package (assets, sensors, and helper definitions).

