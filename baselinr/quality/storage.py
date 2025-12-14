"""
Storage layer for quality scores.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .models import ColumnQualityScore, DataQualityScore

logger = logging.getLogger(__name__)


class QualityScoreStorage:
    """Storage handler for quality scores."""

    def __init__(
        self,
        engine: Engine,
        scores_table: str = "baselinr_quality_scores",
        cache_ttl_minutes: int = 5,
    ):
        """
        Initialize quality score storage.

        Args:
            engine: SQLAlchemy engine for database connection
            scores_table: Name of the scores table
            cache_ttl_minutes: Cache TTL in minutes (default: 5)
        """
        self.engine = engine
        self.scores_table = scores_table
        self._cache: Dict[Tuple[str, Optional[str]], Tuple[DataQualityScore, datetime]] = {}
        self._cache_ttl = timedelta(minutes=cache_ttl_minutes)

    def store_score(self, score: DataQualityScore) -> None:
        """
        Store a quality score in the database.

        Args:
            score: DataQualityScore object to store
        """
        # Invalidate cache for this table
        cache_key = (score.table_name, score.schema_name)
        if cache_key in self._cache:
            del self._cache[cache_key]
            logger.debug(f"Invalidated cache for {score.table_name}")

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
            schema_name: Optional schema name. If None, will try to find score
                        regardless of schema (matches any schema or NULL)

        Returns:
            DataQualityScore if found, None otherwise
        """
        # Check cache first
        cache_key = (table_name, schema_name)
        if cache_key in self._cache:
            cached_score, cached_time = self._cache[cache_key]
            age = datetime.utcnow() - cached_time
            if age < self._cache_ttl:
                logger.debug(f"Cache hit for {table_name}")
                return cached_score
            else:
                # Cache expired, remove it
                del self._cache[cache_key]
                logger.debug(f"Cache expired for {table_name}")

        conditions = ["table_name = :table_name"]
        params: Dict[str, Any] = {"table_name": table_name}

        if schema_name:
            conditions.append("schema_name = :schema_name")
            params["schema_name"] = schema_name
        # If schema_name is None, don't filter by schema - match any schema or NULL
        # This allows finding scores even when schema is not known

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Query optimized with index hint:
        # should have index on (table_name, schema_name, calculated_at)
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

            score = DataQualityScore(
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

            # Cache the result
            self._cache[cache_key] = (score, datetime.utcnow())
            logger.debug(f"Cached score for {table_name}")

            return score

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

    def query_scores_by_schema(self, schema_name: str) -> List[DataQualityScore]:
        """
        Get all latest scores for tables in a schema.

        Args:
            schema_name: Name of the schema

        Returns:
            List of DataQualityScore objects (latest score per table)
        """
        # Optimized query: uses subquery to get latest score per table
        # Index hint: should have index on (schema_name, table_name, calculated_at)
        query = text(
            f"""
            SELECT s1.table_name, s1.schema_name, s1.run_id,
                   s1.overall_score, s1.completeness_score, s1.validity_score,
                   s1.consistency_score, s1.freshness_score, s1.uniqueness_score,
                   s1.accuracy_score, s1.status, s1.total_issues, s1.critical_issues,
                   s1.warnings, s1.calculated_at, s1.period_start, s1.period_end
            FROM {self.scores_table} s1
            INNER JOIN (
                SELECT table_name, schema_name, MAX(calculated_at) as max_calculated_at
                FROM {self.scores_table}
                WHERE schema_name = :schema_name
                GROUP BY table_name, schema_name
            ) s2 ON s1.table_name = s2.table_name
                AND s1.schema_name = s2.schema_name
                AND s1.calculated_at = s2.max_calculated_at
            WHERE s1.schema_name = :schema_name
            ORDER BY s1.table_name
            """
        )

        scores = []
        with self.engine.connect() as conn:
            results = conn.execute(query, {"schema_name": schema_name}).fetchall()

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

    def query_all_latest_scores(self, schema_name: Optional[str] = None) -> List[DataQualityScore]:
        """
        Get latest score for all tables, optionally filtered by schema.

        Args:
            schema_name: Optional schema name to filter by

        Returns:
            List of DataQualityScore objects (latest score per table)
        """
        if schema_name:
            # Filter by schema
            query = text(
                f"""
                SELECT s1.table_name, s1.schema_name, s1.run_id,
                       s1.overall_score, s1.completeness_score, s1.validity_score,
                       s1.consistency_score, s1.freshness_score, s1.uniqueness_score,
                       s1.accuracy_score, s1.status, s1.total_issues, s1.critical_issues,
                       s1.warnings, s1.calculated_at, s1.period_start, s1.period_end
                FROM {self.scores_table} s1
                INNER JOIN (
                    SELECT table_name, schema_name, MAX(calculated_at) as max_calculated_at
                    FROM {self.scores_table}
                    WHERE schema_name = :schema_name
                    GROUP BY table_name, schema_name
                ) s2 ON s1.table_name = s2.table_name
                    AND s1.schema_name = s2.schema_name
                    AND s1.calculated_at = s2.max_calculated_at
                WHERE s1.schema_name = :schema_name
                ORDER BY s1.schema_name, s1.table_name
            """
            )
            params = {"schema_name": schema_name}
        else:
            # All schemas
            query = text(
                f"""
                SELECT s1.table_name, s1.schema_name, s1.run_id,
                       s1.overall_score, s1.completeness_score, s1.validity_score,
                       s1.consistency_score, s1.freshness_score, s1.uniqueness_score,
                       s1.accuracy_score, s1.status, s1.total_issues, s1.critical_issues,
                       s1.warnings, s1.calculated_at, s1.period_start, s1.period_end
                FROM {self.scores_table} s1
                INNER JOIN (
                    SELECT table_name, schema_name, MAX(calculated_at) as max_calculated_at
                    FROM {self.scores_table}
                    GROUP BY table_name, schema_name
                ) s2 ON s1.table_name = s2.table_name
                    AND (
                        s1.schema_name = s2.schema_name
                        OR (s1.schema_name IS NULL AND s2.schema_name IS NULL)
                    )
                    AND s1.calculated_at = s2.max_calculated_at
                ORDER BY s1.schema_name, s1.table_name
            """
            )
            params = {}

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

    def query_system_scores(self) -> List[DataQualityScore]:
        """
        Get latest scores for all tables across all schemas.

        Returns:
            List of DataQualityScore objects (latest score per table)
        """
        return self.query_all_latest_scores(schema_name=None)

    def query_score_trends(
        self,
        table_name: str,
        schema_name: Optional[str] = None,
        days: int = 30,
    ) -> List[DataQualityScore]:
        """
        Get historical scores for trend analysis (alias for get_score_history).

        Args:
            table_name: Name of the table
            schema_name: Optional schema name
            days: Number of days to look back

        Returns:
            List of DataQualityScore objects, ordered by calculated_at DESC
        """
        return self.get_score_history(table_name, schema_name, days)

    def store_column_score(self, score: ColumnQualityScore) -> None:
        """
        Store a column quality score in the database.

        Args:
            score: ColumnQualityScore object to store
        """
        column_scores_table = "baselinr_column_quality_scores"
        with self.engine.connect() as conn:
            insert_query = text(
                f"""
                INSERT INTO {column_scores_table} (
                    table_name, schema_name, column_name, run_id,
                    overall_score, completeness_score, validity_score,
                    consistency_score, freshness_score, uniqueness_score,
                    accuracy_score, status, calculated_at, period_start, period_end
                ) VALUES (
                    :table_name, :schema_name, :column_name, :run_id,
                    :overall_score, :completeness_score, :validity_score,
                    :consistency_score, :freshness_score, :uniqueness_score,
                    :accuracy_score, :status, :calculated_at, :period_start, :period_end
                )
            """
            )

            conn.execute(
                insert_query,
                {
                    "table_name": score.table_name,
                    "schema_name": score.schema_name,
                    "column_name": score.column_name,
                    "run_id": score.run_id,
                    "overall_score": score.overall_score,
                    "completeness_score": score.completeness_score,
                    "validity_score": score.validity_score,
                    "consistency_score": score.consistency_score,
                    "freshness_score": score.freshness_score,
                    "uniqueness_score": score.uniqueness_score,
                    "accuracy_score": score.accuracy_score,
                    "status": score.status,
                    "calculated_at": score.calculated_at,
                    "period_start": score.period_start,
                    "period_end": score.period_end,
                },
            )

            conn.commit()
            logger.debug(
                f"Stored column quality score for {score.table_name}.{score.column_name} "
                f"(schema: {score.schema_name}): {score.overall_score:.1f}"
            )

    def get_latest_column_score(
        self,
        table_name: str,
        column_name: str,
        schema_name: Optional[str] = None,
    ) -> Optional[ColumnQualityScore]:
        """
        Get the most recent column score for a table.

        Args:
            table_name: Name of the table
            column_name: Name of the column
            schema_name: Optional schema name

        Returns:
            ColumnQualityScore if found, None otherwise
        """
        column_scores_table = "baselinr_column_quality_scores"
        conditions = [
            "table_name = :table_name",
            "column_name = :column_name",
        ]
        params: Dict[str, Any] = {
            "table_name": table_name,
            "column_name": column_name,
        }

        if schema_name:
            conditions.append("schema_name = :schema_name")
            params["schema_name"] = schema_name
        else:
            conditions.append("schema_name IS NULL")

        where_clause = " AND ".join(conditions)

        query = text(
            f"""
            SELECT table_name, schema_name, column_name, run_id,
                   overall_score, completeness_score, validity_score,
                   consistency_score, freshness_score, uniqueness_score,
                   accuracy_score, status, calculated_at, period_start, period_end
            FROM {column_scores_table}
            WHERE {where_clause}
            ORDER BY calculated_at DESC
            LIMIT 1
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(query, params).fetchone()

            if not result:
                return None

            return ColumnQualityScore(
                table_name=result[0],
                schema_name=result[1],
                column_name=result[2],
                run_id=result[3],
                overall_score=float(result[4]),
                completeness_score=float(result[5]),
                validity_score=float(result[6]),
                consistency_score=float(result[7]),
                freshness_score=float(result[8]),
                uniqueness_score=float(result[9]),
                accuracy_score=float(result[10]),
                status=result[11],
                calculated_at=result[12],
                period_start=result[13],
                period_end=result[14],
            )

    def get_column_scores_for_table(
        self,
        table_name: str,
        schema_name: Optional[str] = None,
        days: int = 30,
    ) -> List[ColumnQualityScore]:
        """
        Get latest column scores for all columns in a table.

        Args:
            table_name: Name of the table
            schema_name: Optional schema name
            days: Number of days to look back

        Returns:
            List of ColumnQualityScore objects (latest score per column)
        """
        column_scores_table = "baselinr_column_quality_scores"
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

        # Use subquery to get latest score per column
        query = text(
            f"""
            SELECT s1.table_name, s1.schema_name, s1.column_name, s1.run_id,
                   s1.overall_score, s1.completeness_score, s1.validity_score,
                   s1.consistency_score, s1.freshness_score, s1.uniqueness_score,
                   s1.accuracy_score, s1.status, s1.calculated_at, s1.period_start, s1.period_end
            FROM {column_scores_table} s1
            INNER JOIN (
                SELECT table_name, schema_name, column_name, MAX(calculated_at) as max_calculated_at
                FROM {column_scores_table}
                WHERE {where_clause}
                GROUP BY table_name, schema_name, column_name
            ) s2 ON s1.table_name = s2.table_name
                AND s1.column_name = s2.column_name
                AND (
                    (s1.schema_name = s2.schema_name)
                    OR (s1.schema_name IS NULL AND s2.schema_name IS NULL)
                )
                AND s1.calculated_at = s2.max_calculated_at
            ORDER BY s1.column_name
        """
        )

        scores = []
        with self.engine.connect() as conn:
            results = conn.execute(query, params).fetchall()

            for row in results:
                scores.append(
                    ColumnQualityScore(
                        table_name=row[0],
                        schema_name=row[1],
                        column_name=row[2],
                        run_id=row[3],
                        overall_score=float(row[4]),
                        completeness_score=float(row[5]),
                        validity_score=float(row[6]),
                        consistency_score=float(row[7]),
                        freshness_score=float(row[8]),
                        uniqueness_score=float(row[9]),
                        accuracy_score=float(row[10]),
                        status=row[11],
                        calculated_at=row[12],
                        period_start=row[13],
                        period_end=row[14],
                    )
                )

        return scores
