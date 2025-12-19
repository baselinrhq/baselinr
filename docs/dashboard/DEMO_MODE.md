# Demo Mode Quick Start Guide

## What is Demo Mode?

Demo mode allows the Baselinr Quality Studio backend to run without a database by serving pre-generated data from JSON files. Perfect for demos, testing, and Cloudflare Pages deployment.

## Quick Start

### 1. Enable Demo Mode

```bash
export DEMO_MODE=true
```

### 2. Start the Server

```bash
cd dashboard/backend
uvicorn main:app --reload --port 8000
```

### 3. Verify Demo Mode

```bash
curl http://localhost:8000/
```

Response should show:
```json
{
  "status": "healthy",
  "service": "Baselinr Dashboard API",
  "version": "2.0.0",
  "mode": "demo"
}
```

### 4. Get Demo Info

```bash
curl http://localhost:8000/api/demo/info
```

## Features

### ✅ What Works in Demo Mode

- **All Data Endpoints**: runs, tables, drift, validation, metrics
- **Filtering**: warehouse, schema, table, status, dates, severity
- **Sorting**: any field, ascending/descending
- **Pagination**: offset/limit with total counts
- **Detail Views**: run details, table metrics, drift details
- **Aggregations**: dashboard metrics, summaries, trends
- **Performance**: &lt;5ms response times

### ❌ What's Disabled in Demo Mode

- **RCA Routes**: Requires direct database access
- **Chat Routes**: Requires database engine
- **Write Operations**: Demo is read-only

## Environment Variables

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `DEMO_MODE` | `true`, `false` | `false` | Enable demo mode |

## API Endpoints

### Health Check

```bash
GET /
```

Returns mode indicator.

### Demo Info

```bash
GET /api/demo/info
```

Returns demo metadata and statistics (only in demo mode).

### All Data Endpoints

Same as database mode:
- `GET /api/runs`
- `GET /api/tables`
- `GET /api/drift/alerts`
- `GET /api/drift/summary`
- `GET /api/validation/summary`
- `GET /api/validation/results`
- `GET /api/metrics/dashboard`
- And more...

## Examples

### Get Recent Runs

```bash
curl "http://localhost:8000/api/runs?limit=10&sort_order=desc"
```

### Filter by Warehouse

```bash
curl "http://localhost:8000/api/runs?warehouse=snowflake&limit=20"
```

### Get Drift Alerts

```bash
curl "http://localhost:8000/api/drift/alerts?severity=high&limit=10"
```

### Get Dashboard Metrics

```bash
curl "http://localhost:8000/api/metrics/dashboard"
```

### Get Tables

```bash
curl "http://localhost:8000/api/tables?limit=50"
```

## Switching Modes

### Switch to Demo Mode

```bash
export DEMO_MODE=true
uvicorn main:app --reload
```

### Switch to Database Mode

```bash
unset DEMO_MODE
# or
export DEMO_MODE=false
uvicorn main:app --reload
```

## Data

### Demo Data Location

```
dashboard/backend/demo_data/
├── runs.json               (120 runs)
├── metrics.json            (582 metrics)
├── drift_events.json       (54 events)
├── tables.json             (95 tables)
├── validation_results.json (156 results)
├── lineage.json            (16 nodes, 14 edges)
└── metadata.json           (generation info)
```

### Regenerate Demo Data

```bash
cd dashboard/backend
python generate_demo_data.py
```

This will create fresh demo data with new random values.

## Testing

### Run Integration Tests

```bash
python test_demo_mode_integration.py
```

### Run Unit Tests

```bash
pytest test_demo_data_service.py -v
```

### Run Benchmarks

```bash
python benchmark_demo_service.py
```

## Troubleshooting

### Demo Mode Not Working

**Check environment variable**:
```bash
echo $DEMO_MODE
# Should output: true
```

**Check logs**:
```
INFO: Starting in DEMO MODE - using DemoDataService
```

### Endpoints Returning Errors

**Verify demo data exists**:
```bash
ls dashboard/backend/demo_data/
# Should show 7 JSON files
```

**Regenerate if needed**:
```bash
python generate_demo_data.py
```

### Performance Issues

Demo mode should be very fast (&lt;5ms). If slow:
- Check if files are on slow storage
- Verify JSON files aren't corrupted
- Try regenerating demo data

## Deployment

### Cloudflare Pages

Set environment variable in Pages settings:
```
DEMO_MODE=true
```

### Docker

```dockerfile
ENV DEMO_MODE=true
```

### Heroku

```bash
heroku config:set DEMO_MODE=true
```

## Performance

**Demo Mode**:
- Initialization: 4.5ms
- Average query: 0.59ms
- Max query: 4.5ms

**Database Mode** (for comparison):
- Initialization: 50-100ms
- Average query: 50-200ms
- Max query: 500ms+

**Demo mode is 10-40x faster!**

## Support

For issues or questions:
1. Check `DEMO_DATA_SERVICE_README.md` for detailed docs
2. Run integration tests to verify setup
3. Check logs for error messages

## See Also

- [DEMO_DATA_SERVICE_README.md](DEMO_DATA_SERVICE_README.md) - Detailed service documentation
- [PHASE3_COMPLETE.md](PHASE3_COMPLETE.md) - Integration details
- [demo_data/README.md](demo_data/README.md) - Data structure documentation

