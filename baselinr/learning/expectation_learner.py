"""
Expectation Learner for Baselinr.

Learns expected metric ranges from historical profiling data.
Computes statistical expectations, control limits, and distributions.
"""

import json
import logging
import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from ..config.schema import StorageConfig

logger = logging.getLogger(__name__)


@dataclass
class LearnedExpectation:
    """
    Represents learned expectations for a metric.

    Stores statistical properties, control limits, distributions,
    and categorical frequencies learned from historical profiling data.
    """

    table_name: str
    schema_name: Optional[str]
    column_name: str
    metric_name: str
    column_type: Optional[str] = None

    # Expected statistics
    expected_mean: Optional[float] = None
    expected_variance: Optional[float] = None
    expected_stddev: Optional[float] = None
    expected_min: Optional[float] = None
    expected_max: Optional[float] = None

    # Control limits
    lower_control_limit: Optional[float] = None
    upper_control_limit: Optional[float] = None
    lcl_method: str = "shewhart"
    ucl_method: str = "shewhart"

    # EWMA
    ewma_value: Optional[float] = None
    ewma_lambda: float = 0.2

    # Distribution
    distribution_type: Optional[str] = None
    distribution_params: Optional[Dict[str, Any]] = None

    # Categorical
    category_distribution: Optional[Dict[str, float]] = None

    # Metadata
    sample_size: int = 0
    learning_window_days: int = 30
    last_updated: datetime = field(default_factory=datetime.utcnow)
    expectation_version: int = 1


class ExpectationLearner:
    """
    Learns expected ranges from historical profiling metrics.

    Computes expected mean/variance, control limits (Shewhart/EWMA),
    learned distributions, and categorical frequency distributions
    from historical profiling runs.

    Example:
        >>> learner = ExpectationLearner(storage_config, engine)
        >>> expectation = learner.learn_expectations(
        ...     table_name="users",
        ...     column_name="age",
        ...     metric_name="mean",
        ...     window_days=30
        ... )
        >>> if expectation:
        ...     print(f"Expected mean: {expectation.expected_mean}")
        ...     lcl = expectation.lower_control_limit
        ...     ucl = expectation.upper_control_limit
        ...     print(f"Control limits: {lcl} - {ucl}")
    """

    def __init__(
        self,
        storage_config: StorageConfig,
        engine: Engine,
        default_window_days: int = 30,
        min_samples: int = 5,
        ewma_lambda: float = 0.2,
    ):
        """
        Initialize expectation learner.

        Args:
            storage_config: Storage configuration
            engine: Database engine
            default_window_days: Default historical window in days
            min_samples: Minimum number of samples required for learning
            ewma_lambda: EWMA smoothing parameter (0 < lambda <= 1)
        """
        self.storage_config = storage_config
        self.engine = engine
        self.default_window_days = default_window_days
        self.min_samples = min_samples
        self.ewma_lambda = ewma_lambda

    def learn_expectations(
        self,
        table_name: str,
        column_name: str,
        metric_name: str,
        schema_name: Optional[str] = None,
        window_days: Optional[int] = None,
    ) -> Optional[LearnedExpectation]:
        """
        Learn expectations for a specific metric.

        Args:
            table_name: Name of the table
            column_name: Name of the column
            metric_name: Name of the metric
            schema_name: Optional schema name
            window_days: Historical window in days (uses default if None)

        Returns:
            LearnedExpectation or None if insufficient data
        """
        window = window_days or self.default_window_days

        # Get historical metric values
        historical_values = self._get_historical_metrics(
            table_name, column_name, metric_name, schema_name, window
        )

        if len(historical_values) < self.min_samples:
            logger.debug(
                f"Insufficient samples for {table_name}.{column_name}.{metric_name}: "
                f"{len(historical_values)} < {self.min_samples}"
            )
            return None

        # Get column type
        column_type = self._get_column_type(table_name, column_name, schema_name)

        # Create expectation
        expectation = LearnedExpectation(
            table_name=table_name,
            schema_name=schema_name,
            column_name=column_name,
            metric_name=metric_name,
            column_type=column_type,
            sample_size=len(historical_values),
            learning_window_days=window,
            ewma_lambda=self.ewma_lambda,
        )

        # Compute expected statistics
        self._compute_expected_statistics(expectation, historical_values)

        # Compute control limits
        self._compute_control_limits(expectation, historical_values)

        # Learn distribution (for numeric metrics)
        if self._is_numeric_metric(metric_name):
            self._learn_distribution(expectation, historical_values)

        # Learn categorical distribution (if categorical column)
        if self._is_categorical_column(column_type, metric_name):
            self._learn_categorical_distribution(
                expectation, table_name, column_name, schema_name, window
            )

        return expectation

    def _get_historical_metrics(
        self,
        table_name: str,
        column_name: str,
        metric_name: str,
        schema_name: Optional[str],
        window_days: int,
    ) -> List[float]:
        """Retrieve historical metric values from database."""
        cutoff_date = datetime.utcnow() - timedelta(days=window_days)

        # Build schema filter
        schema_filter = ""
        if schema_name:
            schema_filter = "AND r.schema_name = :schema_name AND runs.schema_name = :schema_name"

        query = text(
            f"""
            SELECT CAST(r.metric_value AS FLOAT) as value
            FROM {self.storage_config.results_table} r
            INNER JOIN {self.storage_config.runs_table} runs
                ON r.run_id = runs.run_id
                AND r.dataset_name = runs.dataset_name
            WHERE r.dataset_name = :table_name
            {schema_filter}
            AND r.column_name = :column_name
            AND r.metric_name = :metric_name
            AND runs.profiled_at >= :cutoff_date
            AND runs.profiled_at < CURRENT_TIMESTAMP
            AND (runs.status = 'completed' OR runs.status IS NULL)
            AND r.metric_value IS NOT NULL
            AND r.metric_value != ''
            ORDER BY runs.profiled_at DESC
        """
        )

        params = {
            "table_name": table_name,
            "column_name": column_name,
            "metric_name": metric_name,
            "cutoff_date": cutoff_date,
        }
        if schema_name:
            params["schema_name"] = schema_name

        values = []
        with self.engine.connect() as conn:
            result = conn.execute(query, params)
            for row in result:
                try:
                    val = float(row.value)
                    if math.isfinite(val):
                        values.append(val)
                except (ValueError, TypeError):
                    continue

        return values

    def _compute_expected_statistics(self, expectation: LearnedExpectation, values: List[float]):
        """Compute expected mean, variance, stddev, min, max."""
        if not values:
            return

        expectation.expected_mean = statistics.mean(values)
        expectation.expected_variance = statistics.variance(values) if len(values) > 1 else 0.0
        expectation.expected_stddev = statistics.stdev(values) if len(values) > 1 else 0.0
        expectation.expected_min = min(values)
        expectation.expected_max = max(values)

    def _compute_control_limits(self, expectation: LearnedExpectation, values: List[float]):
        """Compute control limits using Shewhart (default) or EWMA."""
        if not values:
            return

        mean = expectation.expected_mean
        if mean is None:
            return

        stddev = expectation.expected_stddev or 0.0

        # Shewhart control limits (3-sigma)
        if stddev > 0:
            expectation.lower_control_limit = mean - (3 * stddev)
            expectation.upper_control_limit = mean + (3 * stddev)
        else:
            # If no variance, use min/max
            expectation.lower_control_limit = expectation.expected_min
            expectation.upper_control_limit = expectation.expected_max

        expectation.lcl_method = "shewhart"
        expectation.ucl_method = "shewhart"

        # Also compute EWMA if we have enough samples
        if len(values) >= 10:
            self._compute_ewma(expectation, values)

    def _compute_ewma(self, expectation: LearnedExpectation, values: List[float]):
        """Compute Exponentially Weighted Moving Average."""
        if not values:
            return

        # Reverse to process oldest to newest
        values_reversed = list(reversed(values))
        lambda_val = expectation.ewma_lambda

        # Initialize with first value
        ewma = values_reversed[0]

        # Compute EWMA iteratively
        for value in values_reversed[1:]:
            ewma = (lambda_val * value) + ((1 - lambda_val) * ewma)

        expectation.ewma_value = ewma

        # EWMA control limits could be computed here if needed
        # For now, we keep Shewhart as primary

    def _learn_distribution(self, expectation: LearnedExpectation, values: List[float]):
        """Learn distribution type and parameters for numeric metrics."""
        if len(values) < 5:
            return

        # Test for normal distribution (simplified heuristic)
        try:
            mean = expectation.expected_mean
            if mean is None:
                expectation.distribution_type = "empirical"
                return

            median = statistics.median(values)

            # Calculate skewness
            skewness = self._calculate_skewness(values, mean)

            # Check if values approximate normal distribution
            # Heuristic: check if mean ≈ median and distribution is roughly symmetric
            if abs(skewness) < 0.5 and abs(mean - median) / (abs(mean) + 1e-10) < 0.2:
                expectation.distribution_type = "normal"
                expectation.distribution_params = {
                    "mean": mean,
                    "stddev": expectation.expected_stddev,
                }
            else:
                # Store as empirical distribution
                expectation.distribution_type = "empirical"
                expectation.distribution_params = {
                    "mean": mean,
                    "stddev": expectation.expected_stddev,
                    "min": expectation.expected_min,
                    "max": expectation.expected_max,
                    "skewness": skewness,
                }
        except Exception as e:
            logger.warning(f"Failed to learn distribution: {e}")
            expectation.distribution_type = "empirical"

    def _calculate_skewness(self, values: List[float], mean: float) -> float:
        """Calculate sample skewness."""
        if len(values) < 3:
            return 0.0

        stddev = statistics.stdev(values) if len(values) > 1 else 1.0
        if stddev == 0:
            return 0.0

        n = len(values)
        skew_sum = sum(((x - mean) / stddev) ** 3 for x in values)
        skewness = (n / ((n - 1) * (n - 2))) * skew_sum

        return skewness

    def _learn_categorical_distribution(
        self,
        expectation: LearnedExpectation,
        table_name: str,
        column_name: str,
        schema_name: Optional[str],
        window_days: int,
    ):
        """Learn expected frequency distribution for categorical columns."""
        cutoff_date = datetime.utcnow() - timedelta(days=window_days)

        # Build schema filter
        schema_filter = ""
        if schema_name:
            schema_filter = "AND r.schema_name = :schema_name AND runs.schema_name = :schema_name"

        # Try to get top_values or category_distribution from results
        query = text(
            f"""
            SELECT r.metric_value
            FROM {self.storage_config.results_table} r
            INNER JOIN {self.storage_config.runs_table} runs
                ON r.run_id = runs.run_id
                AND r.dataset_name = runs.dataset_name
            WHERE r.dataset_name = :table_name
            {schema_filter}
            AND r.column_name = :column_name
            AND r.metric_name IN ('top_values', 'category_distribution')
            AND runs.profiled_at >= :cutoff_date
            AND (runs.status = 'completed' OR runs.status IS NULL)
            ORDER BY runs.profiled_at DESC
            LIMIT 10
        """
        )

        params = {
            "table_name": table_name,
            "column_name": column_name,
            "cutoff_date": cutoff_date,
        }
        if schema_name:
            params["schema_name"] = schema_name

        # Aggregate category distributions across runs
        category_counts: Dict[str, int] = {}
        total_runs = 0

        with self.engine.connect() as conn:
            result = conn.execute(query, params)
            for row in result:
                try:
                    if row.metric_value:
                        dist_data = (
                            json.loads(row.metric_value)
                            if isinstance(row.metric_value, str)
                            else row.metric_value
                        )
                        if isinstance(dist_data, dict):
                            total_runs += 1
                            for category, count in dist_data.items():
                                category_counts[category] = category_counts.get(category, 0) + count
                except (json.JSONDecodeError, TypeError):
                    continue

        if category_counts and total_runs > 0:
            # Normalize to frequencies
            total_count = sum(category_counts.values())
            expectation.category_distribution = {
                cat: (count / total_count) for cat, count in category_counts.items()
            }

    def _get_column_type(
        self, table_name: str, column_name: str, schema_name: Optional[str]
    ) -> Optional[str]:
        """Get column type from most recent run."""
        schema_filter = ""
        if schema_name:
            schema_filter = "AND r.schema_name = :schema_name"

        query = text(
            f"""
            SELECT DISTINCT r.column_type
            FROM {self.storage_config.results_table} r
            INNER JOIN {self.storage_config.runs_table} runs
                ON r.run_id = runs.run_id
                AND r.dataset_name = runs.dataset_name
            WHERE r.dataset_name = :table_name
            {schema_filter}
            AND r.column_name = :column_name
            ORDER BY runs.profiled_at DESC
            LIMIT 1
        """
        )

        params = {"table_name": table_name, "column_name": column_name}
        if schema_name:
            params["schema_name"] = schema_name

        with self.engine.connect() as conn:
            result = conn.execute(query, params).fetchone()
            return result[0] if result else None

    @staticmethod
    def _is_numeric_metric(metric_name: str) -> bool:
        """Check if metric is numeric."""
        numeric_metrics = {
            "mean",
            "stddev",
            "min",
            "max",
            "count",
            "null_ratio",
            "unique_ratio",
        }
        return metric_name in numeric_metrics

    @staticmethod
    def _is_categorical_column(column_type: Optional[str], metric_name: str) -> bool:
        """Check if column is likely categorical."""
        if not column_type:
            return False
        col_type_lower = column_type.lower()
        categorical_keywords = ["varchar", "char", "text", "string", "enum"]
        return any(kw in col_type_lower for kw in categorical_keywords)
