"""
Sample data generator for Baselinr Dashboard.

⚠️ DEPRECATED: This script has been superseded by generate_demo_data.py
   which includes additional features for demo deployment:
   - Tables metadata generation
   - Validation results generation
   - Lineage relationships
   - JSON export for Cloudflare Pages demo

   For demo data generation, use: python generate_demo_data.py

Creates realistic sample profiling runs, metrics, and drift events
for all supported warehouse types.
"""

import random
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import create_engine, text
import os

# Database connection
DB_URL = os.getenv(
    "BASELINR_DB_URL",
    "postgresql://baselinr:baselinr@localhost:5433/baselinr"
)

# Sample data configuration
WAREHOUSES = ["postgres", "snowflake", "mysql", "bigquery", "redshift", "sqlite"]
SCHEMAS = ["public", "analytics", "raw", "staging"]
TABLES = ["customers", "orders", "products", "users", "transactions", "inventory"]
COLUMNS = {
    "customers": ["id", "name", "email", "created_at", "country"],
    "orders": ["order_id", "customer_id", "total", "order_date", "status"],
    "products": ["product_id", "name", "price", "category", "stock"],
    "users": ["user_id", "username", "email", "age", "signup_date"],
    "transactions": ["txn_id", "amount", "timestamp", "type", "user_id"],
    "inventory": ["item_id", "quantity", "location", "last_updated", "cost"],
}


def generate_run_id():
    """Generate a unique run ID."""
    return f"run_{uuid4().hex[:12]}"


def generate_event_id():
    """Generate a unique event ID."""
    return f"evt_{uuid4().hex[:12]}"


def generate_runs(engine, num_runs=50):
    """Generate sample profiling runs."""
    print(f"Generating {num_runs} sample runs...")
    
    runs = []
    for _ in range(num_runs):
        run_id = generate_run_id()
        table = random.choice(TABLES)
        warehouse = random.choice(WAREHOUSES)
        schema = random.choice(SCHEMAS)
        
        # Generate timestamp within last 30 days
        days_ago = random.randint(0, 30)
        profiled_at = datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23))
        
        # Random metrics
        row_count = random.randint(1000, 1000000)
        column_count = len(COLUMNS.get(table, []))
        
        status = random.choices(
            ["completed", "success", "failed"],
            weights=[70, 25, 5]
        )[0]
        
        runs.append({
            "run_id": run_id,
            "dataset_name": table,
            "schema_name": schema,
            "warehouse_type": warehouse,
            "profiled_at": profiled_at,
            "status": status,
            "row_count": row_count,
            "column_count": column_count,
            "environment": "development"
        })
    
    # Insert runs
    with engine.connect() as conn:
        for run in runs:
            insert_query = text("""
                INSERT INTO baselinr_runs 
                (run_id, dataset_name, schema_name, profiled_at, environment, 
                 row_count, column_count, status)
                VALUES 
                (:run_id, :dataset_name, :schema_name, :profiled_at, :environment,
                 :row_count, :column_count, :status)
                ON CONFLICT (run_id) DO NOTHING
            """)
            conn.execute(insert_query, run)
        conn.commit()
    
    print(f"Created {len(runs)} runs")
    return runs


def generate_metrics(engine, runs):
    """Generate column-level metrics for runs."""
    print("Generating metrics for runs...")
    
    metrics_count = 0
    with engine.connect() as conn:
        for run in runs:
            table = run["dataset_name"]
            columns = COLUMNS.get(table, [])
            
            for column in columns:
                # Generate realistic metrics based on column name
                if "id" in column.lower():
                    column_type = "INTEGER"
                    null_percent = 0.0
                    distinct_count = run["row_count"]
                elif "email" in column.lower() or "name" in column.lower():
                    column_type = "VARCHAR"
                    null_percent = random.uniform(0, 5)
                    distinct_count = int(run["row_count"] * 0.95)
                elif "date" in column.lower() or "timestamp" in column.lower():
                    column_type = "TIMESTAMP"
                    null_percent = random.uniform(0, 2)
                    distinct_count = int(run["row_count"] * 0.3)
                elif "count" in column.lower() or "quantity" in column.lower():
                    column_type = "INTEGER"
                    null_percent = random.uniform(0, 10)
                    distinct_count = random.randint(100, 10000)
                else:
                    column_type = random.choice(["VARCHAR", "INTEGER", "FLOAT"])
                    null_percent = random.uniform(0, 15)
                    distinct_count = random.randint(10, run["row_count"])
                
                # Insert metrics
                metric_types = ["null_count", "null_percent", "distinct_count", "min", "max"]
                for metric_type in metric_types:
                    if metric_type == "null_count":
                        value = str(int(run["row_count"] * null_percent / 100))
                    elif metric_type == "null_percent":
                        value = str(round(null_percent, 2))
                    elif metric_type == "distinct_count":
                        value = str(distinct_count)
                    elif metric_type == "min":
                        value = "0" if column_type == "INTEGER" else "A"
                    elif metric_type == "max":
                        value = "9999" if column_type == "INTEGER" else "Z"
                    else:
                        value = "0"
                    
                    insert_query = text("""
                        INSERT INTO baselinr_results
                        (run_id, column_name, column_type, metric_name, metric_value)
                        VALUES
                        (:run_id, :column_name, :column_type, :metric_name, :metric_value)
                        ON CONFLICT DO NOTHING
                    """)
                    
                    conn.execute(insert_query, {
                        "run_id": run["run_id"],
                        "column_name": column,
                        "column_type": column_type,
                        "metric_name": metric_type,
                        "metric_value": value
                    })
                    metrics_count += 1
        
        conn.commit()
    
    print(f"Created {metrics_count} metrics")


def generate_drift_events(engine, runs):
    """Generate drift detection events."""
    print("Generating drift events...")
    
    # Generate drift for ~30% of runs
    drift_runs = random.sample(runs, int(len(runs) * 0.3))
    
    events = []
    with engine.connect() as conn:
        for run in drift_runs:
            # Generate 1-3 drift events per run
            num_drifts = random.randint(1, 3)
            
            for _ in range(num_drifts):
                event_id = generate_event_id()
                table = run["dataset_name"]
                columns = COLUMNS.get(table, [])
                column = random.choice(columns)
                
                metric_name = random.choice(["null_percent", "distinct_count", "mean", "stddev"])
                severity = random.choices(
                    ["low", "medium", "high"],
                    weights=[50, 35, 15]
                )[0]
                
                baseline_value = random.uniform(10, 100)
                change_percent = random.uniform(5, 50) if severity == "low" else random.uniform(50, 200)
                current_value = baseline_value * (1 + change_percent / 100)
                
                insert_query = text("""
                    INSERT INTO baselinr_events
                    (event_id, run_id, event_type, table_name, column_name,
                     metric_name, baseline_value, current_value, change_percent,
                     drift_severity, timestamp)
                    VALUES
                    (:event_id, :run_id, 'DataDriftDetected', :table_name, :column_name,
                     :metric_name, :baseline_value, :current_value, :change_percent,
                     :drift_severity, :timestamp)
                    ON CONFLICT DO NOTHING
                """)
                
                conn.execute(insert_query, {
                    "event_id": event_id,
                    "run_id": run["run_id"],
                    "table_name": table,
                    "column_name": column,
                    "metric_name": metric_name,
                    "baseline_value": baseline_value,
                    "current_value": current_value,
                    "change_percent": change_percent,
                    "drift_severity": severity,
                    "timestamp": run["profiled_at"]
                })
                
                events.append(event_id)
        
        conn.commit()
    
    print(f"Created {len(events)} drift events")


def main():
    """Generate all sample data."""
    print("=" * 60)
    print("Baselinr Sample Data Generator")
    print("=" * 60)
    
    # Connect to database
    engine = create_engine(DB_URL)
    
    # Generate data
    runs = generate_runs(engine, num_runs=100)
    generate_metrics(engine, runs)
    generate_drift_events(engine, runs)
    
    print("\n" + "=" * 60)
    print("Sample data generation complete!")
    print("=" * 60)
    print(f"\nGenerated:")
    print(f"  - {len(runs)} profiling runs")
    print(f"  - Column-level metrics for all runs")
    print(f"  - Drift events for ~30% of runs")
    print(f"\nDatabase: {DB_URL}")
    print("\nYou can now start the dashboard and see the sample data!")


if __name__ == "__main__":
    main()

