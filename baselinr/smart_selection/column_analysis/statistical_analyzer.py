"""
Statistical analyzer for column profiling data.

Analyzes existing profiling statistics to extract signals
for check recommendations.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@dataclass
class ColumnStatistics:
    """Statistical properties of a column from profiling data."""

    # Basic counts
    row_count: int = 0
    null_count: int = 0
    null_percentage: float = 0.0
    distinct_count: int = 0
    unique_ratio: float = 0.0

    # Numeric statistics
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean_value: Optional[float] = None
    stddev_value: Optional[float] = None
    median_value: Optional[float] = None

    # Timestamp statistics
    min_timestamp: Optional[datetime] = None
    max_timestamp: Optional[datetime] = None
    timestamp_freshness_hours: Optional[float] = None

    # String statistics
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    avg_length: Optional[float] = None

    # Distribution info
    histogram: Optional[List[Dict[str, Any]]] = None
    top_values: Optional[List[Dict[str, Any]]] = None
    value_distribution: Optional[Dict[str, int]] = None

    # Cardinality classification
    cardinality_type: Optional[str] = None  # 'unique', 'high', 'medium', 'low', 'binary'

    # Inferred patterns
    detected_patterns: List[str] = field(default_factory=list)

    # Stability metrics (from historical data)
    is_stable: bool = True
    volatility: Optional[float] = None

    # Data quality indicators
    has_empty_strings: bool = False
    empty_string_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "row_count": self.row_count,
            "null_count": self.null_count,
            "null_percentage": self.null_percentage,
            "distinct_count": self.distinct_count,
            "unique_ratio": self.unique_ratio,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "mean_value": self.mean_value,
            "stddev_value": self.stddev_value,
            "min_timestamp": self.min_timestamp.isoformat() if self.min_timestamp else None,
            "max_timestamp": self.max_timestamp.isoformat() if self.max_timestamp else None,
            "timestamp_freshness_hours": self.timestamp_freshness_hours,
            "min_length": self.min_length,
            "max_length": self.max_length,
            "avg_length": self.avg_length,
            "cardinality_type": self.cardinality_type,
            "detected_patterns": self.detected_patterns,
            "is_stable": self.is_stable,
        }


class StatisticalAnalyzer:
    """Analyzes profiling data to extract statistical signals."""

    # Cardinality thresholds (as percentage of row count)
    BINARY_THRESHOLD = 2  # <= 2 distinct values
    LOW_CARDINALITY_THRESHOLD = 50  # <= 50 distinct values
    MEDIUM_CARDINALITY_THRESHOLD = 0.01  # <= 1% of rows
    HIGH_CARDINALITY_THRESHOLD = 0.5  # <= 50% of rows
    # Above high = unique cardinality

    def __init__(
        self,
        storage_engine: Engine,
        results_table: str = "baselinr_results",
        runs_table: str = "baselinr_runs",
    ):
        """
        Initialize statistical analyzer.

        Args:
            storage_engine: SQLAlchemy engine for storage database
            results_table: Name of profiling results table
            runs_table: Name of profiling runs table
        """
        self.engine = storage_engine
        self.results_table = results_table
        self.runs_table = runs_table

    def analyze_column(
        self,
        table_name: str,
        column_name: str,
        schema_name: Optional[str] = None,
        lookback_days: int = 30,
    ) -> Optional[ColumnStatistics]:
        """
        Analyze a column using historical profiling data.

        Args:
            table_name: Table name
            column_name: Column name
            schema_name: Optional schema name
            lookback_days: Number of days to look back for profiling data

        Returns:
            ColumnStatistics or None if no data available
        """
        # Get most recent profiling metrics
        metrics = self._get_latest_metrics(table_name, column_name, schema_name)

        if not metrics:
            return None

        stats = ColumnStatistics()

        # Parse metrics
        self._parse_basic_metrics(stats, metrics)
        self._parse_numeric_metrics(stats, metrics)
        self._parse_string_metrics(stats, metrics)
        self._parse_distribution_metrics(stats, metrics)

        # Calculate cardinality type
        if stats.row_count > 0:
            stats.cardinality_type = self._classify_cardinality(
                stats.distinct_count, stats.row_count
            )

        # Check stability from historical data
        self._analyze_stability(stats, table_name, column_name, schema_name, lookback_days)

        # Detect patterns in values
        self._detect_patterns(stats, metrics)

        return stats

    def analyze_table_columns(
        self,
        table_name: str,
        schema_name: Optional[str] = None,
        lookback_days: int = 30,
    ) -> Dict[str, ColumnStatistics]:
        """
        Analyze all columns in a table.

        Args:
            table_name: Table name
            schema_name: Optional schema name
            lookback_days: Number of days to look back

        Returns:
            Dictionary mapping column names to statistics
        """
        results = {}

        # Get all columns with profiling data
        columns = self._get_profiled_columns(table_name, schema_name)

        for column_name in columns:
            stats = self.analyze_column(table_name, column_name, schema_name, lookback_days)
            if stats:
                results[column_name] = stats

        return results

    def _get_latest_metrics(
        self,
        table_name: str,
        column_name: str,
        schema_name: Optional[str],
    ) -> Dict[str, Any]:
        """Get the most recent profiling metrics for a column."""
        schema_filter = ""
        if schema_name:
            schema_filter = "AND r.schema_name = :schema_name"

        query = text(
            f"""
            SELECT r.metric_name, r.metric_value, r.column_type
            FROM {self.results_table} r
            INNER JOIN {self.runs_table} runs
                ON r.run_id = runs.run_id
                AND r.dataset_name = runs.dataset_name
            WHERE r.dataset_name = :table_name
            {schema_filter}
            AND r.column_name = :column_name
            AND (runs.status = 'completed' OR runs.status IS NULL)
            ORDER BY runs.profiled_at DESC
        """
        )

        params = {"table_name": table_name, "column_name": column_name}
        if schema_name:
            params["schema_name"] = schema_name

        metrics = {}
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, params)
                latest_run = None

                for row in result:
                    # Keep only first (most recent) run's metrics
                    if latest_run is None:
                        latest_run = True  # Mark we have data
                    metrics[row.metric_name] = row.metric_value

        except Exception as e:
            logger.debug(f"Could not retrieve metrics for {table_name}.{column_name}: {e}")

        return metrics

    def _get_profiled_columns(
        self,
        table_name: str,
        schema_name: Optional[str],
    ) -> List[str]:
        """Get list of columns that have profiling data."""
        schema_filter = ""
        if schema_name:
            schema_filter = "AND r.schema_name = :schema_name"

        query = text(
            f"""
            SELECT DISTINCT r.column_name
            FROM {self.results_table} r
            INNER JOIN {self.runs_table} runs
                ON r.run_id = runs.run_id
                AND r.dataset_name = runs.dataset_name
            WHERE r.dataset_name = :table_name
            {schema_filter}
            AND (runs.status = 'completed' OR runs.status IS NULL)
        """
        )

        params = {"table_name": table_name}
        if schema_name:
            params["schema_name"] = schema_name

        columns = []
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, params)
                columns = [row.column_name for row in result]
        except Exception as e:
            logger.debug(f"Could not retrieve columns for {table_name}: {e}")

        return columns

    def _parse_basic_metrics(self, stats: ColumnStatistics, metrics: Dict[str, Any]) -> None:
        """Parse basic count metrics."""
        try:
            stats.row_count = int(metrics.get("count", 0) or 0)
            stats.null_count = int(metrics.get("null_count", 0) or 0)

            null_ratio = metrics.get("null_ratio")
            if null_ratio is not None:
                stats.null_percentage = float(null_ratio) * 100
            elif stats.row_count > 0:
                stats.null_percentage = (stats.null_count / stats.row_count) * 100

            stats.distinct_count = int(metrics.get("distinct_count", 0) or 0)

            unique_ratio = metrics.get("unique_ratio")
            if unique_ratio is not None:
                stats.unique_ratio = float(unique_ratio)
            elif stats.row_count > 0:
                stats.unique_ratio = stats.distinct_count / stats.row_count

        except (ValueError, TypeError) as e:
            logger.debug(f"Error parsing basic metrics: {e}")

    def _parse_numeric_metrics(self, stats: ColumnStatistics, metrics: Dict[str, Any]) -> None:
        """Parse numeric statistics."""
        try:
            if "min" in metrics and metrics["min"] is not None:
                try:
                    stats.min_value = float(metrics["min"])
                except (ValueError, TypeError):
                    pass

            if "max" in metrics and metrics["max"] is not None:
                try:
                    stats.max_value = float(metrics["max"])
                except (ValueError, TypeError):
                    pass

            if "mean" in metrics and metrics["mean"] is not None:
                try:
                    stats.mean_value = float(metrics["mean"])
                except (ValueError, TypeError):
                    pass

            if "stddev" in metrics and metrics["stddev"] is not None:
                try:
                    stats.stddev_value = float(metrics["stddev"])
                except (ValueError, TypeError):
                    pass

        except Exception as e:
            logger.debug(f"Error parsing numeric metrics: {e}")

    def _parse_string_metrics(self, stats: ColumnStatistics, metrics: Dict[str, Any]) -> None:
        """Parse string length statistics."""
        try:
            if "min_length" in metrics and metrics["min_length"] is not None:
                stats.min_length = int(metrics["min_length"])

            if "max_length" in metrics and metrics["max_length"] is not None:
                stats.max_length = int(metrics["max_length"])

            if "avg_length" in metrics and metrics["avg_length"] is not None:
                stats.avg_length = float(metrics["avg_length"])

        except Exception as e:
            logger.debug(f"Error parsing string metrics: {e}")

    def _parse_distribution_metrics(self, stats: ColumnStatistics, metrics: Dict[str, Any]) -> None:
        """Parse distribution and histogram data."""
        try:
            # Parse histogram
            if "histogram" in metrics and metrics["histogram"]:
                hist_data = metrics["histogram"]
                if isinstance(hist_data, str):
                    stats.histogram = json.loads(hist_data)
                else:
                    stats.histogram = hist_data

            # Parse top values
            if "top_values" in metrics and metrics["top_values"]:
                top_data = metrics["top_values"]
                if isinstance(top_data, str):
                    stats.top_values = json.loads(top_data)
                else:
                    stats.top_values = top_data

                # Extract value distribution from top values
                if stats.top_values:
                    stats.value_distribution = {}
                    for item in stats.top_values:
                        if isinstance(item, dict):
                            val = str(item.get("value", ""))
                            count = item.get("count", 0)
                            stats.value_distribution[val] = count

        except Exception as e:
            logger.debug(f"Error parsing distribution metrics: {e}")

    def _classify_cardinality(self, distinct_count: int, row_count: int) -> str:
        """Classify column cardinality."""
        if distinct_count <= self.BINARY_THRESHOLD:
            return "binary"

        if distinct_count <= self.LOW_CARDINALITY_THRESHOLD:
            return "low"

        ratio = distinct_count / row_count if row_count > 0 else 0

        if ratio >= 0.99:  # 99%+ unique
            return "unique"

        if ratio > self.HIGH_CARDINALITY_THRESHOLD:
            return "high"

        if ratio > self.MEDIUM_CARDINALITY_THRESHOLD:
            return "medium"

        return "low"

    def _analyze_stability(
        self,
        stats: ColumnStatistics,
        table_name: str,
        column_name: str,
        schema_name: Optional[str],
        lookback_days: int,
    ) -> None:
        """Analyze metric stability over time."""
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

        schema_filter = ""
        if schema_name:
            schema_filter = "AND r.schema_name = :schema_name"

        # Get historical distinct counts to check stability
        query = text(
            f"""
            SELECT r.metric_value
            FROM {self.results_table} r
            INNER JOIN {self.runs_table} runs
                ON r.run_id = runs.run_id
                AND r.dataset_name = runs.dataset_name
            WHERE r.dataset_name = :table_name
            {schema_filter}
            AND r.column_name = :column_name
            AND r.metric_name = 'distinct_count'
            AND runs.profiled_at >= :cutoff_date
            AND (runs.status = 'completed' OR runs.status IS NULL)
            ORDER BY runs.profiled_at DESC
        """
        )

        params = {"table_name": table_name, "column_name": column_name, "cutoff_date": cutoff_date}
        if schema_name:
            params["schema_name"] = schema_name

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, params)
                values = []
                for row in result:
                    try:
                        values.append(float(row.metric_value))
                    except (ValueError, TypeError):
                        pass

                if len(values) >= 3:
                    # Calculate coefficient of variation
                    mean_val = sum(values) / len(values)
                    if mean_val > 0:
                        variance = sum((x - mean_val) ** 2 for x in values) / len(values)
                        stddev = variance**0.5
                        cv = stddev / mean_val

                        stats.volatility = cv
                        # Consider unstable if CV > 10%
                        stats.is_stable = cv < 0.1

        except Exception as e:
            logger.debug(f"Error analyzing stability: {e}")

    def _detect_patterns(self, stats: ColumnStatistics, metrics: Dict[str, Any]) -> None:
        """Detect patterns in column values."""
        patterns = []

        # Check for timestamp freshness
        if stats.max_timestamp:
            hours_since = (datetime.utcnow() - stats.max_timestamp).total_seconds() / 3600
            stats.timestamp_freshness_hours = hours_since
            if hours_since < 24:
                patterns.append("frequently_updated")
            elif hours_since > 168:  # 1 week
                patterns.append("stale_data")

        # Check for high null rate
        if stats.null_percentage > 50:
            patterns.append("high_nulls")
        elif stats.null_percentage > 10:
            patterns.append("moderate_nulls")
        elif stats.null_percentage == 0:
            patterns.append("no_nulls")

        # Check for potential identifier
        if stats.unique_ratio > 0.99 and stats.row_count > 100:
            patterns.append("potential_identifier")

        # Check for categorical
        if stats.cardinality_type in ("low", "binary"):
            patterns.append("categorical")

        # Check for boolean-like
        if stats.distinct_count == 2:
            patterns.append("binary_values")

        # Check for skewed distribution
        if stats.mean_value is not None and stats.stddev_value is not None:
            if stats.mean_value != 0 and stats.stddev_value / abs(stats.mean_value) > 1:
                patterns.append("high_variance")

        stats.detected_patterns = patterns
