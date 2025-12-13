"""
Storage layer for quality scores.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .models import DataQualityScore

logger = logging.getLogger(__name__)


class QualityScoreStorage:
    """Storage handler for quality scores."""

    def __init__(self, engine: Engine, scores_table: str = "baselinr_quality_scores"):
        """
        Initialize quality score storage.

        Args:
            engine: SQLAlchemy engine for database connection
            scores_table: Name of the scores table
        """
        self.engine = engine
        self.scores_table = scores_table

    def store_score(self, score: DataQualityScore) -> None:
        """
        Store a quality score in the database.

        Args:
            score: DataQualityScore object to store
        """
        with self.engine.connect() as conn:
            insert_query = text(
                f"""
                INSERT INTO {self.scores_table} (
                    table_name, schema_name, run_id,
                    overall_score, completeness_score, validity_score,
                    consistency_score, freshness_score, uniqueness_score,
                    accuracy_score, status, total_issues, critical_issues,
                    warnings, calculated_at, period_start, period_end
                ) VALUES (
                    :table_name, :schema_name, :run_id,
                    :overall_score, :completeness_score, :validity_score,
                    :consistency_score, :freshness_score, :uniqueness_score,
                    :accuracy_score, :status, :total_issues, :critical_issues,
                    :warnings, :calculated_at, :period_start, :period_end
                )
            """
            )

            conn.execute(
                insert_query,
                {
                    "table_name": score.table_name,
                    "schema_name": score.schema_name,
                    "run_id": score.run_id,
                    "overall_score": score.overall_score,
                    "completeness_score": score.completeness_score,
                    "validity_score": score.validity_score,
                    "consistency_score": score.consistency_score,
                    "freshness_score": score.freshness_score,
                    "uniqueness_score": score.uniqueness_score,
                    "accuracy_score": score.accuracy_score,
                    "status": score.status,
                    "total_issues": score.total_issues,
                    "critical_issues": score.critical_issues,
                    "warnings": score.warnings,
                    "calculated_at": score.calculated_at,
                    "period_start": score.period_start,
                    "period_end": score.period_end,
                },
            )

            conn.commit()
            logger.debug(
                f"Stored quality score for {score.table_name} "
                f"(schema: {score.schema_name}): {score.overall_score:.1f}"
            )

    def get_latest_score(
        self, table_name: str, schema_name: Optional[str] = None
    ) -> Optional[DataQualityScore]:
        """
        Get the most recent score for a table.

        Args:
            table_name: Name of the table
            schema_name: Optional schema name

        Returns:
            DataQualityScore if found, None otherwise
        """
        conditions = ["table_name = :table_name"]
        params: Dict[str, Any] = {"table_name": table_name}

        if schema_name:
            conditions.append("schema_name = :schema_name")
            params["schema_name"] = schema_name
        else:
            conditions.append("schema_name IS NULL")

        where_clause = " AND ".join(conditions)

        query = text(
            f"""
            SELECT table_name, schema_name, run_id,
                   overall_score, completeness_score, validity_score,
                   consistency_score, freshness_score, uniqueness_score,
                   accuracy_score, status, total_issues, critical_issues,
                   warnings, calculated_at, period_start, period_end
            FROM {self.scores_table}
            WHERE {where_clause}
            ORDER BY calculated_at DESC
            LIMIT 1
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(query, params).fetchone()

            if not result:
                return None

            return DataQualityScore(
                table_name=result[0],
                schema_name=result[1],
                run_id=result[2],
                overall_score=float(result[3]),
                completeness_score=float(result[4]),
                validity_score=float(result[5]),
                consistency_score=float(result[6]),
                freshness_score=float(result[7]),
                uniqueness_score=float(result[8]),
                accuracy_score=float(result[9]),
                status=result[10],
                total_issues=int(result[11]),
                critical_issues=int(result[12]),
                warnings=int(result[13]),
                calculated_at=result[14],
                period_start=result[15],
                period_end=result[16],
            )

    def get_score_history(
        self,
        table_name: str,
        schema_name: Optional[str] = None,
        days: int = 30,
    ) -> List[DataQualityScore]:
        """
        Get historical scores for a table.

        Args:
            table_name: Name of the table
            schema_name: Optional schema name
            days: Number of days to look back

        Returns:
            List of DataQualityScore objects, ordered by calculated_at DESC
        """
        conditions = ["table_name = :table_name"]
        params: Dict[str, Any] = {"table_name": table_name}

        if schema_name:
            conditions.append("schema_name = :schema_name")
            params["schema_name"] = schema_name
        else:
            conditions.append("schema_name IS NULL")

        # Add time filter
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        conditions.append("calculated_at >= :cutoff_date")
        params["cutoff_date"] = cutoff_date

        where_clause = " AND ".join(conditions)

        query = text(
            f"""
            SELECT table_name, schema_name, run_id,
                   overall_score, completeness_score, validity_score,
                   consistency_score, freshness_score, uniqueness_score,
                   accuracy_score, status, total_issues, critical_issues,
                   warnings, calculated_at, period_start, period_end
            FROM {self.scores_table}
            WHERE {where_clause}
            ORDER BY calculated_at DESC
        """
        )

        scores = []
        with self.engine.connect() as conn:
            results = conn.execute(query, params).fetchall()

            for row in results:
                scores.append(
                    DataQualityScore(
                        table_name=row[0],
                        schema_name=row[1],
                        run_id=row[2],
                        overall_score=float(row[3]),
                        completeness_score=float(row[4]),
                        validity_score=float(row[5]),
                        consistency_score=float(row[6]),
                        freshness_score=float(row[7]),
                        uniqueness_score=float(row[8]),
                        accuracy_score=float(row[9]),
                        status=row[10],
                        total_issues=int(row[11]),
                        critical_issues=int(row[12]),
                        warnings=int(row[13]),
                        calculated_at=row[14],
                        period_start=row[15],
                        period_end=row[16],
                    )
                )

        return scores
