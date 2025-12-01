"""
Storage layer for RCA data.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .models import CodeDeployment, PipelineRun, RCAResult

logger = logging.getLogger(__name__)


class RCAStorage:
    """Storage handler for RCA data."""

    def __init__(self, engine: Engine):
        """
        Initialize RCA storage.

        Args:
            engine: SQLAlchemy engine for database connection
        """
        self.engine = engine

    def write_pipeline_run(self, run: PipelineRun) -> None:
        """
        Write a pipeline run to storage.

        Args:
            run: PipelineRun object to store
        """
        with self.engine.connect() as conn:
            # Serialize JSON fields
            affected_tables_json = json.dumps(run.affected_tables) if run.affected_tables else None
            metadata_json = json.dumps(run.metadata) if run.metadata else None

            # Check if run already exists
            check_query = text(
                """
                SELECT run_id FROM baselinr_pipeline_runs
                WHERE run_id = :run_id
                LIMIT 1
            """
            )
            existing = conn.execute(check_query, {"run_id": run.run_id}).fetchone()

            if existing:
                # Update existing run
                update_query = text(
                    """
                    UPDATE baselinr_pipeline_runs
                    SET completed_at = :completed_at,
                        duration_seconds = :duration_seconds,
                        status = :status,
                        output_row_count = :output_row_count,
                        metadata = :metadata
                    WHERE run_id = :run_id
                """
                )
                conn.execute(
                    update_query,
                    {
                        "run_id": run.run_id,
                        "completed_at": run.completed_at,
                        "duration_seconds": run.duration_seconds,
                        "status": run.status,
                        "output_row_count": run.output_row_count,
                        "metadata": metadata_json,
                    },
                )
            else:
                # Insert new run
                insert_query = text(
                    """
                    INSERT INTO baselinr_pipeline_runs (
                        run_id, pipeline_name, pipeline_type, started_at, completed_at,
                        duration_seconds, status, input_row_count, output_row_count,
                        git_commit_sha, git_branch, affected_tables, metadata
                    ) VALUES (
                        :run_id, :pipeline_name, :pipeline_type, :started_at, :completed_at,
                        :duration_seconds, :status, :input_row_count, :output_row_count,
                        :git_commit_sha, :git_branch, :affected_tables, :metadata
                    )
                """
                )
                conn.execute(
                    insert_query,
                    {
                        "run_id": run.run_id,
                        "pipeline_name": run.pipeline_name,
                        "pipeline_type": run.pipeline_type,
                        "started_at": run.started_at,
                        "completed_at": run.completed_at,
                        "duration_seconds": run.duration_seconds,
                        "status": run.status,
                        "input_row_count": run.input_row_count,
                        "output_row_count": run.output_row_count,
                        "git_commit_sha": run.git_commit_sha,
                        "git_branch": run.git_branch,
                        "affected_tables": affected_tables_json,
                        "metadata": metadata_json,
                    },
                )

            conn.commit()
            logger.debug(f"Wrote pipeline run: {run.run_id}")

    def write_code_deployment(self, deployment: CodeDeployment) -> None:
        """
        Write a code deployment to storage.

        Args:
            deployment: CodeDeployment object to store
        """
        with self.engine.connect() as conn:
            # Serialize JSON fields
            changed_files_json = (
                json.dumps(deployment.changed_files) if deployment.changed_files else None
            )
            affected_pipelines_json = (
                json.dumps(deployment.affected_pipelines) if deployment.affected_pipelines else None
            )
            metadata_json = json.dumps(deployment.metadata) if deployment.metadata else None

            # Check if deployment already exists
            check_query = text(
                """
                SELECT deployment_id FROM baselinr_code_deployments
                WHERE deployment_id = :deployment_id
                LIMIT 1
            """
            )
            existing = conn.execute(
                check_query, {"deployment_id": deployment.deployment_id}
            ).fetchone()

            if existing:
                # Update existing deployment
                update_query = text(
                    """
                    UPDATE baselinr_code_deployments
                    SET changed_files = :changed_files,
                        affected_pipelines = :affected_pipelines,
                        metadata = :metadata
                    WHERE deployment_id = :deployment_id
                """
                )
                conn.execute(
                    update_query,
                    {
                        "deployment_id": deployment.deployment_id,
                        "changed_files": changed_files_json,
                        "affected_pipelines": affected_pipelines_json,
                        "metadata": metadata_json,
                    },
                )
            else:
                # Insert new deployment
                insert_query = text(
                    """
                    INSERT INTO baselinr_code_deployments (
                        deployment_id, deployed_at, git_commit_sha, git_branch,
                        changed_files, deployment_type, affected_pipelines, metadata
                    ) VALUES (
                        :deployment_id, :deployed_at, :git_commit_sha, :git_branch,
                        :changed_files, :deployment_type, :affected_pipelines, :metadata
                    )
                """
                )
                conn.execute(
                    insert_query,
                    {
                        "deployment_id": deployment.deployment_id,
                        "deployed_at": deployment.deployed_at,
                        "git_commit_sha": deployment.git_commit_sha,
                        "git_branch": deployment.git_branch,
                        "changed_files": changed_files_json,
                        "deployment_type": deployment.deployment_type,
                        "affected_pipelines": affected_pipelines_json,
                        "metadata": metadata_json,
                    },
                )

            conn.commit()
            logger.debug(f"Wrote code deployment: {deployment.deployment_id}")

    def write_rca_result(self, result: RCAResult) -> None:
        """
        Write RCA result to storage.

        Args:
            result: RCAResult object to store
        """
        with self.engine.connect() as conn:
            # Serialize JSON fields
            probable_causes_json = json.dumps(result.probable_causes)
            impact_json = (
                json.dumps(result.impact_analysis.to_dict()) if result.impact_analysis else None
            )
            metadata_json = json.dumps(result.metadata) if result.metadata else None

            # Check if result already exists
            check_query = text(
                """
                SELECT id FROM baselinr_rca_results
                WHERE anomaly_id = :anomaly_id
                LIMIT 1
            """
            )
            existing = conn.execute(check_query, {"anomaly_id": result.anomaly_id}).fetchone()

            if existing:
                # Update existing result
                update_query = text(
                    """
                    UPDATE baselinr_rca_results
                    SET analyzed_at = :analyzed_at,
                        rca_status = :rca_status,
                        probable_causes = :probable_causes,
                        impact_analysis = :impact_analysis,
                        metadata = :metadata
                    WHERE anomaly_id = :anomaly_id
                """
                )
                conn.execute(
                    update_query,
                    {
                        "anomaly_id": result.anomaly_id,
                        "analyzed_at": result.analyzed_at,
                        "rca_status": result.rca_status,
                        "probable_causes": probable_causes_json,
                        "impact_analysis": impact_json,
                        "metadata": metadata_json,
                    },
                )
            else:
                # Insert new result
                insert_query = text(
                    """
                    INSERT INTO baselinr_rca_results (
                        anomaly_id, database_name, table_name, schema_name,
                        column_name, metric_name, analyzed_at, rca_status,
                        probable_causes, impact_analysis, metadata
                    ) VALUES (
                        :anomaly_id, :database_name, :table_name, :schema_name,
                        :column_name, :metric_name, :analyzed_at, :rca_status,
                        :probable_causes, :impact_analysis, :metadata
                    )
                """
                )
                conn.execute(
                    insert_query,
                    {
                        "anomaly_id": result.anomaly_id,
                        "database_name": result.database_name,
                        "table_name": result.table_name,
                        "schema_name": result.schema_name,
                        "column_name": result.column_name,
                        "metric_name": result.metric_name,
                        "analyzed_at": result.analyzed_at,
                        "rca_status": result.rca_status,
                        "probable_causes": probable_causes_json,
                        "impact_analysis": impact_json,
                        "metadata": metadata_json,
                    },
                )

            conn.commit()
            logger.info(f"Wrote RCA result for anomaly: {result.anomaly_id}")

    def get_pipeline_runs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        pipeline_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[PipelineRun]:
        """
        Query pipeline runs with filters.

        Args:
            start_time: Filter runs after this time
            end_time: Filter runs before this time
            pipeline_name: Filter by pipeline name
            status: Filter by status
            limit: Maximum number of results

        Returns:
            List of PipelineRun objects
        """
        query_parts = ["SELECT * FROM baselinr_pipeline_runs WHERE 1=1"]
        params: Dict[str, Any] = {}

        if start_time:
            query_parts.append("AND started_at >= :start_time")
            params["start_time"] = start_time

        if end_time:
            query_parts.append("AND started_at <= :end_time")
            params["end_time"] = end_time

        if pipeline_name:
            query_parts.append("AND pipeline_name = :pipeline_name")
            params["pipeline_name"] = pipeline_name

        if status:
            query_parts.append("AND status = :status")
            params["status"] = status

        query_parts.append("ORDER BY started_at DESC")
        query_parts.append(f"LIMIT {limit}")

        query = text(" ".join(query_parts))

        with self.engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()

            runs = []
            for row in rows:
                # Parse JSON fields
                affected_tables = json.loads(row[11]) if row[11] else []
                metadata = json.loads(row[12]) if row[12] else {}

                run = PipelineRun(
                    run_id=row[0],
                    pipeline_name=row[1],
                    pipeline_type=row[2],
                    started_at=row[3],
                    completed_at=row[4],
                    duration_seconds=row[5],
                    status=row[6],
                    input_row_count=row[7],
                    output_row_count=row[8],
                    git_commit_sha=row[9],
                    git_branch=row[10],
                    affected_tables=affected_tables,
                    metadata=metadata,
                    created_at=row[13] if len(row) > 13 else None,
                )
                runs.append(run)

            return runs

    def get_code_deployments(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        git_commit_sha: Optional[str] = None,
        limit: int = 100,
    ) -> List[CodeDeployment]:
        """
        Query code deployments with filters.

        Args:
            start_time: Filter deployments after this time
            end_time: Filter deployments before this time
            git_commit_sha: Filter by commit SHA
            limit: Maximum number of results

        Returns:
            List of CodeDeployment objects
        """
        query_parts = ["SELECT * FROM baselinr_code_deployments WHERE 1=1"]
        params: Dict[str, Any] = {}

        if start_time:
            query_parts.append("AND deployed_at >= :start_time")
            params["start_time"] = start_time

        if end_time:
            query_parts.append("AND deployed_at <= :end_time")
            params["end_time"] = end_time

        if git_commit_sha:
            query_parts.append("AND git_commit_sha = :git_commit_sha")
            params["git_commit_sha"] = git_commit_sha

        query_parts.append("ORDER BY deployed_at DESC")
        query_parts.append(f"LIMIT {limit}")

        query = text(" ".join(query_parts))

        with self.engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()

            deployments = []
            for row in rows:
                # Parse JSON fields
                changed_files = json.loads(row[4]) if row[4] else []
                affected_pipelines = json.loads(row[6]) if row[6] else []
                metadata = json.loads(row[7]) if row[7] else {}

                deployment = CodeDeployment(
                    deployment_id=row[0],
                    deployed_at=row[1],
                    git_commit_sha=row[2],
                    git_branch=row[3],
                    changed_files=changed_files,
                    deployment_type=row[5],
                    affected_pipelines=affected_pipelines,
                    metadata=metadata,
                    created_at=row[8] if len(row) > 8 else None,
                )
                deployments.append(deployment)

            return deployments

    def get_rca_result(self, anomaly_id: str) -> Optional[RCAResult]:
        """
        Get RCA result for a specific anomaly.

        Args:
            anomaly_id: Anomaly ID to look up

        Returns:
            RCAResult object or None if not found
        """
        query = text(
            """
            SELECT * FROM baselinr_rca_results
            WHERE anomaly_id = :anomaly_id
            LIMIT 1
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(query, {"anomaly_id": anomaly_id})
            row = result.fetchone()

            if not row:
                return None

            # Parse JSON fields
            # Column order: id(0), anomaly_id(1), database_name(2), table_name(3), schema_name(4),
            # column_name(5), metric_name(6), analyzed_at(7), rca_status(8),
            # probable_causes(9), impact_analysis(10), metadata(11)
            probable_causes = json.loads(row[9]) if row[9] else []
            impact_analysis_dict = json.loads(row[10]) if row[10] else None
            metadata = json.loads(row[11]) if row[11] else {}

            # Reconstruct impact analysis
            from .models import ImpactAnalysis

            impact_analysis = None
            if impact_analysis_dict:
                impact_analysis = ImpactAnalysis(
                    upstream_affected=impact_analysis_dict.get("upstream_affected", []),
                    downstream_affected=impact_analysis_dict.get("downstream_affected", []),
                    blast_radius_score=impact_analysis_dict.get("blast_radius_score", 0.0),
                )

            rca_result = RCAResult(
                anomaly_id=row[1],
                database_name=row[2],
                table_name=row[3],
                schema_name=row[4],
                column_name=row[5],
                metric_name=row[6],
                analyzed_at=row[7],
                rca_status=row[8],
                probable_causes=probable_causes,
                impact_analysis=impact_analysis,
                metadata=metadata,
            )

            return rca_result
