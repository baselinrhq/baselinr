"""
Demo data generator for Baselinr Quality Studio.

Creates realistic demo data for all Quality Studio features and exports to JSON files.
This data is used for the Cloudflare Pages demo deployment.
"""

import json
import random
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import List, Dict, Any


# Demo data configuration
WAREHOUSES = ["snowflake", "bigquery", "postgres", "redshift"]
SCHEMAS = ["raw", "staging", "analytics", "production"]
TABLES = [
    "customers", "orders", "products", "users", "transactions", 
    "inventory", "payments", "reviews", "shipments", "suppliers",
    "invoices", "employees", "departments", "sales", "returns"
]

COLUMNS = {
    "customers": ["customer_id", "name", "email", "phone", "created_at", "country", "city", "status"],
    "orders": ["order_id", "customer_id", "total_amount", "order_date", "status", "shipping_address"],
    "products": ["product_id", "name", "price", "category", "stock_quantity", "supplier_id"],
    "users": ["user_id", "username", "email", "age", "signup_date", "last_login", "is_active"],
    "transactions": ["txn_id", "amount", "timestamp", "type", "user_id", "status"],
    "inventory": ["item_id", "quantity", "location", "last_updated", "cost", "reorder_level"],
    "payments": ["payment_id", "order_id", "amount", "payment_method", "status", "processed_at"],
    "reviews": ["review_id", "product_id", "user_id", "rating", "comment", "created_at"],
    "shipments": ["shipment_id", "order_id", "carrier", "tracking_number", "shipped_at", "delivered_at"],
    "suppliers": ["supplier_id", "name", "contact_email", "country", "rating"],
    "invoices": ["invoice_id", "order_id", "amount", "due_date", "paid_at", "status"],
    "employees": ["employee_id", "name", "email", "department_id", "hire_date", "salary"],
    "departments": ["department_id", "name", "manager_id", "budget", "location"],
    "sales": ["sale_id", "product_id", "quantity", "revenue", "sale_date", "region"],
    "returns": ["return_id", "order_id", "reason", "refund_amount", "returned_at", "status"],
}

# Lineage relationships (source -> target)
LINEAGE_EDGES = [
    # Raw to Staging
    ("raw.customers", "staging.customers"),
    ("raw.orders", "staging.orders"),
    ("raw.products", "staging.products"),
    ("raw.transactions", "staging.transactions"),
    # Staging to Analytics
    ("staging.customers", "analytics.customers"),
    ("staging.orders", "analytics.orders"),
    ("staging.products", "analytics.products"),
    ("staging.orders", "analytics.sales"),
    ("staging.products", "analytics.sales"),
    # Multiple sources to single target
    ("staging.orders", "production.invoices"),
    ("staging.customers", "production.invoices"),
    ("staging.payments", "production.invoices"),
    ("staging.shipments", "analytics.logistics"),
    ("staging.orders", "analytics.logistics"),
]


def generate_run_id() -> str:
    """Generate a unique run ID."""
    return f"run_{uuid4().hex[:12]}"


def generate_event_id() -> str:
    """Generate a unique event ID."""
    return f"evt_{uuid4().hex[:12]}"


def generate_runs(num_runs: int = 120) -> List[Dict[str, Any]]:
    """Generate sample profiling runs."""
    print(f"Generating {num_runs} sample runs...")
    
    runs = []
    # Generate runs spanning last 60 days
    for i in range(num_runs):
        run_id = generate_run_id()
        table = random.choice(TABLES)
        warehouse = random.choice(WAREHOUSES)
        schema = random.choice(SCHEMAS)
        
        # Generate timestamp within last 60 days with more recent bias
        days_ago = random.randint(0, 60)
        profiled_at = datetime.now(timezone.utc) - timedelta(days=days_ago, hours=random.randint(0, 23))
        
        # Random metrics
        row_count = random.randint(1000, 5000000)
        column_count = len(COLUMNS.get(table, []))
        
        # Status distribution
        status = random.choices(
            ["completed", "success", "failed", "running"],
            weights=[65, 20, 10, 5]
        )[0]
        
        duration_seconds = random.uniform(5.0, 300.0) if status in ["completed", "success"] else None
        
        runs.append({
            "run_id": run_id,
            "dataset_name": table,
            "schema_name": schema,
            "warehouse_type": warehouse,
            "profiled_at": profiled_at.isoformat(),
            "status": status,
            "row_count": row_count,
            "column_count": column_count,
            "duration_seconds": round(duration_seconds, 2) if duration_seconds else None,
            "environment": "production",
            "has_drift": False  # Will be updated when generating drift events
        })
    
    print(f"[OK] Created {len(runs)} runs")
    return runs


def generate_metrics(runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate column-level metrics for runs."""
    print("Generating metrics for runs...")
    
    all_metrics = []
    
    for run in runs:
        # Only generate metrics for successful runs
        if run["status"] not in ["completed", "success"]:
            continue
            
        table = run["dataset_name"]
        columns = COLUMNS.get(table, [])
        
        for column in columns:
            # Generate realistic metrics based on column name
            if "id" in column.lower():
                column_type = "INTEGER"
                null_percent = 0.0
                distinct_count = run["row_count"]
                min_value = "1"
                max_value = str(run["row_count"])
            elif "email" in column.lower():
                column_type = "VARCHAR"
                null_percent = random.uniform(0, 3)
                distinct_count = int(run["row_count"] * random.uniform(0.90, 0.98))
                min_value = "a@example.com"
                max_value = "z@example.com"
            elif "name" in column.lower():
                column_type = "VARCHAR"
                null_percent = random.uniform(0, 5)
                distinct_count = int(run["row_count"] * random.uniform(0.50, 0.95))
                min_value = "Aaron"
                max_value = "Zoe"
            elif "date" in column.lower() or "timestamp" in column.lower() or "_at" in column.lower():
                column_type = "TIMESTAMP"
                null_percent = random.uniform(0, 2)
                distinct_count = int(run["row_count"] * 0.3)
                min_value = "2023-01-01T00:00:00"
                max_value = "2024-12-31T23:59:59"
            elif "count" in column.lower() or "quantity" in column.lower() or "amount" in column.lower():
                column_type = "NUMERIC"
                null_percent = random.uniform(0, 8)
                distinct_count = random.randint(100, 10000)
                min_value = "0"
                max_value = str(random.randint(1000, 999999))
            elif "status" in column.lower():
                column_type = "VARCHAR"
                null_percent = random.uniform(0, 1)
                distinct_count = random.randint(3, 10)
                min_value = "active"
                max_value = "pending"
            else:
                column_type = random.choice(["VARCHAR", "INTEGER", "FLOAT"])
                null_percent = random.uniform(0, 15)
                distinct_count = random.randint(10, run["row_count"])
                min_value = "0"
                max_value = "999"
            
            null_count = int(run["row_count"] * null_percent / 100)
            distinct_percent = (distinct_count / run["row_count"]) * 100 if run["row_count"] > 0 else 0
            
            # Create metric entry
            metric = {
                "run_id": run["run_id"],
                "column_name": column,
                "column_type": column_type,
                "null_count": null_count,
                "null_percent": round(null_percent, 2),
                "distinct_count": distinct_count,
                "distinct_percent": round(distinct_percent, 2),
                "min_value": min_value,
                "max_value": max_value,
            }
            
            # Add mean and stddev for numeric types
            if column_type in ["INTEGER", "NUMERIC", "FLOAT"]:
                metric["mean"] = round(random.uniform(10.0, 1000.0), 2)
                metric["stddev"] = round(random.uniform(5.0, 100.0), 2)
            
            all_metrics.append(metric)
    
    print(f"[OK] Created {len(all_metrics)} metrics")
    return all_metrics


def generate_tables_metadata(runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate table metadata based on runs."""
    print("Generating tables metadata...")
    
    # Group runs by table
    table_groups = {}
    for run in runs:
        key = (run["dataset_name"], run["schema_name"], run["warehouse_type"])
        if key not in table_groups:
            table_groups[key] = []
        table_groups[key].append(run)
    
    tables = []
    for (table_name, schema_name, warehouse_type), table_runs in table_groups.items():
        # Get most recent run for this table
        sorted_runs = sorted(table_runs, key=lambda x: x["profiled_at"], reverse=True)
        latest_run = sorted_runs[0]
        
        # Count successful runs and drift events
        successful_runs = [r for r in table_runs if r["status"] in ["completed", "success"]]
        drift_count = sum(1 for r in table_runs if r.get("has_drift", False))
        
        # Calculate validation pass rate (will be updated when we generate validations)
        validation_pass_rate = random.uniform(0.75, 0.98)
        
        tables.append({
            "table_name": table_name,
            "schema_name": schema_name,
            "warehouse_type": warehouse_type,
            "last_profiled": latest_run["profiled_at"],
            "row_count": latest_run["row_count"],
            "column_count": latest_run["column_count"],
            "total_runs": len(table_runs),
            "drift_count": drift_count,
            "validation_pass_rate": round(validation_pass_rate, 2),
            "has_recent_drift": drift_count > 0 and any(
                r.get("has_drift") and 
                (datetime.now(timezone.utc) - datetime.fromisoformat(r["profiled_at"])).days < 7
                for r in table_runs
            ),
            "has_failed_validations": validation_pass_rate < 0.90
        })
    
    print(f"[OK] Created metadata for {len(tables)} tables")
    return tables


def generate_drift_events(runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate drift detection events."""
    print("Generating drift events...")
    
    # Select ~30% of successful runs for drift
    successful_runs = [r for r in runs if r["status"] in ["completed", "success"]]
    drift_runs = random.sample(successful_runs, int(len(successful_runs) * 0.30))
    
    events = []
    for run in drift_runs:
        # Mark run as having drift
        run["has_drift"] = True
        
        # Generate 1-3 drift events per run
        num_drifts = random.randint(1, 3)
        
        table = run["dataset_name"]
        columns = COLUMNS.get(table, [])
        
        for _ in range(num_drifts):
            event_id = generate_event_id()
            column = random.choice(columns)
            
            metric_name = random.choice(["null_percent", "distinct_count", "mean", "row_count"])
            severity = random.choices(
                ["low", "medium", "high"],
                weights=[50, 35, 15]
            )[0]
            
            # Generate baseline and current values
            if metric_name == "null_percent":
                baseline_value = random.uniform(1, 10)
                change_percent = random.uniform(10, 30) if severity == "low" else random.uniform(30, 100)
            elif metric_name == "distinct_count":
                baseline_value = random.uniform(1000, 100000)
                change_percent = random.uniform(5, 15) if severity == "low" else random.uniform(15, 50)
            elif metric_name == "mean":
                baseline_value = random.uniform(100, 1000)
                change_percent = random.uniform(10, 25) if severity == "low" else random.uniform(25, 75)
            else:  # row_count
                baseline_value = random.uniform(10000, 1000000)
                change_percent = random.uniform(5, 20) if severity == "low" else random.uniform(20, 60)
            
            # Randomly decide if drift is increase or decrease
            if random.random() > 0.5:
                change_percent = -change_percent
            
            current_value = baseline_value * (1 + change_percent / 100)
            
            events.append({
                "event_id": event_id,
                "run_id": run["run_id"],
                "table_name": table,
                "column_name": column,
                "metric_name": metric_name,
                "baseline_value": round(baseline_value, 2),
                "current_value": round(current_value, 2),
                "change_percent": round(change_percent, 2),
                "severity": severity,
                "timestamp": run["profiled_at"],
                "warehouse_type": run["warehouse_type"]
            })
    
    print(f"[OK] Created {len(events)} drift events")
    return events


def generate_validation_results(runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate validation results for runs."""
    print("Generating validation results...")
    
    rule_types = ["not_null", "unique", "range", "format", "enum", "referential"]
    severities = ["low", "medium", "high"]
    
    results = []
    result_id = 1
    
    # Generate validations for ~70% of successful runs
    successful_runs = [r for r in runs if r["status"] in ["completed", "success"]]
    validation_runs = random.sample(successful_runs, int(len(successful_runs) * 0.70))
    
    for run in validation_runs:
        table = run["dataset_name"]
        schema = run["schema_name"]
        columns = COLUMNS.get(table, [])
        
        # Generate 1-4 validation results per run
        num_validations = random.randint(1, 4)
        
        for _ in range(num_validations):
            rule_type = random.choice(rule_types)
            column = random.choice(columns) if rule_type != "referential" else None
            
            # 80% pass rate
            passed = random.random() < 0.80
            severity = random.choice(severities)
            
            total_rows = run["row_count"]
            failed_rows = 0 if passed else random.randint(1, int(total_rows * 0.15))
            failure_rate = (failed_rows / total_rows) if total_rows > 0 else 0
            
            failure_reason = None
            if not passed:
                if rule_type == "not_null":
                    failure_reason = f"Found {failed_rows} null values in {column}"
                elif rule_type == "unique":
                    failure_reason = f"Found {failed_rows} duplicate values in {column}"
                elif rule_type == "range":
                    failure_reason = f"Found {failed_rows} values outside expected range in {column}"
                elif rule_type == "format":
                    failure_reason = f"Found {failed_rows} values not matching expected format in {column}"
                elif rule_type == "enum":
                    failure_reason = f"Found {failed_rows} values not in allowed set in {column}"
                elif rule_type == "referential":
                    failure_reason = f"Found {failed_rows} rows with missing foreign key references"
            
            results.append({
                "id": result_id,
                "run_id": run["run_id"],
                "table_name": table,
                "schema_name": schema,
                "column_name": column,
                "rule_type": rule_type,
                "passed": passed,
                "failure_reason": failure_reason,
                "total_rows": total_rows,
                "failed_rows": failed_rows,
                "failure_rate": round(failure_rate, 4),
                "severity": severity,
                "validated_at": run["profiled_at"]
            })
            
            result_id += 1
    
    print(f"[OK] Created {len(results)} validation results")
    return results


def generate_lineage_relationships() -> Dict[str, Any]:
    """Generate lineage graph with nodes and edges."""
    print("Generating lineage relationships...")
    
    nodes = []
    edges = []
    node_id_map = {}
    
    # Create nodes for all tables in lineage
    tables_in_lineage = set()
    for source, target in LINEAGE_EDGES:
        tables_in_lineage.add(source)
        tables_in_lineage.add(target)
    
    for table_ref in sorted(tables_in_lineage):
        schema, table = table_ref.split(".")
        warehouse = random.choice(WAREHOUSES)
        node_id = f"{schema}.{table}"
        node_id_map[table_ref] = node_id
        
        nodes.append({
            "id": node_id,
            "type": "table",
            "label": f"{schema}.{table}",
            "schema": schema,
            "table": table,
            "database": None,
            "metadata": {
                "warehouse_type": warehouse,
                "row_count": random.randint(1000, 1000000),
                "column_count": len(COLUMNS.get(table, [])),
            }
        })
    
    # Create edges
    for source_ref, target_ref in LINEAGE_EDGES:
        source_id = node_id_map[source_ref]
        target_id = node_id_map[target_ref]
        
        edges.append({
            "source": source_id,
            "target": target_id,
            "relationship_type": "derives_from",
            "confidence": round(random.uniform(0.85, 1.0), 2),
            "transformation": None,
            "provider": "manual",
            "metadata": {}
        })
    
    lineage_graph = {
        "nodes": nodes,
        "edges": edges,
        "root_id": None,
        "direction": "both"
    }
    
    print(f"[OK] Created lineage graph with {len(nodes)} nodes and {len(edges)} edges")
    return lineage_graph


def generate_table_quality_scores(
    tables: List[Dict[str, Any]],
    runs: List[Dict[str, Any]],
    validation_results: List[Dict[str, Any]],
    drift_events: List[Dict[str, Any]],
    num_scores_per_table: int = 10
) -> List[Dict[str, Any]]:
    """Generate realistic table-level quality scores."""
    print(f"\nGenerating {num_scores_per_table} quality scores per table...")
    
    table_quality_scores = []
    
    for table in tables:
        table_name = table["table_name"]
        schema_name = table["schema_name"]
        
        # Get runs for this table
        table_runs = [r for r in runs 
                     if r["dataset_name"] == table_name and r["schema_name"] == schema_name]
        
        if not table_runs:
            continue
        
        # Sort runs by date (oldest first)
        table_runs = sorted(table_runs, key=lambda r: r["profiled_at"])
        
        # Generate quality scores for the most recent runs
        recent_runs = table_runs[-num_scores_per_table:]
        
        # Initial quality score (varies by table to make it realistic)
        base_score = random.uniform(70, 95)
        
        for idx, run in enumerate(recent_runs):
            run_date = datetime.fromisoformat(run["profiled_at"])
            
            # Add some variation over time (slight improvement trend)
            trend_adjustment = idx * random.uniform(0.5, 2.0)
            overall_score = min(100, base_score + trend_adjustment + random.uniform(-3, 3))
            
            # Individual component scores (with some variation)
            completeness_score = min(100, overall_score + random.uniform(-5, 5))
            validity_score = min(100, overall_score + random.uniform(-8, 3))
            consistency_score = min(100, overall_score + random.uniform(-6, 4))
            freshness_score = min(100, overall_score + random.uniform(-4, 6))
            uniqueness_score = min(100, overall_score + random.uniform(-7, 3))
            accuracy_score = min(100, overall_score + random.uniform(-10, 2))
            
            # Determine status based on overall score
            if overall_score >= 80:
                status = "healthy"
                total_issues = random.randint(0, 5)
                critical_issues = 0
                warnings = total_issues
            elif overall_score >= 60:
                status = "warning"
                total_issues = random.randint(5, 15)
                critical_issues = random.randint(1, 3)
                warnings = total_issues - critical_issues
            else:
                status = "critical"
                total_issues = random.randint(15, 30)
                critical_issues = random.randint(5, 10)
                warnings = total_issues - critical_issues
            
            # Period covered by this score (e.g., last 7 days from run date)
            period_end = run_date
            period_start = run_date - timedelta(days=7)
            
            score = {
                "table_name": table_name,
                "schema_name": schema_name,
                "run_id": run["run_id"],
                "overall_score": round(overall_score, 2),
                "completeness_score": round(completeness_score, 2),
                "validity_score": round(validity_score, 2),
                "consistency_score": round(consistency_score, 2),
                "freshness_score": round(freshness_score, 2),
                "uniqueness_score": round(uniqueness_score, 2),
                "accuracy_score": round(accuracy_score, 2),
                "status": status,
                "total_issues": total_issues,
                "critical_issues": critical_issues,
                "warnings": warnings,
                "calculated_at": run_date.isoformat(),
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat()
            }
            
            table_quality_scores.append(score)
    
    print(f"[OK] Generated {len(table_quality_scores)} table quality scores")
    return table_quality_scores


def generate_column_quality_scores(
    tables: List[Dict[str, Any]],
    runs: List[Dict[str, Any]],
    metrics: List[Dict[str, Any]],
    num_scores_per_table: int = 10
) -> List[Dict[str, Any]]:
    """Generate realistic column-level quality scores."""
    print(f"\nGenerating column quality scores for recent runs...")
    
    column_quality_scores = []
    score_id = 1
    
    for table in tables:
        table_name = table["table_name"]
        schema_name = table["schema_name"]
        
        # Get runs for this table
        table_runs = [r for r in runs 
                     if r["dataset_name"] == table_name and r["schema_name"] == schema_name]
        
        if not table_runs:
            continue
        
        # Sort runs by date and get recent ones
        table_runs = sorted(table_runs, key=lambda r: r["profiled_at"])
        recent_runs = table_runs[-num_scores_per_table:]
        
        # Get columns for this table
        columns = COLUMNS.get(table_name, [])
        
        for run in recent_runs:
            run_date = datetime.fromisoformat(run["profiled_at"])
            
            # Generate score for each column
            for column_name in columns:
                # Base score varies by column (some columns are naturally higher quality)
                base_score = random.uniform(70, 95)
                
                # Add some variation
                overall_score = min(100, base_score + random.uniform(-5, 5))
                
                # Component scores
                completeness_score = min(100, overall_score + random.uniform(-5, 5))
                validity_score = min(100, overall_score + random.uniform(-8, 3))
                consistency_score = min(100, overall_score + random.uniform(-6, 4))
                freshness_score = min(100, overall_score + random.uniform(-4, 6))
                uniqueness_score = min(100, overall_score + random.uniform(-7, 3))
                accuracy_score = min(100, overall_score + random.uniform(-10, 2))
                
                # Determine status
                if overall_score >= 80:
                    status = "healthy"
                elif overall_score >= 60:
                    status = "warning"
                else:
                    status = "critical"
                
                # Period covered
                period_end = run_date
                period_start = run_date - timedelta(days=7)
                
                score = {
                    "id": score_id,
                    "table_name": table_name,
                    "schema_name": schema_name,
                    "column_name": column_name,
                    "run_id": run["run_id"],
                    "overall_score": round(overall_score, 2),
                    "completeness_score": round(completeness_score, 2),
                    "validity_score": round(validity_score, 2),
                    "consistency_score": round(consistency_score, 2),
                    "freshness_score": round(freshness_score, 2),
                    "uniqueness_score": round(uniqueness_score, 2),
                    "accuracy_score": round(accuracy_score, 2),
                    "status": status,
                    "calculated_at": run_date.isoformat(),
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat()
                }
                
                column_quality_scores.append(score)
                score_id += 1
    
    print(f"[OK] Generated {len(column_quality_scores)} column quality scores")
    return column_quality_scores


def validate_data_consistency(
    runs: List[Dict[str, Any]],
    metrics: List[Dict[str, Any]],
    drift_events: List[Dict[str, Any]],
    validation_results: List[Dict[str, Any]]
) -> bool:
    """Validate data consistency before export."""
    print("\nValidating data consistency...")
    
    issues = []
    
    # Check 1: All run_ids in metrics exist in runs
    run_ids = {r["run_id"] for r in runs}
    metric_run_ids = {m["run_id"] for m in metrics}
    invalid_metric_runs = metric_run_ids - run_ids
    if invalid_metric_runs:
        issues.append(f"Found {len(invalid_metric_runs)} metrics with invalid run_ids")
    
    # Check 2: All run_ids in drift_events exist in runs
    drift_run_ids = {e["run_id"] for e in drift_events}
    invalid_drift_runs = drift_run_ids - run_ids
    if invalid_drift_runs:
        issues.append(f"Found {len(invalid_drift_runs)} drift events with invalid run_ids")
    
    # Check 3: All run_ids in validation_results exist in runs
    validation_run_ids = {v["run_id"] for v in validation_results}
    invalid_validation_runs = validation_run_ids - run_ids
    if invalid_validation_runs:
        issues.append(f"Found {len(invalid_validation_runs)} validation results with invalid run_ids")
    
    # Check 4: No duplicate run_ids
    if len(run_ids) != len(runs):
        issues.append("Found duplicate run_ids")
    
    # Check 5: Date formats are consistent
    for run in runs[:5]:  # Sample check
        try:
            datetime.fromisoformat(run["profiled_at"])
        except:
            issues.append(f"Invalid date format in run {run['run_id']}")
            break
    
    if issues:
        print("[ERROR] Validation failed:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    
    print("[OK] All validation checks passed")
    return True


def export_to_json(
    runs: List[Dict[str, Any]],
    metrics: List[Dict[str, Any]],
    drift_events: List[Dict[str, Any]],
    tables: List[Dict[str, Any]],
    validation_results: List[Dict[str, Any]],
    lineage: Dict[str, Any],
    table_quality_scores: List[Dict[str, Any]],
    column_quality_scores: List[Dict[str, Any]],
    output_dir: str = "demo_data"
) -> None:
    """Export all data to JSON files."""
    print(f"\nExporting data to JSON files in {output_dir}/...")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Export each dataset
    datasets = {
        "runs.json": runs,
        "metrics.json": metrics,
        "drift_events.json": drift_events,
        "tables.json": tables,
        "validation_results.json": validation_results,
        "lineage.json": lineage,
        "table_quality_scores.json": table_quality_scores,
        "column_quality_scores.json": column_quality_scores,
    }
    
    for filename, data in datasets.items():
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Calculate file size
        size_kb = os.path.getsize(filepath) / 1024
        print(f"  [OK] {filename} ({size_kb:.1f} KB)")
    
    # Generate metadata
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator_version": "1.1.0",
        "statistics": {
            "total_runs": len(runs),
            "total_metrics": len(metrics),
            "total_drift_events": len(drift_events),
            "total_tables": len(tables),
            "total_validation_results": len(validation_results),
            "total_lineage_nodes": len(lineage["nodes"]),
            "total_lineage_edges": len(lineage["edges"]),
            "total_table_quality_scores": len(table_quality_scores),
            "total_column_quality_scores": len(column_quality_scores),
        },
        "date_range": {
            "earliest": min(r["profiled_at"] for r in runs),
            "latest": max(r["profiled_at"] for r in runs),
        },
        "warehouses": list(set(r["warehouse_type"] for r in runs)),
        "schemas": list(set(r["schema_name"] for r in runs)),
    }
    
    metadata_path = os.path.join(output_dir, "metadata.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    size_kb = os.path.getsize(metadata_path) / 1024
    print(f"  [OK] metadata.json ({size_kb:.1f} KB)")
    
    print(f"\n[OK] Export complete! All files written to {output_dir}/")


def main():
    """Generate all demo data and export to JSON."""
    print("=" * 70)
    print("Baselinr Quality Studio - Demo Data Generator")
    print("=" * 70)
    print()
    
    # Step 1: Generate runs
    runs = generate_runs(num_runs=120)
    
    # Step 2: Generate tables metadata
    tables = generate_tables_metadata(runs)
    
    # Step 3: Generate metrics
    metrics = generate_metrics(runs)
    
    # Step 4: Generate drift events
    drift_events = generate_drift_events(runs)
    
    # Step 5: Generate validation results
    validation_results = generate_validation_results(runs)
    
    # Step 6: Generate lineage
    lineage = generate_lineage_relationships()
    
    # Step 7: Generate table quality scores
    table_quality_scores = generate_table_quality_scores(tables, runs, validation_results, drift_events)
    
    # Step 8: Generate column quality scores
    column_quality_scores = generate_column_quality_scores(tables, runs, metrics)
    
    # Step 9: Validate data consistency
    if not validate_data_consistency(runs, metrics, drift_events, validation_results):
        print("\n[ERROR] Data validation failed. Please review issues above.")
        return
    
    # Step 10: Export to JSON
    export_to_json(runs, metrics, drift_events, tables, validation_results, lineage, 
                   table_quality_scores, column_quality_scores)
    
    print("\n" + "=" * 70)
    print("Demo Data Generation Complete!")
    print("=" * 70)
    print("\nGenerated:")
    print(f"  • {len(runs)} profiling runs")
    print(f"  • {len(metrics)} column metrics")
    print(f"  • {len(drift_events)} drift events")
    print(f"  • {len(tables)} unique tables")
    print(f"  • {len(validation_results)} validation results")
    print(f"  • {len(lineage['nodes'])} lineage nodes, {len(lineage['edges'])} edges")
    print("\nFiles written to: dashboard/backend/demo_data/")
    print("\nYou can now use this data for the Cloudflare Pages demo!")
    print()


if __name__ == "__main__":
    main()

