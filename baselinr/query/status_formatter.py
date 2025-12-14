"""Status formatter for Baselinr CLI status command."""

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    if TYPE_CHECKING:
        from rich.text import Text  # type: ignore


def _infer_drift_type(metric_name: Optional[str]) -> str:
    """Infer drift type from metric name."""
    if not metric_name:
        return "unknown"
    metric_lower = metric_name.lower()
    if "schema" in metric_lower or "column" in metric_lower:
        return "schema"
    elif "count" in metric_lower or "row" in metric_lower:
        return "volume"
    elif "mean" in metric_lower or "stddev" in metric_lower or "distribution" in metric_lower:
        return "distribution"
    elif "profiled_at" in metric_lower or "freshness" in metric_lower:
        return "freshness"
    return "unknown"


def _get_status_indicator(
    has_drift: bool, has_anomalies: bool, severity: Optional[str] = None
) -> str:
    """Get status indicator text based on run health."""
    if has_drift and severity == "high":
        return "[ERROR]"
    elif has_drift or has_anomalies:
        return "[WARNING]"
    else:
        return "[OK]"


def _get_status_indicator_rich(
    has_drift: bool, has_anomalies: bool, severity: Optional[str] = None
) -> "Text":
    """Get modern, sleek status indicator using Rich colors with softer tones."""
    if has_drift and severity == "high":
        # Soft coral/rose for critical issues - modern and less harsh than bright red
        return Text("●", style="bold #ff8787")
    elif has_drift or has_anomalies:
        # Soft amber/gold for warnings - warm and inviting
        return Text("●", style="bold #f4a261")
    else:
        # Soft mint/teal for healthy - fresh and calming
        return Text("●", style="bold #52b788")


def _format_score_badge(score: float, status: str) -> "Text":
    """
    Format score as a small badge for table displays.

    Args:
        score: Quality score (0-100)
        status: Status string ("healthy", "warning", "critical")

    Returns:
        Rich Text with formatted score badge
    """
    if not RICH_AVAILABLE:
        return Text(f"{score:.1f}")

    # Color mapping matching cli_output.py
    color_map = {
        "healthy": "#52b788",  # Soft mint/teal
        "warning": "#f4a261",  # Soft amber/gold
        "critical": "#ff8787",  # Soft coral/rose
    }

    color = color_map.get(status.lower(), "#4a90e2")  # Default to info color
    return Text(f"{score:.1f}", style=f"bold {color}")


def format_status(
    runs_data: List[Dict[str, Any]],
    drift_summary: List[Dict[str, Any]],
    format: str = "rich",
    drift_only: bool = False,
) -> str:
    """
    Format status output for CLI.

    Args:
        runs_data: List of run dictionaries with enriched data
        drift_summary: List of drift summary dictionaries
        format: Output format ("rich", "json", "text")
        drift_only: If True, only show drift summary

    Returns:
        Formatted string output
    """
    if format == "json":
        return _format_json(runs_data, drift_summary, drift_only)

    if format == "text" or not RICH_AVAILABLE:
        return _format_text(runs_data, drift_summary, drift_only)

    # Rich format
    return _format_rich(runs_data, drift_summary, drift_only)


def _format_json(
    runs_data: List[Dict[str, Any]],
    drift_summary: List[Dict[str, Any]],
    drift_only: bool,
) -> str:
    """Format status as JSON."""
    output = {
        "timestamp": datetime.utcnow().isoformat(),
        "drift_summary": drift_summary,
    }
    if not drift_only:
        output["runs"] = runs_data
    return json.dumps(output, indent=2, default=str)


def _format_text(
    runs_data: List[Dict[str, Any]],
    drift_summary: List[Dict[str, Any]],
    drift_only: bool,
) -> str:
    """Format status as plain text (fallback)."""
    lines = []
    lines.append("=" * 80)
    lines.append("BASELINR STATUS")
    lines.append("=" * 80)
    lines.append(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    if not drift_only:
        lines.append("RECENT PROFILING RUNS")
        lines.append("-" * 80)
        if not runs_data:
            lines.append("No runs found.")
        else:
            for run in runs_data:
                lines.append(f"\nTable: {run.get('table_name', 'N/A')}")
                lines.append(f"  Schema: {run.get('schema_name', 'N/A')}")
                lines.append(f"  Run ID: {run.get('run_id', 'N/A')[:8]}...")
                lines.append(f"  Profiled: {run.get('profiled_at', 'N/A')}")
                lines.append(f"  Duration: {run.get('duration', 'N/A')}")
                lines.append(f"  Rows: {run.get('rows_scanned', 'N/A')}")
                lines.append(f"  Metrics: {run.get('metrics_count', 0)}")
                lines.append(f"  Anomalies: {run.get('anomalies_count', 0)}")
                lines.append(f"  Status: {run.get('status_indicator', '🟢')}")
        lines.append("")

    lines.append("DRIFT SUMMARY")
    lines.append("-" * 80)
    if not drift_summary:
        lines.append("No active drift detected.")
    else:
        for drift in drift_summary:
            lines.append(f"\nTable: {drift.get('table_name', 'N/A')}")
            lines.append(f"  Severity: {drift.get('severity', 'N/A')}")
            lines.append(f"  Type: {drift.get('drift_type', 'N/A')}")
            lines.append(f"  Started: {drift.get('started_at', 'N/A')}")
            lines.append(f"  Events: {drift.get('event_count', 0)}")

    lines.append("")
    lines.append("=" * 80)
    return "\n".join(lines)


def _format_rich(
    runs_data: List[Dict[str, Any]],
    drift_summary: List[Dict[str, Any]],
    drift_only: bool,
) -> str:
    """Format status using Rich library."""
    console = Console()
    output_parts: List[Any] = []

    # Header
    header = Panel.fit(
        f"[bold]Baselinr Status[/bold]\n"
        f"[dim]Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}[/dim]",
        border_style="blue",
    )
    output_parts.append(header)

    # Recent Runs Section
    if not drift_only:
        runs_table = Table(
            title="Recent Profiling Runs", show_header=True, header_style="bold magenta"
        )
        runs_table.add_column("Table", style="cyan", no_wrap=True)
        runs_table.add_column("Schema", style="dim")
        runs_table.add_column("Duration", justify="right")
        runs_table.add_column("Rows", justify="right")
        runs_table.add_column("Metrics", justify="right")
        runs_table.add_column("Anomalies", justify="right")
        runs_table.add_column("Score", justify="right")
        runs_table.add_column("Status", justify="center")

        if not runs_data:
            runs_table.add_row("[dim]No runs found[/dim]", "", "", "", "", "", "", "")
        else:
            for run in runs_data:
                table_name = run.get("table_name", "N/A")
                schema_name = run.get("schema_name") or "[dim]-[/dim]"
                duration = run.get("duration", "N/A")
                rows = (
                    f"{run.get('rows_scanned', 0):,}"
                    if run.get("rows_scanned")
                    else "[dim]N/A[/dim]"
                )
                metrics = str(run.get("metrics_count", 0))
                anomalies = str(run.get("anomalies_count", 0))

                # Format quality score badge
                quality_score = run.get("quality_score")
                quality_status = run.get("quality_status")
                if quality_score is not None:
                    score_badge = _format_score_badge(quality_score, quality_status or "healthy")
                else:
                    score_badge = Text("[dim]N/A[/dim]")

                # Use Rich Text for modern status indicator with softer colors
                has_drift = run.get("has_drift", False)
                has_anomalies = run.get("anomalies_count", 0) > 0
                severity = run.get("drift_severity")
                status = _get_status_indicator_rich(has_drift, has_anomalies, severity)

                runs_table.add_row(
                    table_name, schema_name, duration, rows, metrics, anomalies, score_badge, status
                )

        output_parts.append(runs_table)

    # Drift Summary Section
    drift_table = Table(title="Active Drift Summary", show_header=True, header_style="bold yellow")
    drift_table.add_column("Table", style="cyan", no_wrap=True)
    drift_table.add_column("Severity", justify="center")
    drift_table.add_column("Type", style="dim")
    drift_table.add_column("Started", style="dim")
    drift_table.add_column("Events", justify="right")

    if not drift_summary:
        drift_table.add_row("[dim]No active drift detected[/dim]", "", "", "", "")
    else:
        for drift in drift_summary:
            table_name = drift.get("table_name", "N/A")
            severity = drift.get("severity", "unknown")
            drift_type = drift.get("drift_type", "unknown")
            started_at = drift.get("started_at", "N/A")
            event_count = str(drift.get("event_count", 0))

            # Color code severity
            if severity == "high":
                severity_text = Text(severity.upper(), style="bold red")
            elif severity == "medium":
                severity_text = Text(severity.upper(), style="bold yellow")
            elif severity == "low":
                severity_text = Text(severity.upper(), style="yellow")
            else:
                severity_text = Text(severity, style="dim")

            # Format started_at timestamp
            if started_at and started_at != "N/A":
                try:
                    dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    started_at = dt.strftime("%Y-%m-%d %H:%M")
                except (ValueError, AttributeError):
                    pass

            drift_table.add_row(table_name, severity_text, drift_type, started_at, event_count)

    output_parts.append(drift_table)

    # Combine all parts
    with console.capture() as capture:
        for part in output_parts:
            console.print(part)
            console.print()  # Add spacing

    result = capture.get()
    return str(result) if result is not None else ""
