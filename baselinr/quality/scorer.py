"""
Quality scoring engine for Baselinr.

Calculates comprehensive data quality scores by combining
validation results, drift events, profiling metrics, and anomaly detection.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from ..config.schema import QualityScoringConfig
from .models import DataQualityScore, ScoreStatus

logger = logging.getLogger(__name__)


class QualityScorer:
    """Calculates data quality scores for tables."""

    def __init__(
        self,
        engine: Engine,
        config: QualityScoringConfig,
        results_table: str = "baselinr_results",
        validation_table: str = "baselinr_validation_results",
        events_table: str = "baselinr_events",
        runs_table: str = "baselinr_runs",
    ):
        """
        Initialize quality scorer.

        Args:
            engine: SQLAlchemy engine for database connection
            config: Quality scoring configuration
            results_table: Name of the profiling results table
            validation_table: Name of the validation results table
            events_table: Name of the events table
            runs_table: Name of the runs table
        """
        self.engine = engine
        self.config = config
        self.results_table = results_table
        self.validation_table = validation_table
        self.events_table = events_table
        self.runs_table = runs_table

    def calculate_table_score(
        self,
        table_name: str,
        schema_name: Optional[str] = None,
        run_id: Optional[str] = None,
        period_days: int = 7,
    ) -> DataQualityScore:
        """
        Calculate quality score for a table.

        Args:
            table_name: Name of the table
            schema_name: Optional schema name
            run_id: Optional run ID to associate with the score
            period_days: Number of days to look back for data

        Returns:
            DataQualityScore object
        """
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=period_days)

        # Calculate component scores
        completeness_score = self._calculate_completeness_score(
            table_name, schema_name, period_start, period_end
        )
        validity_score = self._calculate_validity_score(
            table_name, schema_name, period_start, period_end
        )
        consistency_score = self._calculate_consistency_score(
            table_name, schema_name, period_start, period_end
        )
        freshness_score = self._calculate_freshness_score(table_name, schema_name)
        uniqueness_score = self._calculate_uniqueness_score(
            table_name, schema_name, period_start, period_end
        )
        accuracy_score = self._calculate_accuracy_score(
            table_name, schema_name, period_start, period_end
        )

        # Calculate overall score using weighted average
        weights = self.config.weights
        overall_score = (
            completeness_score * weights.completeness
            + validity_score * weights.validity
            + consistency_score * weights.consistency
            + freshness_score * weights.freshness
            + uniqueness_score * weights.uniqueness
            + accuracy_score * weights.accuracy
        ) / 100.0

        # Determine status
        thresholds = self.config.thresholds
        if overall_score >= thresholds.healthy:
            status = ScoreStatus.HEALTHY.value
        elif overall_score >= thresholds.warning:
            status = ScoreStatus.WARNING.value
        else:
            status = ScoreStatus.CRITICAL.value

        # Count issues
        total_issues, critical_issues, warnings = self._count_issues(
            table_name, schema_name, period_start, period_end
        )

        return DataQualityScore(
            overall_score=round(overall_score, 2),
            completeness_score=round(completeness_score, 2),
            validity_score=round(validity_score, 2),
            consistency_score=round(consistency_score, 2),
            freshness_score=round(freshness_score, 2),
            uniqueness_score=round(uniqueness_score, 2),
            accuracy_score=round(accuracy_score, 2),
            status=status,
            total_issues=total_issues,
            critical_issues=critical_issues,
            warnings=warnings,
            table_name=table_name,
            schema_name=schema_name,
            run_id=run_id,
            calculated_at=period_end,
            period_start=period_start,
            period_end=period_end,
        )

    def _calculate_completeness_score(
        self,
        table_name: str,
        schema_name: Optional[str],
        period_start: datetime,
        period_end: datetime,
    ) -> float:
        """Calculate completeness score based on null ratios."""
        conditions = ["dataset_name = :table_name"]
        params: Dict[str, Any] = {"table_name": table_name}

        if schema_name:
            conditions.append("schema_name = :schema_name")
            params["schema_name"] = schema_name
        else:
            conditions.append("schema_name IS NULL")

        conditions.append("metric_name = 'null_ratio'")
        conditions.append("profiled_at >= :period_start")
        conditions.append("profiled_at <= :period_end")
        params["period_start"] = period_start
        params["period_end"] = period_end

        where_clause = " AND ".join(conditions)

        query = text(
            f"""
            SELECT AVG(CAST(metric_value AS FLOAT))
            FROM {self.results_table}
            WHERE {where_clause}
        """
        )

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, params).fetchone()
                if result and result[0] is not None:
                    avg_null_ratio = float(result[0])
                    # Convert null ratio (0-1) to completeness score (0-100)
                    # Lower null ratio = higher completeness
                    completeness_score = max(0.0, min(100.0, (1.0 - avg_null_ratio) * 100.0))
                    return completeness_score
        except Exception as e:
            logger.warning(f"Error calculating completeness score: {e}")

        # Default: assume good completeness if no data
        return 100.0

    def _calculate_validity_score(
        self,
        table_name: str,
        schema_name: Optional[str],
        period_start: datetime,
        period_end: datetime,
    ) -> float:
        """Calculate validity score based on validation rule pass rate."""
        conditions = ["table_name = :table_name"]
        params: Dict[str, Any] = {"table_name": table_name}

        if schema_name:
            conditions.append("schema_name = :schema_name")
            params["schema_name"] = schema_name
        else:
            conditions.append("schema_name IS NULL")

        conditions.append("validated_at >= :period_start")
        conditions.append("validated_at <= :period_end")
        params["period_start"] = period_start
        params["period_end"] = period_end

        where_clause = " AND ".join(conditions)

        query = text(
            f"""
            SELECT
                COUNT(*) as total_rules,
                SUM(CASE WHEN passed = TRUE THEN 1 ELSE 0 END) as passed_rules
            FROM {self.validation_table}
            WHERE {where_clause}
        """
        )

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, params).fetchone()
                if result and result[0] and result[0] > 0:
                    total_rules = int(result[0])
                    passed_rules = int(result[1]) if result[1] else 0
                    validity_score = (passed_rules / total_rules) * 100.0
                    return max(0.0, min(100.0, validity_score))
        except Exception as e:
            logger.warning(f"Error calculating validity score: {e}")

        # Default: assume perfect validity if no validation rules
        return 100.0

    def _calculate_consistency_score(
        self,
        table_name: str,
        schema_name: Optional[str],
        period_start: datetime,
        period_end: datetime,
    ) -> float:
        """Calculate consistency score based on drift events and schema stability."""
        conditions = ["table_name = :table_name"]
        params: Dict[str, Any] = {"table_name": table_name}

        conditions.append("event_type = 'drift_detected'")
        conditions.append("timestamp >= :period_start")
        conditions.append("timestamp <= :period_end")
        params["period_start"] = period_start
        params["period_end"] = period_end

        where_clause = " AND ".join(conditions)

        query = text(
            f"""
            SELECT drift_severity, COUNT(*) as count
            FROM {self.events_table}
            WHERE {where_clause}
            GROUP BY drift_severity
        """
        )

        # Severity weights
        severity_weights = {"high": 10.0, "medium": 5.0, "low": 2.0}

        drift_penalty = 0.0
        try:
            with self.engine.connect() as conn:
                results = conn.execute(query, params).fetchall()
                for row in results:
                    severity = str(row[0]).lower() if row[0] else "low"
                    count = int(row[1])
                    weight = severity_weights.get(severity, 2.0)
                    drift_penalty += weight * count
        except Exception as e:
            logger.warning(f"Error calculating consistency score: {e}")

        # Get schema stability from profiling results (column_stability_score)
        schema_stability = 1.0
        try:
            stability_query = text(
                f"""
                SELECT AVG(CAST(metric_value AS FLOAT))
                FROM {self.results_table}
                WHERE dataset_name = :table_name
                  AND metric_name = 'column_stability_score'
                  AND profiled_at >= :period_start
                  AND profiled_at <= :period_end
            """
            )
            with self.engine.connect() as conn:
                result = conn.execute(
                    stability_query,
                    {
                        "table_name": table_name,
                        "period_start": period_start,
                        "period_end": period_end,
                    },
                ).fetchone()
                if result and result[0] is not None:
                    schema_stability = float(result[0])
        except Exception as e:
            logger.debug(f"Could not get schema stability: {e}")

        # Calculate consistency: max(0, 100 - drift_penalty) * schema_stability
        consistency_score = max(0.0, min(100.0, (100.0 - drift_penalty) * schema_stability))
        return consistency_score

    def _calculate_freshness_score(self, table_name: str, schema_name: Optional[str]) -> float:
        """Calculate freshness score based on time since last profile."""
        conditions = ["dataset_name = :table_name"]
        params: Dict[str, Any] = {"table_name": table_name}

        if schema_name:
            conditions.append("schema_name = :schema_name")
            params["schema_name"] = schema_name
        else:
            conditions.append("schema_name IS NULL")

        where_clause = " AND ".join(conditions)

        query = text(
            f"""
            SELECT MAX(profiled_at) as last_profiled
            FROM {self.runs_table}
            WHERE {where_clause}
        """
        )

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, params).fetchone()
                if result and result[0]:
                    last_profiled = result[0]
                    if isinstance(last_profiled, str):
                        last_profiled = datetime.fromisoformat(last_profiled.replace("Z", "+00:00"))
                    elif not isinstance(last_profiled, datetime):
                        return 0.0

                    hours_since_update = (
                        datetime.utcnow() - last_profiled
                    ).total_seconds() / 3600.0

                    freshness = self.config.freshness
                    if hours_since_update <= freshness.excellent:
                        return 100.0
                    elif hours_since_update <= freshness.good:
                        return 80.0
                    elif hours_since_update <= freshness.acceptable:
                        return 60.0
                    else:
                        # Linear decay after acceptable threshold
                        decay_rate = 10.0 / 24.0  # 10 points per day
                        hours_over = hours_since_update - freshness.acceptable
                        score = 60.0 - (hours_over * decay_rate)
                        return max(0.0, score)
        except Exception as e:
            logger.warning(f"Error calculating freshness score: {e}")

        # Default: assume stale if no data
        return 0.0

    def _calculate_uniqueness_score(
        self,
        table_name: str,
        schema_name: Optional[str],
        period_start: datetime,
        period_end: datetime,
    ) -> float:
        """Calculate uniqueness score based on unique ratios."""
        conditions = ["dataset_name = :table_name"]
        params: Dict[str, Any] = {"table_name": table_name}

        if schema_name:
            conditions.append("schema_name = :schema_name")
            params["schema_name"] = schema_name
        else:
            conditions.append("schema_name IS NULL")

        conditions.append("metric_name = 'unique_ratio'")
        conditions.append("profiled_at >= :period_start")
        conditions.append("profiled_at <= :period_end")
        params["period_start"] = period_start
        params["period_end"] = period_end

        where_clause = " AND ".join(conditions)

        query = text(
            f"""
            SELECT AVG(CAST(metric_value AS FLOAT))
            FROM {self.results_table}
            WHERE {where_clause}
        """
        )

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, params).fetchone()
                if result and result[0] is not None:
                    avg_unique_ratio = float(result[0])
                    # Convert unique ratio (0-1) to uniqueness score (0-100)
                    uniqueness_score = avg_unique_ratio * 100.0
                    return max(0.0, min(100.0, uniqueness_score))
        except Exception as e:
            logger.warning(f"Error calculating uniqueness score: {e}")

        # Default: assume good uniqueness if no data
        return 100.0

    def _calculate_accuracy_score(
        self,
        table_name: str,
        schema_name: Optional[str],
        period_start: datetime,
        period_end: datetime,
    ) -> float:
        """Calculate accuracy score based on anomaly detection."""
        conditions = ["table_name = :table_name"]
        params: Dict[str, Any] = {"table_name": table_name}

        conditions.append("event_type = 'AnomalyDetected'")
        conditions.append("timestamp >= :period_start")
        conditions.append("timestamp <= :period_end")
        params["period_start"] = period_start
        params["period_end"] = period_end

        where_clause = " AND ".join(conditions)

        query = text(
            f"""
            SELECT COUNT(*) as anomaly_count
            FROM {self.events_table}
            WHERE {where_clause}
        """
        )

        anomaly_penalty = 0.0
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, params).fetchone()
                if result and result[0]:
                    anomaly_count = int(result[0])
                    # 5 points per anomaly, max 100 points penalty
                    anomaly_penalty = min(100.0, anomaly_count * 5.0)
        except Exception as e:
            logger.warning(f"Error calculating accuracy score: {e}")

        # Calculate accuracy: 100 - anomaly_penalty
        accuracy_score = max(0.0, 100.0 - anomaly_penalty)
        return accuracy_score

    def _count_issues(
        self,
        table_name: str,
        schema_name: Optional[str],
        period_start: datetime,
        period_end: datetime,
    ) -> tuple[int, int, int]:
        """
        Count total issues, critical issues, and warnings.

        Returns:
            Tuple of (total_issues, critical_issues, warnings)
        """
        total_issues = 0
        critical_issues = 0
        warnings = 0

        # Count validation failures
        try:
            validation_conditions = ["table_name = :table_name", "passed = FALSE"]
            validation_params: Dict[str, Any] = {"table_name": table_name}

            if schema_name:
                validation_conditions.append("schema_name = :schema_name")
                validation_params["schema_name"] = schema_name
            else:
                validation_conditions.append("schema_name IS NULL")

            validation_conditions.append("validated_at >= :period_start")
            validation_conditions.append("validated_at <= :period_end")
            validation_params["period_start"] = period_start
            validation_params["period_end"] = period_end

            validation_where_clause = " AND ".join(validation_conditions)

            query = text(
                f"""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END) as critical,
                    SUM(CASE WHEN severity IN ('medium', 'low') THEN 1 ELSE 0 END) as warning
                FROM {self.validation_table}
                WHERE {validation_where_clause}
            """
            )

            with self.engine.connect() as conn:
                result = conn.execute(query, validation_params).fetchone()
                if result:
                    total_issues += int(result[0]) if result[0] else 0
                    critical_issues += int(result[1]) if result[1] else 0
                    warnings += int(result[2]) if result[2] else 0
        except Exception as e:
            logger.debug(f"Error counting validation issues: {e}")

        # Count high-severity drift events
        try:
            drift_conditions = [
                "table_name = :table_name",
                "event_type = 'drift_detected'",
                "drift_severity = 'high'",
            ]
            drift_params: Dict[str, Any] = {"table_name": table_name}

            drift_conditions.append("timestamp >= :period_start")
            drift_conditions.append("timestamp <= :period_end")
            drift_params["period_start"] = period_start
            drift_params["period_end"] = period_end

            drift_where_clause = " AND ".join(drift_conditions)

            query = text(
                f"""
                SELECT COUNT(*) as count
                FROM {self.events_table}
                WHERE {drift_where_clause}
            """
            )

            with self.engine.connect() as conn:
                result = conn.execute(query, drift_params).fetchone()
                if result and result[0]:
                    critical_issues += int(result[0])
                    total_issues += int(result[0])
        except Exception as e:
            logger.debug(f"Error counting drift issues: {e}")

        return (total_issues, critical_issues, warnings)
