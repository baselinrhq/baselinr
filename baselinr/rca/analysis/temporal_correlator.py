"""
Temporal correlation analyzer for RCA.

Analyzes events in a time window around an anomaly to find
temporally proximate causes.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine

from ..models import CodeChangeCause, PipelineCause

logger = logging.getLogger(__name__)


class TemporalCorrelator:
    """
    Analyzes temporal correlation between anomalies and potential causes.

    Finds pipeline runs, deployments, and other events that occurred
    near the time of an anomaly and scores them by proximity.
    """

    def __init__(
        self,
        engine: Engine,
        lookback_window_hours: int = 24,
        max_causes_to_return: int = 10,
    ):
        """
        Initialize temporal correlator.

        Args:
            engine: SQLAlchemy engine for querying
            lookback_window_hours: How far back to look for causes
            max_causes_to_return: Maximum number of causes to return
        """
        self.engine = engine
        self.lookback_window_hours = lookback_window_hours
        self.max_causes_to_return = max_causes_to_return

    def find_correlated_pipeline_runs(
        self,
        anomaly_timestamp: datetime,
        table_name: str,
        database_name: Optional[str] = None,
        schema_name: Optional[str] = None,
    ) -> List[PipelineCause]:
        """
        Find pipeline runs correlated with an anomaly.

        Args:
            anomaly_timestamp: When the anomaly occurred
            table_name: Name of affected table
            schema_name: Schema name (if applicable)

        Returns:
            List of PipelineCause objects scored by temporal proximity
        """
        # Calculate time window
        start_time = anomaly_timestamp - timedelta(hours=self.lookback_window_hours)
        end_time = anomaly_timestamp

        # Query pipeline runs in window
        query = text(
            """
            SELECT run_id, pipeline_name, pipeline_type, started_at, completed_at,
                   status, duration_seconds, affected_tables, metadata
            FROM baselinr_pipeline_runs
            WHERE started_at >= :start_time
            AND started_at <= :end_time
            ORDER BY started_at DESC
            LIMIT :limit
        """
        )

        causes = []

        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    query,
                    {
                        "start_time": start_time,
                        "end_time": end_time,
                        "limit": self.max_causes_to_return * 2,  # Get more for filtering
                    },
                )
                rows = result.fetchall()

                for row in rows:
                    run_id = row[0]
                    pipeline_name = row[1]
                    pipeline_type = row[2]
                    started_at = row[3]
                    # completed_at = row[4]  # Not used in scoring
                    status = row[5]
                    duration_seconds = row[6]
                    affected_tables_json = row[7]
                    # metadata_json = row[8]  # Not used

                    # Parse JSON fields
                    import json

                    affected_tables = (
                        json.loads(affected_tables_json) if affected_tables_json else []
                    )

                    # Ensure started_at is a datetime object
                    if isinstance(started_at, str):
                        try:
                            started_at = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                        except (ValueError, AttributeError):
                            # Fallback: try parsing common formats
                            from datetime import datetime as dt

                            try:
                                started_at = dt.strptime(started_at, "%Y-%m-%d %H:%M:%S")
                            except ValueError:
                                started_at = datetime.utcnow()  # Fallback

                    # Calculate temporal proximity score (0-1, higher is closer)
                    proximity_score = self._calculate_temporal_proximity(
                        started_at, anomaly_timestamp
                    )

                    # Check if this pipeline affected the anomalous table
                    table_relevance = self._calculate_table_relevance(table_name, affected_tables)

                    # Combine scores
                    confidence = (proximity_score * 0.6) + (table_relevance * 0.4)

                    # Boost confidence for failed runs
                    if status == "failed":
                        confidence = min(1.0, confidence * 1.5)
                        cause_type = "pipeline_failure"
                    elif status == "success" and duration_seconds:
                        # Check for degradation (unusually long duration)
                        # TODO: Compare with historical average
                        cause_type = "pipeline_degradation"
                    else:
                        cause_type = "data_quality"

                    # Build description
                    time_diff = (anomaly_timestamp - started_at).total_seconds() / 60
                    description = (
                        f"Pipeline '{pipeline_name}' ({pipeline_type}) {status} "
                        f"{time_diff:.1f} minutes before anomaly"
                    )

                    if status == "failed":
                        description += ". Failure may have caused data quality issues."

                    # Suggested action
                    if status == "failed":
                        suggested_action = f"Check logs for pipeline '{pipeline_name}' run {run_id}"
                    else:
                        suggested_action = (
                            f"Review changes in pipeline '{pipeline_name}' "
                            f"that may affect data quality"
                        )

                    cause = PipelineCause(
                        cause_type=cause_type,
                        cause_id=run_id,
                        confidence_score=confidence,
                        description=description,
                        affected_assets=affected_tables,
                        suggested_action=suggested_action,
                        evidence={
                            "temporal_proximity": proximity_score,
                            "table_relevance": table_relevance,
                            "time_before_anomaly_minutes": time_diff,
                            "pipeline_status": status,
                            "pipeline_type": pipeline_type,
                            "duration_seconds": duration_seconds,
                        },
                    )

                    causes.append(cause)

        except Exception as e:
            logger.error(f"Error finding correlated pipeline runs: {e}")

        # Sort by confidence and limit
        causes.sort(key=lambda c: c.confidence_score, reverse=True)
        return causes[: self.max_causes_to_return]

    def find_correlated_deployments(
        self,
        anomaly_timestamp: datetime,
        table_name: str,
        database_name: Optional[str] = None,
        schema_name: Optional[str] = None,
    ) -> List[CodeChangeCause]:
        """
        Find code deployments correlated with an anomaly.

        Args:
            anomaly_timestamp: When the anomaly occurred
            table_name: Name of affected table
            schema_name: Schema name (if applicable)

        Returns:
            List of CodeChangeCause objects scored by temporal proximity
        """
        # Calculate time window
        start_time = anomaly_timestamp - timedelta(hours=self.lookback_window_hours)
        end_time = anomaly_timestamp

        # Query deployments in window
        query = text(
            """
            SELECT deployment_id, deployed_at, git_commit_sha, git_branch,
                   deployment_type, affected_pipelines, changed_files, metadata
            FROM baselinr_code_deployments
            WHERE deployed_at >= :start_time
            AND deployed_at <= :end_time
            ORDER BY deployed_at DESC
            LIMIT :limit
        """
        )

        causes = []

        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    query,
                    {
                        "start_time": start_time,
                        "end_time": end_time,
                        "limit": self.max_causes_to_return * 2,
                    },
                )
                rows = result.fetchall()

                for row in rows:
                    deployment_id = row[0]
                    deployed_at = row[1]
                    git_commit_sha = row[2]
                    git_branch = row[3]
                    deployment_type = row[4]
                    affected_pipelines_json = row[5]
                    changed_files_json = row[6]
                    # metadata_json = row[7]  # Not used

                    # Parse JSON fields
                    import json

                    affected_pipelines = (
                        json.loads(affected_pipelines_json) if affected_pipelines_json else []
                    )
                    changed_files = json.loads(changed_files_json) if changed_files_json else []

                    # Ensure deployed_at is a datetime object
                    if isinstance(deployed_at, str):
                        try:
                            deployed_at = datetime.fromisoformat(deployed_at.replace("Z", "+00:00"))
                        except (ValueError, AttributeError):
                            # Fallback: try parsing common formats
                            from datetime import datetime as dt

                            try:
                                deployed_at = dt.strptime(deployed_at, "%Y-%m-%d %H:%M:%S")
                            except ValueError:
                                deployed_at = datetime.utcnow()  # Fallback

                    # Calculate temporal proximity score
                    proximity_score = self._calculate_temporal_proximity(
                        deployed_at, anomaly_timestamp
                    )

                    # Check if deployment affects data pipelines
                    pipeline_relevance = 0.5 if affected_pipelines else 0.3

                    # Schema changes are higher impact
                    if deployment_type == "schema":
                        pipeline_relevance = min(1.0, pipeline_relevance * 1.5)

                    confidence = (proximity_score * 0.7) + (pipeline_relevance * 0.3)

                    # Build description
                    time_diff = (anomaly_timestamp - deployed_at).total_seconds() / 60
                    description = (
                        f"Code deployment ({deployment_type}) to branch '{git_branch}' "
                        f"{time_diff:.1f} minutes before anomaly"
                    )

                    if affected_pipelines:
                        description += f". Affected pipelines: {', '.join(affected_pipelines[:3])}"

                    # Suggested action
                    if git_commit_sha:
                        suggested_action = (
                            f"Review commit {git_commit_sha[:8]} for changes "
                            f"that may affect data quality"
                        )
                    else:
                        suggested_action = "Review recent code changes"

                    cause = CodeChangeCause(
                        cause_type="code_change",
                        cause_id=deployment_id,
                        confidence_score=confidence,
                        description=description,
                        affected_assets=affected_pipelines,
                        suggested_action=suggested_action,
                        evidence={
                            "temporal_proximity": proximity_score,
                            "pipeline_relevance": pipeline_relevance,
                            "time_before_anomaly_minutes": time_diff,
                            "deployment_type": deployment_type,
                            "git_commit_sha": git_commit_sha,
                            "git_branch": git_branch,
                            "changed_files_count": len(changed_files),
                        },
                    )

                    causes.append(cause)

        except Exception as e:
            logger.error(f"Error finding correlated deployments: {e}")

        # Sort by confidence and limit
        causes.sort(key=lambda c: c.confidence_score, reverse=True)
        return causes[: self.max_causes_to_return]

    def _calculate_temporal_proximity(self, event_time: datetime, anomaly_time: datetime) -> float:
        """
        Calculate temporal proximity score (0-1).

        Closer events get higher scores. Uses exponential decay.

        Args:
            event_time: When the event occurred
            anomaly_time: When the anomaly occurred

        Returns:
            Score between 0 and 1
        """
        # Time difference in hours
        time_diff_hours = abs((anomaly_time - event_time).total_seconds() / 3600)

        if time_diff_hours > self.lookback_window_hours:
            return 0.0

        # Exponential decay with half-life of 4 hours
        import math

        half_life = 4.0
        decay_rate = math.log(2) / half_life
        proximity = math.exp(-decay_rate * time_diff_hours)

        return proximity

    def _calculate_table_relevance(self, target_table: str, affected_tables: List[str]) -> float:
        """
        Calculate how relevant a pipeline is to a specific table.

        Args:
            target_table: The table with the anomaly
            affected_tables: Tables affected by the pipeline

        Returns:
            Relevance score between 0 and 1
        """
        if not affected_tables:
            return 0.3  # Unknown relevance

        # Exact match
        if target_table in affected_tables:
            return 1.0

        # Partial match (case insensitive)
        target_lower = target_table.lower()
        for table in affected_tables:
            if target_lower in table.lower() or table.lower() in target_lower:
                return 0.7

        # No match but pipeline has affected tables
        return 0.4

    def find_all_correlated_events(
        self,
        anomaly_timestamp: datetime,
        table_name: str,
        database_name: Optional[str] = None,
        schema_name: Optional[str] = None,
    ) -> Tuple[List[PipelineCause], List[CodeChangeCause]]:
        """
        Find all correlated events (pipelines and deployments).

        Args:
            anomaly_timestamp: When the anomaly occurred
            table_name: Name of affected table
            database_name: Database name (if applicable)
            schema_name: Schema name (if applicable)

        Returns:
            Tuple of (pipeline_causes, deployment_causes)
        """
        pipeline_causes = self.find_correlated_pipeline_runs(
            anomaly_timestamp, table_name, database_name, schema_name
        )

        deployment_causes = self.find_correlated_deployments(
            anomaly_timestamp, table_name, database_name, schema_name
        )

        return pipeline_causes, deployment_causes
