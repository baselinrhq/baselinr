"""
Main anomaly detector for Baselinr.

Orchestrates multiple detection methods using learned expectations
as baselines to detect outliers and seasonal anomalies.
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from ..config.schema import ColumnConfig, StorageConfig
from ..events import EventBus
from ..learning.expectation_learner import LearnedExpectation
from ..learning.expectation_storage import ExpectationStorage
from ..profiling.column_matcher import ColumnMatcher
from .anomaly_types import AnomalyType
from .detection_methods import (
    DetectionResult,
    EWMADetector,
    IQRDetector,
    MADDetector,
    RegimeShiftDetector,
    TrendSeasonalityDetector,
)

logger = logging.getLogger(__name__)


@dataclass
class AnomalyResult:
    """Result from anomaly detection."""

    anomaly_type: AnomalyType
    table_name: str
    schema_name: Optional[str]
    column_name: str
    metric_name: str
    expected_value: Optional[float]
    actual_value: float
    deviation_score: float
    severity: str  # "low", "medium", "high"
    detection_method: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    explanation: Optional[str] = None  # Human-readable explanation


class AnomalyDetector:
    """
    Detects anomalies using learned expectations as baselines.

    Uses multiple detection methods (IQR, MAD, EWMA, trend/seasonality,
    regime shift) to identify outliers and anomalies in profiling metrics.

    Example:
        >>> detector = AnomalyDetector(storage_config, engine, event_bus)
        >>> anomalies = detector.detect_anomalies(
        ...     table_name="users",
        ...     column_name="age",
        ...     metric_name="mean",
        ...     current_value=45.5
        ... )
    """

    # Metrics that support anomaly detection
    NUMERIC_METRICS = [
        "count",
        "null_ratio",
        "unique_ratio",
        "mean",
        "stddev",
        "min",
        "max",
    ]

    def __init__(
        self,
        storage_config: StorageConfig,
        engine: Engine,
        event_bus: Optional[EventBus] = None,
        enabled_methods: Optional[List[str]] = None,
        iqr_threshold: float = 1.5,
        mad_threshold: float = 3.0,
        ewma_deviation_threshold: float = 2.0,
        seasonality_enabled: bool = True,
        regime_shift_enabled: bool = True,
        regime_shift_window: int = 3,
        regime_shift_sensitivity: float = 0.05,
        llm_config=None,
    ):
        """
        Initialize anomaly detector.

        Args:
            storage_config: Storage configuration
            engine: Database engine
            event_bus: Optional event bus for emitting anomaly events
            enabled_methods: List of enabled detection methods
                (default: all methods)
            iqr_threshold: IQR multiplier threshold
            mad_threshold: MAD threshold (modified z-score)
            ewma_deviation_threshold: EWMA deviation threshold (stddevs)
            seasonality_enabled: Whether to enable seasonality detection
            regime_shift_enabled: Whether to enable regime shift detection
            regime_shift_window: Number of recent runs for regime shift
            regime_shift_sensitivity: P-value threshold for regime shift
            llm_config: Optional LLM configuration for explanations
        """
        self.storage_config = storage_config
        self.engine = engine
        self.event_bus = event_bus
        self.expectation_storage = ExpectationStorage(storage_config=storage_config, engine=engine)
        self.llm_config = llm_config

        # Default to all methods if not specified
        if enabled_methods is None:
            enabled_methods = [
                "control_limits",
                "iqr",
                "mad",
                "ewma",
                "seasonality",
                "regime_shift",
            ]

        self.enabled_methods = enabled_methods

        # Initialize detection methods
        self.iqr_detector = IQRDetector(threshold=iqr_threshold)
        self.mad_detector = MADDetector(threshold=mad_threshold)
        self.ewma_detector = EWMADetector(deviation_threshold=ewma_deviation_threshold)
        self.trend_seasonality_detector = TrendSeasonalityDetector(
            seasonality_enabled=seasonality_enabled,
            deviation_threshold=ewma_deviation_threshold,
        )
        self.regime_shift_detector = RegimeShiftDetector(
            window_size=regime_shift_window,
            sensitivity=regime_shift_sensitivity,
        )

    def detect_anomalies(
        self,
        table_name: str,
        column_name: str,
        metric_name: str,
        current_value: float,
        schema_name: Optional[str] = None,
        current_timestamp: Optional[datetime] = None,
        column_configs: Optional[List[ColumnConfig]] = None,
        profiled_columns: Optional[List[str]] = None,
    ) -> List[AnomalyResult]:
        """
        Detect anomalies for a metric value.

        Args:
            table_name: Name of the table
            column_name: Name of the column
            metric_name: Name of the metric
            current_value: Current metric value to check
            schema_name: Optional schema name
            current_timestamp: Optional timestamp of current value
            column_configs: Optional column-level configurations
            profiled_columns: Optional list of columns that were actually profiled

        Returns:
            List of AnomalyResult objects for detected anomalies
        """
        if current_timestamp is None:
            current_timestamp = datetime.utcnow()

        # Check if column was profiled (dependency check)
        if profiled_columns is not None and column_name not in profiled_columns:
            logger.debug(
                f"Skipping anomaly detection for column {column_name}: column was not profiled"
            )
            return []

        # Check if anomaly detection is enabled for this column
        column_matcher = ColumnMatcher(column_configs=column_configs) if column_configs else None
        if not self._should_detect_anomaly(column_name, column_matcher):
            logger.debug(
                f"Skipping anomaly detection for column {column_name}: anomaly detection disabled"
            )
            return []

        # Get column-specific anomaly config if available
        column_anomaly_config = None
        enabled_methods = self.enabled_methods
        if column_matcher:
            column_config = column_matcher.get_column_anomaly_config(column_name)
            if column_config and column_config.anomaly:
                column_anomaly_config = column_config.anomaly
                # Override enabled methods if specified
                if column_anomaly_config.methods:
                    enabled_methods = column_anomaly_config.methods

        # Skip non-numeric metrics for most methods
        if metric_name not in self.NUMERIC_METRICS:
            logger.debug(f"Skipping anomaly detection for non-numeric metric: {metric_name}")
            return []

        # Retrieve learned expectation
        expectation = self.expectation_storage.get_expectation(
            table_name=table_name,
            column_name=column_name,
            metric_name=metric_name,
            schema_name=schema_name,
        )

        if not expectation:
            logger.debug(f"No expectation found for {table_name}.{column_name}.{metric_name}")
            return []

        anomalies = []

        # Apply column-specific thresholds if available
        iqr_threshold = self.iqr_detector.threshold
        mad_threshold = self.mad_detector.threshold
        ewma_threshold = self.ewma_detector.deviation_threshold

        if column_anomaly_config and column_anomaly_config.thresholds:
            if "iqr_threshold" in column_anomaly_config.thresholds:
                iqr_threshold = column_anomaly_config.thresholds["iqr_threshold"]
            if "mad_threshold" in column_anomaly_config.thresholds:
                mad_threshold = column_anomaly_config.thresholds["mad_threshold"]
            if "ewma_deviation_threshold" in column_anomaly_config.thresholds:
                ewma_threshold = column_anomaly_config.thresholds["ewma_deviation_threshold"]

        # Control limits check
        if "control_limits" in enabled_methods:
            result = self._check_control_limits(current_value, expectation)
            if result.is_anomaly:
                anomalies.append(
                    AnomalyResult(
                        anomaly_type=AnomalyType.CONTROL_LIMIT_BREACH,
                        table_name=table_name,
                        schema_name=schema_name,
                        column_name=column_name,
                        metric_name=metric_name,
                        expected_value=expectation.expected_mean,
                        actual_value=current_value,
                        deviation_score=result.score,
                        severity=result.severity,
                        detection_method="control_limits",
                        metadata=result.metadata,
                    )
                )

        # IQR detection
        if "iqr" in enabled_methods:
            historical_values = self._get_historical_metrics(
                table_name, column_name, metric_name, schema_name
            )
            if len(historical_values) >= 4:
                # Use column-specific threshold if different
                if iqr_threshold != self.iqr_detector.threshold:
                    from .detection_methods import IQRDetector

                    iqr_detector = IQRDetector(threshold=iqr_threshold)
                else:
                    iqr_detector = self.iqr_detector
                result = iqr_detector.detect(current_value, historical_values)
                if result.is_anomaly:
                    anomalies.append(
                        AnomalyResult(
                            anomaly_type=AnomalyType.IQR_DEVIATION,
                            table_name=table_name,
                            schema_name=schema_name,
                            column_name=column_name,
                            metric_name=metric_name,
                            expected_value=expectation.expected_mean,
                            actual_value=current_value,
                            deviation_score=result.score,
                            severity=result.severity,
                            detection_method="iqr",
                            metadata=result.metadata,
                        )
                    )

        # MAD detection
        if "mad" in enabled_methods:
            historical_values = self._get_historical_metrics(
                table_name, column_name, metric_name, schema_name
            )
            if len(historical_values) >= 3:
                # Use column-specific threshold if different
                if mad_threshold != self.mad_detector.threshold:
                    from .detection_methods import MADDetector

                    mad_detector = MADDetector(threshold=mad_threshold)
                else:
                    mad_detector = self.mad_detector
                result = mad_detector.detect(current_value, historical_values)
                if result.is_anomaly:
                    anomalies.append(
                        AnomalyResult(
                            anomaly_type=AnomalyType.MAD_DEVIATION,
                            table_name=table_name,
                            schema_name=schema_name,
                            column_name=column_name,
                            metric_name=metric_name,
                            expected_value=expectation.expected_mean,
                            actual_value=current_value,
                            deviation_score=result.score,
                            severity=result.severity,
                            detection_method="mad",
                            metadata=result.metadata,
                        )
                    )

        # EWMA detection
        if "ewma" in enabled_methods:
            # Use column-specific threshold if different
            if ewma_threshold != self.ewma_detector.deviation_threshold:
                from .detection_methods import EWMADetector

                ewma_detector = EWMADetector(deviation_threshold=ewma_threshold)
            else:
                ewma_detector = self.ewma_detector
            result = ewma_detector.detect(current_value, expectation)
            if result.is_anomaly:
                anomalies.append(
                    AnomalyResult(
                        anomaly_type=AnomalyType.EWMA_OUTLIER,
                        table_name=table_name,
                        schema_name=schema_name,
                        column_name=column_name,
                        metric_name=metric_name,
                        expected_value=expectation.ewma_value,
                        actual_value=current_value,
                        deviation_score=result.score,
                        severity=result.severity,
                        detection_method="ewma",
                        metadata=result.metadata,
                    )
                )

        # Trend/seasonality detection
        if "seasonality" in enabled_methods:
            historical_series = self._get_historical_series(
                table_name, column_name, metric_name, schema_name
            )
            if len(historical_series) >= 7:  # Need enough data for trend
                result = self.trend_seasonality_detector.detect(
                    current_value, current_timestamp, historical_series
                )
                if result.is_anomaly:
                    anomaly_type = AnomalyType.SEASONAL_ANOMALY
                    if "trend" in result.metadata.get("reason", "").lower():
                        anomaly_type = AnomalyType.TREND_ANOMALY

                    anomalies.append(
                        AnomalyResult(
                            anomaly_type=anomaly_type,
                            table_name=table_name,
                            schema_name=schema_name,
                            column_name=column_name,
                            metric_name=metric_name,
                            expected_value=expectation.expected_mean,
                            actual_value=current_value,
                            deviation_score=result.score,
                            severity=result.severity,
                            detection_method="trend_seasonality",
                            metadata=result.metadata,
                        )
                    )

        # Regime shift detection
        if "regime_shift" in enabled_methods:
            historical_values = self._get_historical_metrics(
                table_name, column_name, metric_name, schema_name
            )
            if len(historical_values) >= 5:
                # Get recent values (last N runs)
                recent_values = historical_values[: self.regime_shift_detector.window_size]
                baseline_values = historical_values[self.regime_shift_detector.window_size :]

                if len(recent_values) >= 2 and len(baseline_values) >= 2:
                    result = self.regime_shift_detector.detect(recent_values, baseline_values)
                    if result.is_anomaly:
                        anomalies.append(
                            AnomalyResult(
                                anomaly_type=AnomalyType.REGIME_SHIFT,
                                table_name=table_name,
                                schema_name=schema_name,
                                column_name=column_name,
                                metric_name=metric_name,
                                expected_value=expectation.expected_mean,
                                actual_value=current_value,
                                deviation_score=result.score,
                                severity=result.severity,
                                detection_method="regime_shift",
                                metadata=result.metadata,
                            )
                        )

        # Determine specific anomaly types for common metrics
        for anomaly in anomalies:
            self._categorize_anomaly(anomaly)

        # Generate LLM explanations for detected anomalies
        if self.llm_config and self.llm_config.enabled:
            self._generate_anomaly_explanations(anomalies, table_name, schema_name)

        return anomalies

    def _generate_anomaly_explanations(
        self,
        anomalies: List[AnomalyResult],
        table_name: str,
        schema_name: Optional[str],
    ):
        """Generate LLM explanations for detected anomalies."""
        try:
            from ..llm.explainer import LLMExplainer

            explainer = LLMExplainer(self.llm_config)

            for anomaly in anomalies:
                # Construct alert data for prompt
                alert_data = {
                    "table": table_name,
                    "column": anomaly.column_name,
                    "metric": anomaly.metric_name,
                    "expected_value": anomaly.expected_value,
                    "actual_value": anomaly.actual_value,
                    "deviation_score": anomaly.deviation_score,
                    "severity": anomaly.severity,
                    "anomaly_type": (
                        anomaly.anomaly_type.value
                        if hasattr(anomaly.anomaly_type, "value")
                        else str(anomaly.anomaly_type)
                    ),
                    "detection_method": anomaly.detection_method,
                    "metadata": anomaly.metadata or {},
                }

                # Generate explanation
                explanation = explainer.generate_explanation(
                    alert_data=alert_data,
                    alert_type="anomaly",
                    fallback_object=anomaly,
                )
                anomaly.explanation = explanation

        except Exception as e:
            logger.warning(f"Failed to generate anomaly explanations: {e}")

    def _should_detect_anomaly(
        self, column_name: str, column_matcher: Optional[ColumnMatcher]
    ) -> bool:
        """
        Check if anomaly detection should be performed for a column.

        Args:
            column_name: Name of the column
            column_matcher: Optional column matcher with column configs

        Returns:
            True if anomaly should be detected, False otherwise
        """
        if column_matcher is None:
            # No column configs: use default (anomaly enabled)
            return True

        column_config = column_matcher.get_column_anomaly_config(column_name)
        if column_config and column_config.anomaly:
            # Check if anomaly is explicitly disabled
            if column_config.anomaly.enabled is False:
                return False
            # If enabled is None or True, proceed with anomaly detection
            return True

        # No column-specific config: use default (anomaly enabled)
        return True

    def _check_control_limits(
        self, current_value: float, expectation: LearnedExpectation
    ) -> DetectionResult:
        """Check if value breaches control limits."""
        from .detection_methods import DetectionResult

        if expectation.lower_control_limit is None or expectation.upper_control_limit is None:
            return DetectionResult(
                is_anomaly=False,
                severity="none",
                score=0.0,
                metadata={"reason": "no_control_limits"},
            )

        lcl = expectation.lower_control_limit
        ucl = expectation.upper_control_limit

        is_breach = current_value < lcl or current_value > ucl

        if is_breach:
            mean = expectation.expected_mean or ((lcl + ucl) / 2)
            stddev = expectation.expected_stddev or ((ucl - lcl) / 6)

            if stddev > 0:
                deviation_stddevs = abs(current_value - mean) / stddev
            else:
                deviation_stddevs = abs(current_value - mean)

            # Determine severity
            if deviation_stddevs > 3.0:
                severity = "high"
            elif deviation_stddevs > 2.0:
                severity = "medium"
            else:
                severity = "low"

            score = min(deviation_stddevs / 3.0, 1.0)
        else:
            severity = "none"
            score = 0.0

        return DetectionResult(
            is_anomaly=is_breach,
            severity=severity,
            score=score,
            metadata={
                "lower_control_limit": lcl,
                "upper_control_limit": ucl,
                "current_value": current_value,
            },
        )

    def _get_historical_metrics(
        self,
        table_name: str,
        column_name: str,
        metric_name: str,
        schema_name: Optional[str],
        window_days: int = 90,
    ) -> List[float]:
        """Fetch historical metric values from baselinr_results."""
        cutoff_date = datetime.utcnow() - timedelta(days=window_days)

        schema_filter = ""
        if schema_name:
            schema_filter = "AND r.schema_name = :schema_name"
        else:
            schema_filter = "AND (r.schema_name IS NULL OR r.schema_name = :schema_name)"

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
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, params)
                for row in result:
                    try:
                        val = float(row.value)
                        if not (math.isnan(val) or math.isinf(val)):
                            values.append(val)
                    except (ValueError, TypeError):
                        continue
        except Exception as e:
            logger.warning(f"Failed to fetch historical metrics: {e}")

        return values

    def _get_historical_series(
        self,
        table_name: str,
        column_name: str,
        metric_name: str,
        schema_name: Optional[str],
        window_days: int = 90,
    ) -> List[tuple]:
        """Fetch historical metric values with timestamps for time-series analysis."""
        cutoff_date = datetime.utcnow() - timedelta(days=window_days)

        schema_filter = ""
        if schema_name:
            schema_filter = "AND r.schema_name = :schema_name"
        else:
            schema_filter = "AND (r.schema_name IS NULL OR r.schema_name = :schema_name)"

        query = text(
            f"""
            SELECT
                runs.profiled_at as timestamp,
                CAST(r.metric_value AS FLOAT) as value
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
            ORDER BY runs.profiled_at ASC
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

        series = []
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, params)
                for row in result:
                    try:
                        val = float(row.value)
                        timestamp = row.timestamp
                        if not (math.isnan(val) or math.isinf(val)) and timestamp:
                            series.append((timestamp, val))
                    except (ValueError, TypeError):
                        continue
        except Exception as e:
            logger.warning(f"Failed to fetch historical series: {e}")

        return series

    def _categorize_anomaly(self, anomaly: AnomalyResult):
        """Categorize anomaly into specific types based on metric."""
        # Map metrics to specific anomaly types
        if anomaly.metric_name == "count":
            if anomaly.actual_value > (anomaly.expected_value or 0):
                anomaly.anomaly_type = AnomalyType.ROW_COUNT_SPIKE
            else:
                anomaly.anomaly_type = AnomalyType.ROW_COUNT_DIP

        elif anomaly.metric_name == "null_ratio":
            if anomaly.actual_value > 0.9:
                anomaly.anomaly_type = AnomalyType.NULL_SPIKE

        elif anomaly.metric_name == "unique_ratio":
            if anomaly.actual_value < (anomaly.expected_value or 1.0) * 0.5:
                anomaly.anomaly_type = AnomalyType.UNIQUENESS_DROP

        elif anomaly.metric_name == "schema_freshness":
            # Track freshness delay (would need timestamp comparison)
            anomaly.anomaly_type = AnomalyType.FRESHNESS_DELAY

    def emit_anomaly_events(self, anomalies: List[AnomalyResult]):
        """Emit anomaly events via event bus."""
        if not self.event_bus:
            return

        from ..events.events import AnomalyDetected

        for anomaly in anomalies:
            try:
                self.event_bus.emit(
                    AnomalyDetected(
                        event_type="AnomalyDetected",
                        timestamp=datetime.utcnow(),
                        table=anomaly.table_name,
                        column=anomaly.column_name,
                        metric=anomaly.metric_name,
                        anomaly_type=anomaly.anomaly_type.value,
                        expected_value=anomaly.expected_value,
                        actual_value=anomaly.actual_value,
                        severity=anomaly.severity,
                        detection_method=anomaly.detection_method,
                        explanation=anomaly.explanation,
                        metadata=anomaly.metadata,
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to emit anomaly event: {e}")
