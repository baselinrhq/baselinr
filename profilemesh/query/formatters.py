"""Output formatters for query results."""

import json
from typing import Any, Dict, List


def format_runs(runs: List[Any], format: str = "table") -> str:
    """
    Format run query results.

    Args:
        runs: List of RunSummary objects
        format: Output format (table, json, csv)

    Returns:
        Formatted string
    """
    if format == "json":
        return json.dumps([run.to_dict() for run in runs], indent=2, default=str)

    elif format == "csv":
        if not runs:
            return (
                "run_id,dataset_name,schema_name,profiled_at,environment,status,"
                "row_count,column_count"
            )

        lines = [
            "run_id,dataset_name,schema_name,profiled_at,environment,status,"
            "row_count,column_count"
        ]
        for run in runs:
            profiled_at_str = run.profiled_at.isoformat() if run.profiled_at else ""
            lines.append(
                f"{run.run_id},{run.dataset_name},{run.schema_name or ''},"
                f"{profiled_at_str},"
                f"{run.environment or ''},{run.status or ''},"
                f"{run.row_count or ''},{run.column_count or ''}"
            )
        return "\n".join(lines)

    else:  # table format
        if not runs:
            return "No runs found."

        # Use tabulate if available, otherwise simple formatting
        try:
            from tabulate import tabulate  # type: ignore[import-untyped]

            headers = ["Run ID", "Table", "Schema", "Profiled At", "Status", "Rows", "Cols"]
            rows = []
            for run in runs:
                rows.append(
                    [
                        run.run_id[:8] + "...",
                        run.dataset_name,
                        run.schema_name or "-",
                        run.profiled_at.strftime("%Y-%m-%d %H:%M") if run.profiled_at else "-",
                        run.status or "-",
                        f"{run.row_count:,}" if run.row_count else "-",
                        run.column_count or "-",
                    ]
                )

            return tabulate(rows, headers=headers, tablefmt="grid")  # type: ignore[no-any-return]

        except ImportError:
            # Fallback to simple formatting
            lines = ["RUN RESULTS", "=" * 80]
            for run in runs:
                lines.append(f"\nRun ID: {run.run_id}")
                lines.append(f"  Table: {run.dataset_name}")
                lines.append(f"  Schema: {run.schema_name or 'N/A'}")
                lines.append(f"  Profiled: {run.profiled_at}")
                lines.append(f"  Status: {run.status}")
                lines.append(f"  Rows: {run.row_count:,}" if run.row_count else "  Rows: N/A")
                lines.append(f"  Columns: {run.column_count}")
            return "\n".join(lines)


def format_drift(events: List[Any], format: str = "table") -> str:
    """
    Format drift event query results.

    Args:
        events: List of DriftEvent objects
        format: Output format (table, json, csv)

    Returns:
        Formatted string
    """
    if format == "json":
        return json.dumps([event.to_dict() for event in events], indent=2, default=str)

    elif format == "csv":
        if not events:
            return (
                "event_id,event_type,table_name,column_name,metric_name,"
                "baseline_value,current_value,change_percent,severity,timestamp"
            )

        lines = [
            "event_id,event_type,table_name,column_name,metric_name,"
            "baseline_value,current_value,change_percent,severity,timestamp"
        ]
        for event in events:
            lines.append(
                f"{event.event_id},{event.event_type},{event.table_name or ''},"
                f"{event.column_name or ''},{event.metric_name or ''},"
                f"{event.baseline_value or ''},{event.current_value or ''},"
                f"{event.change_percent or ''},{event.drift_severity or ''},"
                f"{event.timestamp.isoformat() if event.timestamp else ''}"
            )
        return "\n".join(lines)

    else:  # table format
        if not events:
            return "No drift events found."

        try:
            from tabulate import tabulate

            headers = [
                "Table",
                "Column",
                "Metric",
                "Baseline",
                "Current",
                "Change %",
                "Severity",
                "Time",
            ]
            rows = []
            for event in events:
                rows.append(
                    [
                        event.table_name or "-",
                        event.column_name or "-",
                        event.metric_name or "-",
                        f"{event.baseline_value:.2f}" if event.baseline_value is not None else "-",
                        f"{event.current_value:.2f}" if event.current_value is not None else "-",
                        (
                            f"{event.change_percent:+.1f}%"
                            if event.change_percent is not None
                            else "-"
                        ),
                        event.drift_severity or "-",
                        event.timestamp.strftime("%Y-%m-%d %H:%M") if event.timestamp else "-",
                    ]
                )

            return tabulate(rows, headers=headers, tablefmt="grid")  # type: ignore[no-any-return]

        except ImportError:
            lines = ["DRIFT EVENTS", "=" * 80]
            for event in events:
                lines.append(
                    f"\n[{event.drift_severity.upper() if event.drift_severity else 'N/A'}] "
                    f"{event.table_name}.{event.column_name}"
                )
                lines.append(f"  Metric: {event.metric_name}")
                lines.append(f"  Baseline: {event.baseline_value}")
                lines.append(f"  Current: {event.current_value}")
                if event.change_percent is not None:
                    lines.append(f"  Change: {event.change_percent:+.2f}%")
                else:
                    lines.append("  Change: N/A")
                lines.append(f"  Time: {event.timestamp}")
            return "\n".join(lines)


def format_table_history(data: Dict[str, Any], format: str = "table") -> str:
    """
    Format table history results.

    Args:
        data: Dictionary with table history data
        format: Output format (table, json, csv)

    Returns:
        Formatted string
    """
    if format == "json":
        return json.dumps(data, indent=2, default=str)

    elif format == "csv":
        if not data.get("runs"):
            return "run_id,profiled_at,status,row_count,column_count"

        lines = ["run_id,profiled_at,status,row_count,column_count"]
        for run in data["runs"]:
            lines.append(
                f"{run['run_id']},{run['profiled_at']},{run['status']},"
                f"{run['row_count'] or ''},{run['column_count'] or ''}"
            )
        return "\n".join(lines)

    else:  # table format
        lines = [
            f"TABLE HISTORY: {data['table_name']}",
            "=" * 80,
            f"Schema: {data.get('schema_name') or 'N/A'}",
            f"Total Runs: {data['run_count']}",
            "",
        ]

        if not data.get("runs"):
            lines.append("No run history found.")
            return "\n".join(lines)

        try:
            from tabulate import tabulate

            headers = ["Run ID", "Profiled At", "Status", "Rows", "Columns"]
            rows = []
            for run in data["runs"]:
                rows.append(
                    [
                        run["run_id"][:8] + "...",
                        run["profiled_at"][:16] if run["profiled_at"] else "-",
                        run["status"] or "-",
                        f"{run['row_count']:,}" if run["row_count"] else "-",
                        run["column_count"] or "-",
                    ]
                )

            lines.append(tabulate(rows, headers=headers, tablefmt="grid"))
            return "\n".join(lines)

        except ImportError:
            for run in data["runs"]:
                lines.append(f"\nRun: {run['run_id']}")
                lines.append(f"  Profiled: {run['profiled_at']}")
                lines.append(f"  Status: {run['status']}")
                if run["row_count"]:
                    lines.append(f"  Rows: {run['row_count']:,}")
                else:
                    lines.append("  Rows: N/A")
            return "\n".join(lines)
