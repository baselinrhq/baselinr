"""
Rich output utilities for Baselinr CLI.

Provides consistent formatting, colors, and status indicators across all CLI commands.
Uses modern soft color palette matching the dashboard style.
"""

import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    if TYPE_CHECKING:
        from rich.text import Text  # type: ignore

# Modern soft color palette matching dashboard style
COLORS = {
    "success": "#52b788",  # Soft mint/teal
    "warning": "#f4a261",  # Soft amber/gold
    "error": "#ff8787",  # Soft coral/rose
    "info": "#4a90e2",  # Soft blue/cyan
    "profiling": "#4a90e2",  # Soft blue/cyan
    "optimized": "#a78bfa",  # Soft magenta/purple
    "drift_check": "#f4a261",  # Soft amber/gold
    "anomaly": "#ff8787",  # Soft coral/rose
}

# Default console instance
_console: Optional["Console"] = None


def get_console() -> Optional["Console"]:
    """Get or create Rich Console instance with error handling."""
    global _console
    if _console is None:
        try:
            _console = Console()
        except (UnicodeEncodeError, OSError, ImportError):
            # Fallback to plain console if Rich fails
            _console = None
    return _console


def get_status_indicator(state: str) -> "Text":
    """
    Get colored status indicator dot matching dashboard style.

    Args:
        state: Status state ("profiling", "drift_check", "warning", "anomaly",
            "optimized", "success")

    Returns:
        Rich Text with colored dot indicator
    """
    if not RICH_AVAILABLE:
        # Fallback to plain text
        return Text("●")

    color_map = {
        "profiling": COLORS["profiling"],
        "drift_check": COLORS["drift_check"],
        "warning": COLORS["warning"],
        "anomaly": COLORS["anomaly"],
        "optimized": COLORS["optimized"],
        "success": COLORS["success"],
        "healthy": COLORS["success"],
    }

    color = color_map.get(state, COLORS["info"])
    return Text("●", style=f"bold {color}")


def get_severity_color(severity: str) -> str:
    """
    Get color for drift severity.

    Args:
        severity: Severity level ("high", "medium", "low", "none")

    Returns:
        Color hex code
    """
    severity_map = {
        "high": COLORS["error"],
        "medium": COLORS["warning"],
        "low": COLORS["warning"],
        "none": COLORS["success"],
    }
    return severity_map.get(severity.lower(), COLORS["info"])


def format_run_summary(
    duration_seconds: float,
    tables_scanned: int,
    drifts_detected: int = 0,
    warnings: int = 0,
    anomalies: int = 0,
) -> Any:
    """
    Format post-run summary with Rich Panel.

    Args:
        duration_seconds: Total duration in seconds
        tables_scanned: Number of tables scanned
        drifts_detected: Number of drifts detected
        warnings: Number of warnings
        anomalies: Number of anomalies

    Returns:
        Formatted summary string
    """
    if not RICH_AVAILABLE:
        # Fallback to plain text
        duration_str = (
            f"{duration_seconds:.1f}s" if duration_seconds < 60 else f"{duration_seconds / 60:.1f}m"
        )
        parts = [f"{tables_scanned} tables scanned"]
        if drifts_detected > 0:
            parts.append(f"{drifts_detected} drifts detected")
        if warnings > 0:
            parts.append(f"{warnings} warnings")
        if anomalies > 0:
            parts.append(f"{anomalies} anomalies")
        return f"Profiling completed in {duration_str}\n\n" + " • ".join(parts)

    console = get_console()
    if not console:
        return format_run_summary(
            duration_seconds, tables_scanned, drifts_detected, warnings, anomalies
        )

    # Format duration
    if duration_seconds < 60:
        duration_str = f"{duration_seconds:.1f}s"
    elif duration_seconds < 3600:
        duration_str = f"{duration_seconds / 60:.1f}m"
    else:
        duration_str = f"{duration_seconds / 3600:.1f}h"

    # Build summary text with colored indicators
    summary_parts = []
    success_color = COLORS["success"]
    summary_parts.append(
        f"[bold {success_color}]Profiling completed in {duration_str}" f"[/bold {success_color}]"
    )
    summary_parts.append("")

    stats = []
    stats.append(f"[cyan]{tables_scanned}[/cyan] tables scanned")
    if drifts_detected > 0:
        stats.append(
            f"[{COLORS['warning']}]{drifts_detected} drifts detected[/{COLORS['warning']}]"
        )
    if warnings > 0:
        stats.append(f"[{COLORS['warning']}]{warnings} warnings[/{COLORS['warning']}]")
    if anomalies > 0:
        stats.append(f"[{COLORS['error']}]{anomalies} anomalies[/{COLORS['error']}]")

    summary_parts.append(" • ".join(stats))

    summary_text = "\n".join(summary_parts)

    # Create panel with soft border
    panel = Panel.fit(
        summary_text,
        border_style=COLORS["info"],
        title="[bold]Summary[/bold]",
    )

    # Return the panel directly instead of capturing - let safe_print handle it
    # This avoids ANSI code issues
    return panel


def render_histogram(
    baseline: List[Dict[str, Any]], current: List[Dict[str, Any]], bins: int = 10
) -> str:
    """
    Render inline histogram comparison for distribution changes.

    Args:
        baseline: Baseline histogram data (list of {bin, count} dicts)
        current: Current histogram data (list of {bin, count} dicts)
        bins: Number of bins

    Returns:
        Formatted histogram string
    """
    if not RICH_AVAILABLE or not baseline or not current:
        return "[Histogram data not available]"

    console = get_console()
    if not console:
        return "[Histogram data not available]"

    # Normalize histogram data
    def normalize_hist(hist_data: List[Dict[str, Any]]) -> List[float]:
        """Normalize histogram to 0-1 range for display."""
        if not hist_data:
            return []
        counts = [item.get("count", 0) for item in hist_data if isinstance(item, dict)]
        if not counts:
            return []
        max_count = max(counts) if counts else 1
        return [c / max_count if max_count > 0 else 0 for c in counts]

    baseline_norm = normalize_hist(baseline)
    current_norm = normalize_hist(current)

    # Create simple bar chart representation
    max_bars = 20  # Maximum width for histogram bars
    lines = []
    lines.append("[bold]Distribution Comparison[/bold]")
    lines.append("")

    # Find max length for alignment
    max_len = max(len(baseline_norm), len(current_norm))
    for i in range(max_len):
        baseline_val = baseline_norm[i] if i < len(baseline_norm) else 0
        current_val = current_norm[i] if i < len(current_norm) else 0

        baseline_bars = int(baseline_val * max_bars)
        current_bars = int(current_val * max_bars)

        baseline_bar = "█" * baseline_bars
        current_bar = "█" * current_bars

        info_color = COLORS["info"]
        warning_color = COLORS["warning"]
        lines.append(
            f"Bin {i+1:2d}: [dim]Baseline:[/dim] [{info_color}]{baseline_bar}"
            f"[/{info_color}] [dim]Current:[/dim] [{warning_color}]{current_bar}"
            f"[/{warning_color}]"
        )

    return "\n".join(lines)


def create_progress_bar(total: int, description: str = "Processing") -> Optional["Progress"]:
    """
    Create Rich progress bar for long operations.

    Args:
        total: Total number of items to process
        description: Description text for progress bar

    Returns:
        Rich Progress instance or None if Rich unavailable
    """
    if not RICH_AVAILABLE:
        return None

    console = get_console()
    if not console:
        return None

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    )

    return progress


def format_drift_severity(severity: str) -> "Text":
    """
    Format drift severity with appropriate color.

    Args:
        severity: Severity level ("high", "medium", "low", "none")

    Returns:
        Rich Text with colored severity
    """
    if not RICH_AVAILABLE:
        return Text(severity.upper())

    color = get_severity_color(severity)
    return Text(severity.upper(), style=f"bold {color}")


def extract_histogram_data(metric_data: Any) -> Optional[List[Dict[str, Any]]]:
    """
    Extract histogram data from metric results.

    Args:
        metric_data: Metric data (could be dict, string JSON, or None)

    Returns:
        List of histogram bins with {bin, count} or None if not available
    """
    if not metric_data:
        return None

    try:
        # If it's a string, try to parse as JSON
        if isinstance(metric_data, str):
            parsed = json.loads(metric_data)
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict) and "histogram" in parsed:
                return extract_histogram_data(parsed["histogram"])

        # If it's a dict, look for histogram key
        if isinstance(metric_data, dict):
            if "histogram" in metric_data:
                return extract_histogram_data(metric_data["histogram"])
            # If the dict itself looks like histogram data
            if "bin" in metric_data or "count" in metric_data:
                return [metric_data]

        # If it's a list, assume it's histogram data
        if isinstance(metric_data, list):
            return metric_data

    except (json.JSONDecodeError, TypeError, AttributeError):
        pass

    return None


def safe_print(*args, **kwargs) -> None:
    """
    Safely print using Rich Console with fallback to plain print.

    Handles UnicodeEncodeError and other terminal issues gracefully.
    """
    console = get_console()
    if console and RICH_AVAILABLE:
        try:
            console.print(*args, **kwargs)
        except (UnicodeEncodeError, OSError):
            # Fallback to plain print with Unicode handling
            try:
                import sys

                # Try to print with UTF-8 encoding
                if hasattr(sys.stdout, "reconfigure"):
                    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
                print(*args, **kwargs)
            except (UnicodeEncodeError, OSError):
                # Last resort: remove emojis and print
                import re

                cleaned_args = [
                    (
                        re.sub(r"[\U0001F300-\U0001F9FF\U00002600-\U000027BF]", "", str(arg))
                        if isinstance(arg, str)
                        else arg
                    )
                    for arg in args
                ]
                print(*cleaned_args, **kwargs)
    else:
        try:
            import sys

            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            print(*args, **kwargs)
        except (UnicodeEncodeError, OSError):
            # Last resort: remove emojis and print
            import re

            cleaned_args = [
                (
                    re.sub(r"[\U0001F300-\U0001F9FF\U00002600-\U000027BF]", "", str(arg))
                    if isinstance(arg, str)
                    else arg
                )
                for arg in args
            ]
            print(*cleaned_args, **kwargs)
