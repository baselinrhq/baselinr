# Root Cause Analysis (RCA)

Comprehensive root cause analysis capabilities for Baselinr that correlates anomalies with pipeline runs, code changes, and upstream data issues using the existing lineage graph.

## Overview

The RCA module provides:

- **Temporal Correlation**: Finds events (pipeline runs, deployments) that occurred near the time of an anomaly
- **Lineage Analysis**: Traces upstream anomalies and calculates downstream impact using the lineage graph
- **Pattern Matching**: Learns from historical incidents to improve future root cause identification
- **Multi-Signal Scoring**: Combines temporal proximity, lineage distance, and historical patterns for confident cause identification

## Configuration

Add RCA configuration to your `baselinr.yml`:

```yaml
rca:
  enabled: true
  lookback_window_hours: 24
  max_depth: 5
  max_causes_to_return: 5
  min_confidence_threshold: 0.3
  auto_analyze: true
  enable_pattern_learning: true
  collectors:
    dbt:
      enabled: true
      manifest_path: ./target/manifest.json
    dagster:
      enabled: false
      dagster_instance_path: /path/to/.dagster
      dagster_graphql_url: http://localhost:3000/graphql
    airflow:
      enabled: false
```

## Collecting Pipeline Run Data

### Using DBT Collector

```python
from baselinr.rca.collectors import DbtRunCollector
from sqlalchemy import create_engine

engine = create_engine("postgresql://...")

collector = DbtRunCollector(
    engine=engine,
    project_dir="/path/to/dbt/project"
)

# Collect and store runs
runs_collected = collector.collect_and_store()
```

### Using Dagster Collector

```python
from baselinr.rca.collectors import DagsterRunCollector
from sqlalchemy import create_engine

engine = create_engine("postgresql://...")

collector = DagsterRunCollector(
    engine=engine,
    instance_path="/path/to/.dagster",  # Optional, uses DAGSTER_HOME env var
    graphql_url="http://localhost:3000/graphql"  # Optional
)

# Collect and store runs
runs_collected = collector.collect_and_store()
```

### Manual Registration

```python
from baselinr.rca.models import PipelineRun
from baselinr.rca.storage import RCAStorage
from datetime import datetime

storage = RCAStorage(engine)

run = PipelineRun(
    run_id="run_12345",
    pipeline_name="sales_etl",
    pipeline_type="dbt",
    started_at=datetime.utcnow(),
    status="success",
    affected_tables=["sales", "orders"]
)

storage.write_pipeline_run(run)
```

## Collecting Code Changes

### Using Webhook Integration

```python
from baselinr.rca.collectors import CodeChangeCollector

collector = CodeChangeCollector(engine)

# Handle GitHub webhook
deployment = collector.handle_webhook(
    payload=github_webhook_payload,
    platform="github",
    signature=request.headers.get("X-Hub-Signature-256")
)
```

### Manual Registration

```python
from baselinr.rca.models import CodeDeployment
from datetime import datetime

deployment = CodeDeployment(
    deployment_id="deploy_001",
    deployed_at=datetime.utcnow(),
    git_commit_sha="abc123",
    git_branch="main",
    changed_files=["models/sales.sql"],
    deployment_type="code",
    affected_pipelines=["dbt"]
)

storage.write_code_deployment(deployment)
```

## Performing Root Cause Analysis

### Automatic Analysis (with Event Bus)

When `auto_analyze: true` in config, RCA runs automatically when anomalies are detected:

```python
from baselinr.rca.service import RCAService
from baselinr.events import EventBus

event_bus = EventBus()
service = RCAService(
    engine=engine,
    event_bus=event_bus,
    auto_analyze=True
)

# RCA will automatically trigger when AnomalyDetected event is emitted
```

### Manual Analysis

```python
from baselinr.rca.service import RCAService
from datetime import datetime

service = RCAService(
    engine=engine,
    auto_analyze=False
)

result = service.analyze_anomaly(
    anomaly_id="anomaly_001",
    table_name="sales",
    anomaly_timestamp=datetime.utcnow(),
    schema_name="public",
    column_name="amount",
    metric_name="mean"
)

# Access results
for cause in result.probable_causes:
    print(f"Confidence: {cause['confidence_score']:.2f}")
    print(f"Description: {cause['description']}")
    print(f"Suggested Action: {cause['suggested_action']}")
```

## API Usage

RCA endpoints are available in the dashboard backend:

```bash
# Trigger RCA for an anomaly
POST /api/rca/analyze
{
  "anomaly_id": "anomaly_001",
  "table_name": "sales",
  "anomaly_timestamp": "2024-01-15T10:00:00Z",
  "schema_name": "public"
}

# Get RCA result
GET /api/rca/{anomaly_id}

# List recent RCA results
GET /api/rca/?limit=10

# Get RCA statistics
GET /api/rca/statistics/summary

# Get pipeline runs
GET /api/rca/pipeline-runs/recent?limit=20

# Get code deployments
GET /api/rca/deployments/recent?limit=20

# Get events timeline
GET /api/rca/timeline?start_time=...&end_time=...&asset_name=sales
```

## How It Works

### Temporal Correlation

1. Given an anomaly timestamp, finds events within a lookback window (default: 24 hours)
2. Scores events by temporal proximity using exponential decay
3. Boosts confidence for failed pipeline runs
4. Returns top-scoring correlated events

### Lineage Analysis

1. Traces upstream tables using the lineage graph
2. Finds anomalies that occurred earlier in upstream tables
3. Calculates confidence based on:
   - Lineage distance (closer = higher confidence)
   - Temporal proximity (earlier = higher confidence)
   - Column/metric matching
4. Calculates impact by finding downstream affected tables

### Pattern Matching

1. Searches historical RCA results for similar incidents
2. Identifies recurring patterns (e.g., same cause type for same table)
3. Boosts confidence for causes that match historical patterns
4. Learns from user feedback to improve over time

### Multi-Signal Scoring

Combines multiple signals to produce final confidence scores:

```
confidence = (temporal_proximity × 0.4) + 
             (lineage_distance × 0.3) + 
             (historical_pattern × 0.3)
```

## Example Output

```json
{
  "anomaly_id": "anomaly_001",
  "table_name": "sales",
  "schema_name": "public",
  "column_name": "amount",
  "metric_name": "mean",
  "analyzed_at": "2024-01-15T10:30:00Z",
  "rca_status": "analyzed",
  "probable_causes": [
    {
      "cause_type": "pipeline_failure",
      "cause_id": "run_12345",
      "confidence_score": 0.85,
      "description": "Pipeline 'sales_etl' (dbt) failed 30 minutes before anomaly",
      "affected_assets": ["sales", "orders"],
      "suggested_action": "Check logs for pipeline 'sales_etl' run run_12345",
      "evidence": {
        "temporal_proximity": 0.9,
        "table_relevance": 1.0,
        "time_before_anomaly_minutes": 30,
        "pipeline_status": "failed"
      }
    },
    {
      "cause_type": "code_change",
      "cause_id": "deploy_001",
      "confidence_score": 0.72,
      "description": "Code deployment (code) to branch 'main' 60 minutes before anomaly",
      "affected_assets": ["dbt"],
      "suggested_action": "Review commit abc123 for changes that may affect data quality",
      "evidence": {
        "temporal_proximity": 0.8,
        "deployment_type": "code",
        "git_commit_sha": "abc123"
      }
    }
  ],
  "impact_analysis": {
    "upstream_affected": ["raw_sales"],
    "downstream_affected": ["sales_summary", "reporting"],
    "blast_radius_score": 0.6
  }
}
```

## Extending RCA

### Adding New Collectors

Create a new collector by extending `BaseCollector`:

```python
from baselinr.rca.collectors import BaseCollector
from baselinr.rca.models import PipelineRun

class AirflowRunCollector(BaseCollector):
    def collect(self) -> List[PipelineRun]:
        # Implement Airflow-specific collection logic
        runs = []
        # ... fetch from Airflow API
        return runs

# Register collector
from baselinr.rca.collectors import PipelineRunCollector
PipelineRunCollector.register_collector("airflow", AirflowRunCollector)
```

## Performance Considerations

- **Lookback Window**: Larger windows increase analysis time. Default 24 hours is recommended.
- **Lineage Depth**: Deeper traversals take longer. Limit to 5-10 hops.
- **Pattern Matching**: Disable if not needed to reduce query load.
- **Indexing**: Ensure proper indexes on timestamp and foreign key columns.

## Troubleshooting

### No Causes Found

- Check that pipeline runs/deployments are being collected
- Verify lookback window covers the time period
- Lower `min_confidence_threshold` to see more potential causes

### Low Confidence Scores

- Ensure lineage data is accurate and up-to-date
- Verify timestamps are correct for pipeline runs and anomalies
- Check that affected_tables lists are populated

### Slow Analysis

- Reduce `lookback_window_hours`
- Decrease `max_depth` for lineage traversal
- Disable pattern matching temporarily
- Add indexes to RCA tables

