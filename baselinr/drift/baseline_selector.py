"""
Baseline selector for automatic baseline selection in drift detection.

Selects appropriate baseline based on column characteristics and historical data patterns.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from ..config.schema import DriftDetectionConfig, StorageConfig

logger = logging.getLogger(__name__)


@dataclass
class BaselineResult:
    """Result of baseline selection."""

    method: str  # "last_run", "moving_average", "prior_period", "stable_window"
    baseline_value: Any  # Computed baseline value (or single value)
    baseline_run_id: Optional[str] = None  # Single run ID if applicable
    metadata: Optional[Dict[str, Any]] = None  # Additional metadata about selection

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaselineSelector:
    """Selects appropriate baseline for drift detection based on column characteristics."""

    def __init__(
        self,
        storage_config: StorageConfig,
        drift_config: DriftDetectionConfig,
        engine: Engine,
    ):
        """
        Initialize baseline selector.

        Args:
            storage_config: Storage configuration
            drift_config: Drift detection configuration
            engine: Database engine
        """
        self.storage_config = storage_config
        self.drift_config = drift_config
        self.engine = engine

    def select_baseline(
        self,
        dataset_name: str,
        column_name: str,
        metric_name: str,
        current_run_id: str,
        schema_name: Optional[str] = None,
    ) -> BaselineResult:
        """
        Select baseline for a specific column and metric.

        Args:
            dataset_name: Name of the dataset
            column_name: Name of the column
            metric_name: Name of the metric
            current_run_id: Current run ID to compare against
            schema_name: Optional schema name

        Returns:
            BaselineResult with selected baseline method and value
        """
        baseline_config = self.drift_config.baselines
        strategy = baseline_config.get("strategy", "last_run")

        # If explicit strategy, use it
        if strategy == "last_run":
            return self._get_last_successful_run(
                dataset_name, column_name, metric_name, current_run_id, schema_name
            )
        elif strategy == "moving_average":
            return self._get_moving_average_baseline(
                dataset_name, column_name, metric_name, current_run_id, schema_name
            )
        elif strategy == "prior_period":
            return self._get_prior_period_baseline(
                dataset_name, column_name, metric_name, current_run_id, schema_name
            )
        elif strategy == "stable_window":
            return self._get_stable_window_baseline(
                dataset_name, column_name, metric_name, current_run_id, schema_name
            )
        elif strategy == "auto":
            # Auto-select based on column characteristics
            return self._auto_select_baseline(
                dataset_name, column_name, metric_name, current_run_id, schema_name
            )
        else:
            # Fallback to last run
            logger.warning(f"Unknown baseline strategy: {strategy}, using last_run")
            return self._get_last_successful_run(
                dataset_name, column_name, metric_name, current_run_id, schema_name
            )

    def _get_last_successful_run(
        self,
        dataset_name: str,
        column_name: str,
        metric_name: str,
        current_run_id: str,
        schema_name: Optional[str] = None,
    ) -> BaselineResult:
        """Get the last successful run before current run."""
        # Get runs before current run, ordered by time
        runs = self._get_runs_before(
            dataset_name, current_run_id, schema_name, limit=1, status="completed"
        )

        if not runs:
            raise ValueError(f"No successful runs found before {current_run_id} for {dataset_name}")

        baseline_run_id = runs[0]
        baseline_value = self._get_metric_value(baseline_run_id, column_name, metric_name)

        if baseline_value is None:
            raise ValueError(
                f"Metric {metric_name} not found for column {column_name} in run {baseline_run_id}"
            )

        return BaselineResult(
            method="last_run",
            baseline_value=baseline_value,
            baseline_run_id=baseline_run_id,
            metadata={"run_id": baseline_run_id},
        )

    def _get_moving_average_baseline(
        self,
        dataset_name: str,
        column_name: str,
        metric_name: str,
        current_run_id: str,
        schema_name: Optional[str] = None,
    ) -> BaselineResult:
        """Compute baseline as moving average of last N runs."""
        windows = self.drift_config.baselines.get("windows", {})
        n_runs = windows.get("moving_average", 7)

        # Get last N runs before current
        runs = self._get_runs_before(
            dataset_name, current_run_id, schema_name, limit=n_runs, status="completed"
        )

        if len(runs) < 2:
            # Fallback to last run if insufficient data
            logger.warning(f"Only {len(runs)} runs available for moving average, using last run")
            return self._get_last_successful_run(
                dataset_name, column_name, metric_name, current_run_id, schema_name
            )

        # Get metric values for all runs
        values = []
        run_ids = []
        for run_id in runs:
            value = self._get_metric_value(run_id, column_name, metric_name)
            if value is not None and isinstance(value, (int, float)):
                values.append(value)
                run_ids.append(run_id)

        if not values:
            raise ValueError(
                f"No valid metric values found for {column_name}.{metric_name} in runs"
            )

        # Compute average
        avg_value = sum(values) / len(values)

        return BaselineResult(
            method="moving_average",
            baseline_value=avg_value,
            baseline_run_id=None,  # Not a single run
            metadata={
                "n_runs": len(values),
                "run_ids": run_ids,
                "window_size": n_runs,
                "individual_values": values,
            },
        )

    def _get_prior_period_baseline(
        self,
        dataset_name: str,
        column_name: str,
        metric_name: str,
        current_run_id: str,
        schema_name: Optional[str] = None,
    ) -> BaselineResult:
        """Get baseline from same period last week/month."""
        windows = self.drift_config.baselines.get("windows", {})
        prior_period_days = windows.get("prior_period", 7)

        # Get current run timestamp
        current_meta = self._get_run_metadata(current_run_id)
        current_time = current_meta["profiled_at"]

        if isinstance(current_time, str):
            current_time = datetime.fromisoformat(current_time.replace("Z", "+00:00"))
        elif not isinstance(current_time, datetime):
            current_time = datetime.fromisoformat(str(current_time))

        # Calculate target date
        target_date = current_time - timedelta(days=prior_period_days)

        # Find run closest to target date
        runs = self._get_runs_by_date_range(
            dataset_name,
            start_date=target_date - timedelta(days=prior_period_days // 2),
            end_date=target_date + timedelta(days=prior_period_days // 2),
            schema_name=schema_name,
            status="completed",
        )

        if not runs:
            # Fallback to last run
            logger.warning(
                f"No runs found for prior period ({prior_period_days} days ago), using last run"
            )
            return self._get_last_successful_run(
                dataset_name, column_name, metric_name, current_run_id, schema_name
            )

        # Find closest run to target date
        closest_run = None
        min_diff = None
        for run_id, run_meta in runs.items():
            run_time = run_meta["profiled_at"]
            if isinstance(run_time, str):
                run_time = datetime.fromisoformat(run_time.replace("Z", "+00:00"))
            elif not isinstance(run_time, datetime):
                run_time = datetime.fromisoformat(str(run_time))

            diff = abs((run_time - target_date).total_seconds())
            if min_diff is None or diff < min_diff:
                min_diff = diff
                closest_run = run_id

        if closest_run is None:
            raise ValueError("Could not find closest run for prior period")

        baseline_value = self._get_metric_value(closest_run, column_name, metric_name)

        if baseline_value is None:
            raise ValueError(
                f"Metric {metric_name} not found for column {column_name} in run {closest_run}"
            )

        return BaselineResult(
            method="prior_period",
            baseline_value=baseline_value,
            baseline_run_id=closest_run,
            metadata={
                "run_id": closest_run,
                "target_date": target_date.isoformat(),
                "prior_period_days": prior_period_days,
                "time_difference_seconds": min_diff,
            },
        )

    def _get_stable_window_baseline(
        self,
        dataset_name: str,
        column_name: str,
        metric_name: str,
        current_run_id: str,
        schema_name: Optional[str] = None,
    ) -> BaselineResult:
        """Find historical window with low drift and use its average."""
        # Get historical runs (last 30 or available)
        runs = self._get_runs_before(
            dataset_name, current_run_id, schema_name, limit=30, status="completed"
        )

        if len(runs) < 3:
            # Need at least 3 runs to find a stable window
            return self._get_last_successful_run(
                dataset_name, column_name, metric_name, current_run_id, schema_name
            )

        # Calculate drift scores between consecutive runs
        drift_scores = self._get_historical_drift_scores(runs, column_name, metric_name)

        if not drift_scores:
            # Fallback to last run
            return self._get_last_successful_run(
                dataset_name, column_name, metric_name, current_run_id, schema_name
            )

        # Find window with lowest average drift (looking for runs with minimal change)
        # Use a sliding window of 5 runs
        window_size = min(5, len(runs) - 1)
        best_window_start = 0
        best_avg_drift = float("inf")

        for i in range(len(drift_scores) - window_size + 1):
            window_scores = drift_scores[i : i + window_size]
            avg_drift = sum(abs(score) for score in window_scores) / len(window_scores)

            if avg_drift < best_avg_drift:
                best_avg_drift = avg_drift
                best_window_start = i

        # Get runs in the stable window (inclusive of end)
        stable_runs = runs[best_window_start : best_window_start + window_size + 1]

        # Compute average of stable window
        values = []
        for run_id in stable_runs:
            value = self._get_metric_value(run_id, column_name, metric_name)
            if value is not None and isinstance(value, (int, float)):
                values.append(value)

        if not values:
            raise ValueError("No valid values found in stable window")

        avg_value = sum(values) / len(values)

        return BaselineResult(
            method="stable_window",
            baseline_value=avg_value,
            baseline_run_id=None,
            metadata={
                "window_size": len(values),
                "run_ids": stable_runs,
                "average_drift": best_avg_drift,
                "individual_values": values,
            },
        )

    def _auto_select_baseline(
        self,
        dataset_name: str,
        column_name: str,
        metric_name: str,
        current_run_id: str,
        schema_name: Optional[str] = None,
    ) -> BaselineResult:
        """Automatically select baseline based on column characteristics."""
        windows = self.drift_config.baselines.get("windows", {})
        min_runs = windows.get("min_runs", 3)

        # Get historical runs for analysis
        runs = self._get_runs_before(
            dataset_name, current_run_id, schema_name, limit=30, status="completed"
        )

        if len(runs) < min_runs:
            # Not enough data for auto-selection, use last run
            logger.debug(
                f"Only {len(runs)} runs available (need {min_runs}), using last_run strategy"
            )
            return self._get_last_successful_run(
                dataset_name, column_name, metric_name, current_run_id, schema_name
            )

        # Analyze column characteristics
        characteristics = self._analyze_column_characteristics(runs, column_name, metric_name)

        # Apply heuristic
        if characteristics.get("is_high_variance", False):
            logger.debug(f"High variance detected for {column_name}, using moving_average")
            return self._get_moving_average_baseline(
                dataset_name, column_name, metric_name, current_run_id, schema_name
            )
        elif characteristics.get("is_seasonal", False):
            logger.debug(f"Seasonality detected for {column_name}, using prior_period")
            return self._get_prior_period_baseline(
                dataset_name, column_name, metric_name, current_run_id, schema_name
            )
        else:
            # Default to last run for stable columns
            logger.debug(f"Stable column {column_name}, using last_run")
            return self._get_last_successful_run(
                dataset_name, column_name, metric_name, current_run_id, schema_name
            )

    def _analyze_column_characteristics(
        self, runs: List[str], column_name: str, metric_name: str
    ) -> Dict[str, Any]:
        """
        Analyze column characteristics to determine optimal baseline strategy.

        Returns dict with:
        - is_high_variance: bool
        - is_seasonal: bool
        - coefficient_of_variation: float
        """
        # Get metric values
        values = []
        timestamps = []
        for run_id in runs:
            value = self._get_metric_value(run_id, column_name, metric_name)
            if value is not None and isinstance(value, (int, float)):
                values.append(value)
                meta = self._get_run_metadata(run_id)
                ts = meta["profiled_at"]
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                elif not isinstance(ts, datetime):
                    ts = datetime.fromisoformat(str(ts))
                timestamps.append(ts)

        if len(values) < 2:
            return {
                "is_high_variance": False,
                "is_seasonal": False,
                "coefficient_of_variation": 0.0,
            }

        # Calculate variance
        cv = self._calculate_column_variance(values)

        # Detect seasonality (only if we have enough timestamps)
        is_seasonal = False
        if len(timestamps) >= 7:
            is_seasonal = self._detect_seasonality(values, timestamps)

        # High variance threshold: CV > 0.2
        is_high_variance = cv > 0.2

        return {
            "is_high_variance": is_high_variance,
            "is_seasonal": is_seasonal,
            "coefficient_of_variation": cv,
        }

    def _calculate_column_variance(self, values: List[float]) -> float:
        """Calculate coefficient of variation (CV = std/mean)."""
        if len(values) < 2:
            return 0.0

        mean = sum(values) / len(values)
        if mean == 0:
            return 0.0

        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance**0.5

        result = std_dev / abs(mean)
        return float(result)

    def _detect_seasonality(self, values: List[float], timestamps: List[datetime]) -> bool:
        """
        Detect weekly or monthly seasonality in metric values.

        Simple heuristic: check if values show periodicity around 7 or 30 days.
        """
        if len(values) < 7 or len(timestamps) < 7:
            return False

        # Sort by timestamp
        sorted_data = sorted(zip(timestamps, values))
        timestamps_sorted = [t for t, _ in sorted_data]
        values_sorted = [v for _, v in sorted_data]

        # Check for weekly pattern (7 days)
        weekly_pattern = self._check_periodicity(values_sorted, timestamps_sorted, 7)

        # Check for monthly pattern (30 days)
        monthly_pattern = self._check_periodicity(values_sorted, timestamps_sorted, 30)

        return weekly_pattern or monthly_pattern

    def _check_periodicity(
        self, values: List[float], timestamps: List[datetime], period_days: int
    ) -> bool:
        """Check if values show periodicity with given period."""
        # Simple heuristic: group values by day-of-period and check variance within groups
        # If variance within groups is low but between groups is high, there's periodicity

        if len(values) < period_days * 2:
            return False

        # Group by day of period
        groups: Dict[int, List[float]] = {}
        for i, (ts, val) in enumerate(zip(timestamps, values)):
            days_since_start = (ts - timestamps[0]).days
            day_in_period = days_since_start % period_days
            if day_in_period not in groups:
                groups[day_in_period] = []
            groups[day_in_period].append(val)

        if len(groups) < 3:  # Need at least 3 groups
            return False

        # Calculate variance within groups vs between groups
        within_variances = []
        group_means = []

        for group_values in groups.values():
            if len(group_values) < 2:
                continue
            mean = sum(group_values) / len(group_values)
            group_means.append(mean)
            variance = sum((x - mean) ** 2 for x in group_values) / len(group_values)
            within_variances.append(variance)

        if not within_variances or not group_means:
            return False

        avg_within_var = sum(within_variances) / len(within_variances)
        overall_mean = sum(group_means) / len(group_means)
        between_var = sum((m - overall_mean) ** 2 for m in group_means) / len(group_means)

        # If between-group variance is significantly higher than within-group variance,
        # there's a pattern
        if avg_within_var > 0:
            ratio = between_var / avg_within_var
            # Threshold: ratio > 1.5 indicates periodicity (lowered for better detection)
            return ratio > 1.5

        # If within-group variance is very low and we have clear groups, there's periodicity
        if avg_within_var == 0 and len(group_means) >= 3:
            # Check if group means differ significantly
            if max(group_means) - min(group_means) > 0:
                return True

        return False

    def _get_historical_drift_scores(
        self, runs: List[str], column_name: str, metric_name: str
    ) -> List[float]:
        """Calculate drift scores (percentage change) between consecutive runs."""
        scores = []
        for i in range(len(runs) - 1):
            baseline_run = runs[i + 1]  # Older run
            current_run = runs[i]  # Newer run

            baseline_value = self._get_metric_value(baseline_run, column_name, metric_name)
            current_value = self._get_metric_value(current_run, column_name, metric_name)

            if (
                baseline_value is not None
                and current_value is not None
                and isinstance(baseline_value, (int, float))
                and isinstance(current_value, (int, float))
                and baseline_value != 0
            ):
                change_percent = ((current_value - baseline_value) / abs(baseline_value)) * 100
                scores.append(change_percent)
            else:
                scores.append(0.0)  # No change if values missing

        return scores

    # Database helper methods

    def _get_runs_before(
        self,
        dataset_name: str,
        current_run_id: str,
        schema_name: Optional[str] = None,
        limit: int = 10,
        status: Optional[str] = None,
    ) -> List[str]:
        """Get run IDs before (and not including) current run, ordered by time DESC."""
        # First get current run timestamp
        current_meta = self._get_run_metadata(current_run_id)
        current_time = current_meta["profiled_at"]

        # Build status filter - use status if provided, otherwise include NULL (legacy runs)
        status_filter = ""
        if status:
            status_filter = "AND (status = :status OR status IS NULL)"
        else:
            # If no status filter, include all runs
            # (including NULL status for backward compatibility)
            status_filter = ""

        query = f"""
            SELECT run_id FROM {self.storage_config.runs_table}
            WHERE dataset_name = :dataset_name
            AND profiled_at < :current_time
            {"AND schema_name = :schema_name" if schema_name else ""}
            {status_filter}
            ORDER BY profiled_at DESC
            LIMIT :limit
        """

        params = {
            "dataset_name": dataset_name,
            "current_time": current_time,
            "limit": limit,
        }
        if schema_name:
            params["schema_name"] = schema_name
        if status:
            params["status"] = status

        with self.engine.connect() as conn:
            result = conn.execute(text(query), params)
            return [row[0] for row in result]

    def _get_runs_by_date_range(
        self,
        dataset_name: str,
        start_date: datetime,
        end_date: datetime,
        schema_name: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Get runs within date range, returned as {run_id: metadata}."""
        # Build status filter - use status if provided, otherwise include NULL (legacy runs)
        status_filter = ""
        if status:
            status_filter = "AND (status = :status OR status IS NULL)"
        else:
            status_filter = ""

        # SQLite date comparison - use DATE() function for proper comparison
        query = f"""
            SELECT run_id, dataset_name, schema_name, profiled_at, status, row_count, column_count
            FROM {self.storage_config.runs_table}
            WHERE dataset_name = :dataset_name
            AND DATE(profiled_at) >= DATE(:start_date)
            AND DATE(profiled_at) <= DATE(:end_date)
            {"AND schema_name = :schema_name" if schema_name else ""}
            {status_filter}
            ORDER BY profiled_at DESC
        """

        params = {
            "dataset_name": dataset_name,
            "start_date": start_date,
            "end_date": end_date,
        }
        if schema_name:
            params["schema_name"] = schema_name
        if status:
            params["status"] = status

        runs = {}
        with self.engine.connect() as conn:
            result = conn.execute(text(query), params)
            for row in result:
                runs[row.run_id] = {
                    "run_id": row.run_id,
                    "dataset_name": row.dataset_name,
                    "schema_name": row.schema_name,
                    "profiled_at": row.profiled_at,
                    "status": row.status,
                    "row_count": row.row_count,
                    "column_count": row.column_count,
                }

        return runs

    def _get_run_metrics_for_column(
        self, runs: List[str], column_name: str, metric_name: str
    ) -> Dict[str, Any]:
        """Get metric values for a column across multiple runs."""
        if not runs:
            return {}

        placeholders = ", ".join([f":run_{i}" for i in range(len(runs))])
        query = f"""
            SELECT run_id, metric_value
            FROM {self.storage_config.results_table}
            WHERE run_id IN ({placeholders})
            AND column_name = :column_name
            AND metric_name = :metric_name
        """

        params = {f"run_{i}": run_id for i, run_id in enumerate(runs)}
        params["column_name"] = column_name
        params["metric_name"] = metric_name

        metrics = {}
        with self.engine.connect() as conn:
            result = conn.execute(text(query), params)
            for row in result:
                try:
                    metrics[row.run_id] = float(row.metric_value) if row.metric_value else None
                except (ValueError, TypeError):
                    metrics[row.run_id] = row.metric_value

        return metrics

    def _get_metric_value(self, run_id: str, column_name: str, metric_name: str) -> Optional[Any]:
        """Get a single metric value for a column in a run."""
        query = text(
            f"""
            SELECT metric_value
            FROM {self.storage_config.results_table}
            WHERE run_id = :run_id
            AND column_name = :column_name
            AND metric_name = :metric_name
            LIMIT 1
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(
                query, {"run_id": run_id, "column_name": column_name, "metric_name": metric_name}
            ).fetchone()

            if not result or result[0] is None:
                return None

            # Try to convert to float
            try:
                return float(result[0])
            except (ValueError, TypeError):
                return result[0]

    def _get_run_metadata(self, run_id: str) -> Dict[str, Any]:
        """Get metadata for a run."""
        query = text(
            f"""
            SELECT run_id, dataset_name, schema_name, profiled_at, status, row_count, column_count
            FROM {self.storage_config.runs_table}
            WHERE run_id = :run_id
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(query, {"run_id": run_id}).fetchone()
            if not result:
                raise ValueError(f"Run not found: {run_id}")

            return {
                "run_id": result.run_id,
                "dataset_name": result.dataset_name,
                "schema_name": result.schema_name,
                "profiled_at": result.profiled_at,
                "status": result.status,
                "row_count": result.row_count,
                "column_count": result.column_count,
            }
