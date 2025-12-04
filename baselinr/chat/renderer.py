"""
Response rendering for Baselinr chat interface.

Formats LLM responses and tool outputs for CLI display using Rich.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.theme import Theme

    RICH_AVAILABLE = True

    # Custom theme for Baselinr
    BASELINR_THEME = Theme(
        {
            "info": "cyan",
            "warning": "yellow",
            "error": "red bold",
            "success": "green",
            "metric": "blue",
            "table_name": "magenta bold",
            "column_name": "cyan",
            "value": "white",
            "user": "green bold",
            "assistant": "cyan bold",
            "tool": "yellow",
        }
    )
except ImportError:
    RICH_AVAILABLE = False
    # Type stubs for when rich is not available
    Console = None  # type: ignore[assignment,misc]
    Markdown = None  # type: ignore[assignment,misc]
    Panel = None  # type: ignore[assignment,misc]
    Table = None  # type: ignore[assignment,misc]
    Text = None  # type: ignore[assignment,misc]
    Theme = None  # type: ignore[assignment,misc]
    BASELINR_THEME = None  # type: ignore[assignment]


@dataclass
class ChatRenderer:
    """Renders chat responses for CLI display."""

    console: Optional[Any] = None
    show_tool_calls: bool = False  # Show raw tool call info
    verbose: bool = False

    def __post_init__(self):
        if RICH_AVAILABLE and self.console is None and BASELINR_THEME is not None:
            self.console = Console(theme=BASELINR_THEME)
        elif RICH_AVAILABLE and self.console is None:
            self.console = Console()

    def render_welcome(self) -> None:
        """Render welcome message."""
        if not RICH_AVAILABLE or not self.console:
            print("\n=== Baselinr Chat ===")
            print("Ask me anything about your data quality monitoring!")
            print("\nCommands: /help, /clear, /history, /stats, /exit\n")
            return

        welcome_text = """[bold cyan]Baselinr Chat[/bold cyan]
Ask me anything about your data quality monitoring!

[bold]Commands:[/bold]
  [cyan]/help[/cyan]    - Show help
  [cyan]/clear[/cyan]   - Clear conversation history
  [cyan]/history[/cyan] - Show conversation history
  [cyan]/stats[/cyan]   - Show session statistics
  [cyan]/exit[/cyan]    - Exit chat (or Ctrl+D)

[dim]Examples:[/dim]
  • "What tables have been profiled recently?"
  • "Show me drift events in the orders table"
  • "Are there any anomalies I should investigate?"
  • "Compare the last two runs of customers"
"""

        self.console.print(Panel(welcome_text, title="Welcome", border_style="cyan"))

    def render_user_message(self, message: str) -> None:
        """Render user message."""
        if not RICH_AVAILABLE or not self.console:
            print(f"\n🧑 You: {message}")
            return

        self.console.print()
        self.console.print("🧑 [user]You:[/user]", message)

    def render_assistant_message(self, message: str) -> None:
        """Render assistant message."""
        if not RICH_AVAILABLE or not self.console:
            print(f"\n🤖 Baselinr: {message}")
            return

        self.console.print()
        self.console.print("🤖 [assistant]Baselinr:[/assistant]")
        self.console.print(Markdown(message))

    def render_thinking(self) -> Any:
        """Render thinking indicator."""
        if not RICH_AVAILABLE or not self.console:
            print("Thinking...", end="", flush=True)
            return None

        return self.console.status("[bold yellow]Thinking...", spinner="dots")

    def render_tool_call(self, tool_name: str, args: Dict[str, Any]) -> None:
        """Render tool call information."""
        if not self.show_tool_calls:
            return

        if not RICH_AVAILABLE or not self.console:
            print(f"  [Tool: {tool_name}]")
            return

        self.console.print(f"  [tool]→ Calling {tool_name}[/tool]", style="dim")

    def render_tool_result(self, tool_name: str, result: Any) -> None:
        """Render tool result (for verbose mode)."""
        if not self.verbose:
            return

        if not RICH_AVAILABLE or not self.console:
            print(f"  [Result from {tool_name}]")
            return

        # Parse result
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                pass

        # Create summary
        if isinstance(result, list):
            summary = f"Returned {len(result)} items"
        elif isinstance(result, dict):
            if "error" in result:
                summary = f"Error: {result['error']}"
            else:
                summary = f"Returned {len(result)} fields"
        else:
            summary = str(result)[:100]

        self.console.print(f"  [dim]← {summary}[/dim]")

    def render_error(self, error: str) -> None:
        """Render error message."""
        if not RICH_AVAILABLE or not self.console:
            print(f"\n❌ Error: {error}")
            return

        self.console.print(f"\n[error]❌ Error:[/error] {error}")

    def render_info(self, message: str) -> None:
        """Render info message."""
        if not RICH_AVAILABLE or not self.console:
            print(f"ℹ️ {message}")
            return

        self.console.print(f"[info]ℹ️ {message}[/info]")

    def render_success(self, message: str) -> None:
        """Render success message."""
        if not RICH_AVAILABLE or not self.console:
            print(f"✓ {message}")
            return

        self.console.print(f"[success]✓[/success] {message}")

    def render_warning(self, message: str) -> None:
        """Render warning message."""
        if not RICH_AVAILABLE or not self.console:
            print(f"⚠️ {message}")
            return

        self.console.print(f"[warning]⚠️ {message}[/warning]")

    def render_history(self, messages: List[Any]) -> None:
        """Render conversation history."""
        if not messages:
            self.render_info("No conversation history")
            return

        if not RICH_AVAILABLE or not self.console:
            print("\n=== Conversation History ===")
            for msg in messages:
                role = "You" if msg.role == "user" else "Baselinr"
                print(f"{role}: {msg.content[:100]}...")
            return

        self.console.print()
        self.console.print("[bold]Conversation History:[/bold]")
        self.console.print()

        for msg in messages:
            if msg.role == "user":
                self.console.print(f"🧑 [user]You:[/user] {msg.content}")
            elif msg.role == "assistant":
                content = msg.content[:200]
                if len(msg.content) > 200:
                    content += "..."
                self.console.print(f"🤖 [assistant]Baselinr:[/assistant] {content}")
            self.console.print()

    def render_stats(self, stats: Dict[str, Any]) -> None:
        """Render session statistics."""
        if not RICH_AVAILABLE or not self.console:
            print("\n=== Session Statistics ===")
            for key, value in stats.items():
                print(f"  {key}: {value}")
            return

        table = Table(title="Session Statistics", show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Session ID", stats.get("session_id", "N/A"))
        table.add_row("Duration", f"{stats.get('duration_seconds', 0)}s")
        table.add_row("Messages", str(stats.get("total_messages", 0)))
        table.add_row("Tool Calls", str(stats.get("total_tool_calls", 0)))
        table.add_row("Tokens Used", f"{stats.get('total_tokens_used', 0):,}")

        # Estimate cost
        tokens = stats.get("total_tokens_used", 0)
        if tokens > 0:
            estimated_cost = (tokens / 1_000_000) * 0.15  # GPT-4o-mini pricing
            table.add_row("Est. Cost", f"${estimated_cost:.4f}")

        self.console.print()
        self.console.print(table)

    def render_help(self) -> None:
        """Render help message."""
        help_text = """
[bold]Available Commands:[/bold]

  [cyan]/help[/cyan]     - Show this help message
  [cyan]/clear[/cyan]    - Clear conversation history
  [cyan]/history[/cyan]  - Show conversation history
  [cyan]/stats[/cyan]    - Show session statistics
  [cyan]/tools[/cyan]    - List available tools
  [cyan]/verbose[/cyan]  - Toggle verbose mode
  [cyan]/exit[/cyan]     - Exit chat

[bold]Example Questions:[/bold]

  [dim]Profiling:[/dim]
  • "What tables have been profiled recently?"
  • "Show me the profile for the orders table"
  • "How many rows are in the customers table?"

  [dim]Drift & Anomalies:[/dim]
  • "Are there any high severity drift events?"
  • "What anomalies were detected this week?"
  • "Tell me about drift in the email column"

  [dim]Trends & History:[/dim]
  • "Show me the trend for null rate in customer_email"
  • "Compare the last two runs for orders"
  • "How has distinct count changed over time?"

  [dim]Discovery:[/dim]
  • "Search for tables with 'order' in the name"
  • "What tables are in the analytics schema?"
  • "Show me the lineage for transactions"
"""
        if not RICH_AVAILABLE or not self.console:
            print(help_text.replace("[bold]", "").replace("[/bold]", ""))
            print(help_text.replace("[cyan]", "").replace("[/cyan]", ""))
            print(help_text.replace("[dim]", "").replace("[/dim]", ""))
            return

        self.console.print(Panel(help_text, title="Help", border_style="cyan"))

    def render_tools(self, tools: List[Any]) -> None:
        """Render available tools."""
        if not tools:
            self.render_info("No tools available")
            return

        if not RICH_AVAILABLE or not self.console:
            print("\n=== Available Tools ===")
            for tool in tools:
                print(f"  {tool.name}: {tool.description[:80]}...")
            return

        table = Table(title="Available Tools", show_lines=True)
        table.add_column("Tool", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Category", style="dim")

        for tool in tools:
            description = tool.description[:100]
            if len(tool.description) > 100:
                description += "..."
            table.add_row(tool.name, description, tool.category)

        self.console.print()
        self.console.print(table)

    def render_goodbye(self) -> None:
        """Render goodbye message."""
        if not RICH_AVAILABLE or not self.console:
            print("\n👋 Goodbye!")
            return

        self.console.print("\n👋 [cyan]Goodbye![/cyan]")


def format_drift_summary(events: List[Dict[str, Any]]) -> str:
    """Format drift events summary as markdown."""
    if not events:
        return "No drift events found."

    lines = ["**Drift Events Summary:**\n"]

    # Group by severity
    high = [e for e in events if e.get("drift_severity", "").lower() == "high"]
    medium = [e for e in events if e.get("drift_severity", "").lower() == "medium"]
    low = [e for e in events if e.get("drift_severity", "").lower() == "low"]

    if high:
        lines.append(f"🔴 **High Severity:** {len(high)} events")
        for e in high[:3]:
            lines.append(
                f"  - {e.get('table_name')}.{e.get('column_name')}: {e.get('metric_name')}"
            )

    if medium:
        lines.append(f"🟡 **Medium Severity:** {len(medium)} events")

    if low:
        lines.append(f"🟢 **Low Severity:** {len(low)} events")

    return "\n".join(lines)


def format_table_profile(profile: Dict[str, Any]) -> str:
    """Format table profile as markdown."""
    if "error" in profile:
        return f"Error: {profile['error']}"

    lines = [
        f"**Table:** {profile.get('dataset_name', 'Unknown')}",
        f"**Schema:** {profile.get('schema_name', 'N/A')}",
        f"**Last Profiled:** {profile.get('profiled_at', 'N/A')}",
        (
            f"**Row Count:** {profile.get('row_count', 'N/A'):,}"
            if profile.get("row_count")
            else "**Row Count:** N/A"
        ),
        f"**Columns:** {profile.get('column_count', 'N/A')}",
        "",
        "**Column Summary:**",
    ]

    columns = profile.get("columns", [])
    for col in columns[:10]:  # Limit to 10 columns
        metrics = col.get("metrics", {})
        null_ratio = metrics.get("null_ratio", "N/A")
        if isinstance(null_ratio, (int, float)):
            null_ratio = f"{null_ratio:.1%}"

        lines.append(
            f"- **{col.get('column_name')}** ({col.get('column_type', 'unknown')}): "
            f"null_ratio={null_ratio}"
        )

    if len(columns) > 10:
        lines.append(f"... and {len(columns) - 10} more columns")

    return "\n".join(lines)


def format_trend_summary(trend_data: Dict[str, Any]) -> str:
    """Format trend data as markdown."""
    if "error" in trend_data:
        return f"Error: {trend_data['error']}"

    summary = trend_data.get("summary", {})
    history = trend_data.get("history", [])

    lines = [
        "**Trend Summary:**",
        f"- Data points: {summary.get('count', len(history))}",
    ]

    if "min" in summary:
        lines.append(f"- Min: {summary['min']:.4f}")
    if "max" in summary:
        lines.append(f"- Max: {summary['max']:.4f}")
    if "mean" in summary:
        lines.append(f"- Mean: {summary['mean']:.4f}")
    if "trend" in summary:
        trend_emoji = (
            "📈"
            if summary["trend"] == "increasing"
            else "📉" if summary["trend"] == "decreasing" else "➡️"
        )
        lines.append(f"- Trend: {trend_emoji} {summary['trend']}")
        if "trend_percent" in summary:
            lines.append(f"- Change: {summary['trend_percent']:.1f}%")

    return "\n".join(lines)
