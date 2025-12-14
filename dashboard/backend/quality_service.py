"""
Service layer for quality scores API operations.
"""

import sys
import os
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.engine import Engine
from sqlalchemy import text

# Add parent directory to path to import baselinr
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from baselinr.quality.storage import QualityScoreStorage
from baselinr.quality.scorer import QualityScorer
from baselinr.quality.models import DataQualityScore, ColumnQualityScore
from baselinr.config.schema import QualityScoringConfig
from quality_models import (
    QualityScoreResponse,
    ScoreComponentResponse,
    ScoreHistoryResponse,
    QualityScoresListResponse,
    SchemaScoreResponse,
    SystemScoreResponse,
    IssuesResponse,
    TrendAnalysisResponse,
    ColumnScoreResponse,
    ColumnScoresListResponse,
    ScoreComparisonResponse,
)

logger = logging.getLogger(__name__)


class QualityService:
    """Service for quality scores API operations."""

    def __init__(self, db_engine: Optional[Engine] = None):
        """
        Initialize quality service.

        Args:
            db_engine: Database engine for score storage
        """
        self.db_engine = db_engine
        if db_engine:
            self.storage = QualityScoreStorage(db_engine)
        else:
            self.storage = None
            logger.warning("No database engine provided, quality service will not function")

    def _convert_score_to_response(
        self, score: DataQualityScore, include_trend: bool = True
    ) -> QualityScoreResponse:
        """
        Convert DataQualityScore to QualityScoreResponse with trend calculation.

        Args:
            score: DataQualityScore object
            include_trend: Whether to calculate and include trend data

        Returns:
            QualityScoreResponse object
        """
        trend = None
        trend_percentage = None

        if include_trend and self.storage:
            # Get previous score for trend calculation
            history = self.storage.get_score_history(
                score.table_name, score.schema_name, days=90
            )
            if len(history) > 1:
                # Current is first, previous is second
                previous = history[1]
                # Use QualityScorer.compare_scores if available
                # For now, calculate manually
                if previous.overall_score == 0:
                    trend_percentage = 100.0 if score.overall_score > 0 else 0.0
                else:
                    trend_percentage = (
                        (score.overall_score - previous.overall_score)
                        / previous.overall_score
                        * 100.0
                    )

                if trend_percentage > 1.0:
                    trend = "improving"
                elif trend_percentage < -1.0:
                    trend = "degrading"
                else:
                    trend = "stable"

        return QualityScoreResponse(
            table_name=score.table_name,
            schema_name=score.schema_name,
            overall_score=score.overall_score,
            status=score.status,
            trend=trend,
            trend_percentage=round(trend_percentage, 2) if trend_percentage is not None else None,
            components=ScoreComponentResponse(
                completeness=score.completeness_score,
                validity=score.validity_score,
                consistency=score.consistency_score,
                freshness=score.freshness_score,
                uniqueness=score.uniqueness_score,
                accuracy=score.accuracy_score,
            ),
            issues=IssuesResponse(
                total=score.total_issues,
                critical=score.critical_issues,
                warnings=score.warnings,
            ),
            calculated_at=score.calculated_at,
            run_id=score.run_id,
        )

    def get_table_score(
        self, table_name: str, schema_name: Optional[str] = None
    ) -> Optional[QualityScoreResponse]:
        """
        Get latest score for a table.

        Args:
            table_name: Name of the table
            schema_name: Optional schema name. If provided but no score found,
                        will try again without schema filter as fallback.

        Returns:
            QualityScoreResponse if found, None otherwise
        """
        if not self.storage:
            logger.warning(f"No storage available for table {table_name}")
            return None

        try:
            logger.debug(f"Fetching score for table: {table_name}, schema: {schema_name}")
            score = self.storage.get_latest_score(table_name, schema_name)
            
            # If schema was provided but no score found, try without schema as fallback
            if not score and schema_name:
                logger.debug(f"No score found with schema {schema_name}, trying without schema filter")
                score = self.storage.get_latest_score(table_name, schema_name=None)
            
            if not score:
                logger.debug(f"No score found for table: {table_name}, schema: {schema_name}")
                return None

            logger.debug(f"Found score for {table_name}: {score.overall_score} (schema: {score.schema_name})")
            return self._convert_score_to_response(score, include_trend=True)
        except Exception as e:
            logger.error(f"Error getting table score for {table_name}: {e}", exc_info=True)
            return None

    def get_all_scores(
        self, schema: Optional[str] = None, status: Optional[str] = None
    ) -> List[QualityScoreResponse]:
        """
        Get all table scores, optionally filtered by schema and status.

        Args:
            schema: Optional schema name to filter by
            status: Optional status to filter by (healthy, warning, critical)

        Returns:
            List of QualityScoreResponse objects
        """
        if not self.storage:
            return []

        try:
            scores = self.storage.query_all_latest_scores(schema_name=schema)
            responses = [
                self._convert_score_to_response(score, include_trend=False)
                for score in scores
            ]

            # Filter by status if provided
            if status:
                responses = [r for r in responses if r.status == status.lower()]

            return responses
        except Exception as e:
            logger.error(f"Error getting all scores: {e}")
            return []

    def get_score_history(
        self,
        table_name: str,
        schema_name: Optional[str] = None,
        days: int = 30,
    ) -> List[QualityScoreResponse]:
        """
        Get historical scores for a table.

        Args:
            table_name: Name of the table
            schema_name: Optional schema name
            days: Number of days to look back

        Returns:
            List of QualityScoreResponse objects
        """
        if not self.storage:
            return []

        try:
            scores = self.storage.get_score_history(table_name, schema_name, days)
            return [
                self._convert_score_to_response(score, include_trend=False) for score in scores
            ]
        except Exception as e:
            logger.error(f"Error getting score history for {table_name}: {e}")
            return []

    def _get_table_weights(self, table_names: List[str], schema_name: Optional[str] = None) -> Dict[str, float]:
        """
        Get weights for tables based on row count.

        Args:
            table_names: List of table names
            schema_name: Optional schema name

        Returns:
            Dictionary mapping table_name -> weight (0-1)
        """
        weights: Dict[str, float] = {}
        if not self.db_engine:
            # Equal weights if no engine
            weight = 1.0 / len(table_names) if table_names else 1.0
            return {name: weight for name in table_names}

        try:
            # Build IN clause with individual parameters for better compatibility
            placeholders = ','.join([f':table_{i}' for i in range(len(table_names))])
            conditions = [f"dataset_name IN ({placeholders})"]
            params: Dict[str, Any] = {f"table_{i}": name for i, name in enumerate(table_names)}

            if schema_name:
                conditions.append("schema_name = :schema_name")
                params["schema_name"] = schema_name
            else:
                conditions.append("schema_name IS NULL")

            where_clause = " AND ".join(conditions)

            # Get latest row_count for each table
            query = text(
                f"""
                SELECT dataset_name, MAX(row_count) as max_row_count
                FROM baselinr_runs
                WHERE {where_clause}
                GROUP BY dataset_name
            """
            )

            row_counts: Dict[str, int] = {}
            total_rows = 0

            with self.db_engine.connect() as conn:
                results = conn.execute(query, params).fetchall()
                for row in results:
                    table_name = row[0]
                    row_count = int(row[1]) if row[1] else 0
                    row_counts[table_name] = row_count
                    total_rows += row_count

            # Calculate weights (proportional to row count)
            if total_rows > 0:
                for table_name in table_names:
                    row_count = row_counts.get(table_name, 0)
                    weights[table_name] = row_count / total_rows if total_rows > 0 else 1.0 / len(table_names)
            else:
                # Equal weights if no row count data
                weight = 1.0 / len(table_names) if table_names else 1.0
                weights = {name: weight for name in table_names}

        except Exception as e:
            logger.debug(f"Error getting table weights: {e}, using equal weights")
            weight = 1.0 / len(table_names) if table_names else 1.0
            weights = {name: weight for name in table_names}

        return weights

    def get_schema_score(self, schema_name: str) -> Optional[SchemaScoreResponse]:
        """
        Calculate aggregated schema-level score with weighted averages.

        Args:
            schema_name: Name of the schema

        Returns:
            SchemaScoreResponse if schema has scores, None otherwise
        """
        if not self.storage:
            return None

        try:
            scores = self.storage.query_scores_by_schema(schema_name)
            if not scores:
                return None

            # Get table weights based on row count
            table_names = [s.table_name for s in scores]
            weights = self._get_table_weights(table_names, schema_name)

            # Calculate weighted average for overall score
            weighted_total = sum(s.overall_score * weights.get(s.table_name, 1.0 / len(scores)) for s in scores)
            avg_score = weighted_total

            # Calculate component-level weighted averages
            component_scores = {
                "completeness": sum(s.completeness_score * weights.get(s.table_name, 1.0 / len(scores)) for s in scores),
                "validity": sum(s.validity_score * weights.get(s.table_name, 1.0 / len(scores)) for s in scores),
                "consistency": sum(s.consistency_score * weights.get(s.table_name, 1.0 / len(scores)) for s in scores),
                "freshness": sum(s.freshness_score * weights.get(s.table_name, 1.0 / len(scores)) for s in scores),
                "uniqueness": sum(s.uniqueness_score * weights.get(s.table_name, 1.0 / len(scores)) for s in scores),
                "accuracy": sum(s.accuracy_score * weights.get(s.table_name, 1.0 / len(scores)) for s in scores),
            }

            healthy_count = sum(1 for s in scores if s.status == "healthy")
            warning_count = sum(1 for s in scores if s.status == "warning")
            critical_count = sum(1 for s in scores if s.status == "critical")

            # Determine overall status (worst status wins)
            if critical_count > 0:
                overall_status = "critical"
            elif warning_count > 0:
                overall_status = "warning"
            else:
                overall_status = "healthy"

            # Convert scores to responses
            table_responses = [
                self._convert_score_to_response(score, include_trend=False) for score in scores
            ]

            return SchemaScoreResponse(
                schema_name=schema_name,
                overall_score=round(avg_score, 2),
                status=overall_status,
                table_count=len(scores),
                healthy_count=healthy_count,
                warning_count=warning_count,
                critical_count=critical_count,
                tables=table_responses,
            )
        except Exception as e:
            logger.error(f"Error getting schema score for {schema_name}: {e}")
            return None

    def get_system_score(self) -> SystemScoreResponse:
        """
        Calculate system-level aggregated score with weighted averages.

        Returns:
            SystemScoreResponse
        """
        if not self.storage:
            return SystemScoreResponse(
                overall_score=0.0,
                status="critical",
                total_tables=0,
                healthy_count=0,
                warning_count=0,
                critical_count=0,
            )

        try:
            scores = self.storage.query_system_scores()
            if not scores:
                return SystemScoreResponse(
                    overall_score=0.0,
                    status="critical",
                    total_tables=0,
                    healthy_count=0,
                    warning_count=0,
                    critical_count=0,
                )

            # Get table weights based on row count
            table_names = [s.table_name for s in scores]
            weights = self._get_table_weights(table_names)

            # Calculate weighted average for overall score
            weighted_total = sum(s.overall_score * weights.get(s.table_name, 1.0 / len(scores)) for s in scores)
            avg_score = weighted_total

            healthy_count = sum(1 for s in scores if s.status == "healthy")
            warning_count = sum(1 for s in scores if s.status == "warning")
            critical_count = sum(1 for s in scores if s.status == "critical")

            # Determine overall status (worst status wins)
            if critical_count > 0:
                overall_status = "critical"
            elif warning_count > 0:
                overall_status = "warning"
            else:
                overall_status = "healthy"

            return SystemScoreResponse(
                overall_score=round(avg_score, 2),
                status=overall_status,
                total_tables=len(scores),
                healthy_count=healthy_count,
                warning_count=warning_count,
                critical_count=critical_count,
            )
        except Exception as e:
            logger.error(f"Error getting system score: {e}")
            return SystemScoreResponse(
                overall_score=0.0,
                status="critical",
                total_tables=0,
                healthy_count=0,
                warning_count=0,
                critical_count=0,
            )

    def get_component_breakdown(
        self, table_name: str, schema_name: Optional[str] = None
    ) -> Optional[ScoreComponentResponse]:
        """
        Get component breakdown for a table.

        Args:
            table_name: Name of the table
            schema_name: Optional schema name

        Returns:
            ScoreComponentResponse if found, None otherwise
        """
        if not self.storage:
            return None

        try:
            score = self.storage.get_latest_score(table_name, schema_name)
            if not score:
                return None

            return ScoreComponentResponse(
                completeness=score.completeness_score,
                validity=score.validity_score,
                consistency=score.consistency_score,
                freshness=score.freshness_score,
                uniqueness=score.uniqueness_score,
                accuracy=score.accuracy_score,
            )
        except Exception as e:
            logger.error(f"Error getting component breakdown for {table_name}: {e}")
            return None

    def get_trend_analysis(
        self,
        table_name: str,
        schema_name: Optional[str] = None,
        days: int = 30,
    ) -> Optional[TrendAnalysisResponse]:
        """
        Get trend analysis for a table.

        Args:
            table_name: Name of the table
            schema_name: Optional schema name
            days: Number of days to look back

        Returns:
            TrendAnalysisResponse if analysis can be performed, None otherwise
        """
        if not self.storage:
            return None

        try:
            scores = self.storage.get_score_history(table_name, schema_name, days)
            if len(scores) < 2:
                return None

            # Create scorer instance for trend analysis
            # Use default config (will be loaded from config if available)
            from baselinr.config.schema import QualityScoringConfig
            config = QualityScoringConfig()
            scorer = QualityScorer(self.db_engine, config)

            trend_data = scorer.analyze_score_trend(scores)

            return TrendAnalysisResponse(
                direction=trend_data["direction"],
                rate_of_change=trend_data["rate_of_change"],
                confidence=trend_data["confidence"],
                periods_analyzed=trend_data["periods_analyzed"],
                overall_change=trend_data["overall_change"],
            )
        except Exception as e:
            logger.error(f"Error getting trend analysis for {table_name}: {e}")
            return None

    def get_column_scores(
        self,
        table_name: str,
        schema_name: Optional[str] = None,
        days: int = 30,
    ) -> ColumnScoresListResponse:
        """
        Get column-level scores for a table.

        Args:
            table_name: Name of the table
            schema_name: Optional schema name
            days: Number of days to look back

        Returns:
            ColumnScoresListResponse with column scores
        """
        if not self.storage:
            return ColumnScoresListResponse(scores=[], total=0)

        try:
            column_scores = self.storage.get_column_scores_for_table(
                table_name, schema_name, days
            )
            responses = []
            for score in column_scores:
                responses.append(
                    ColumnScoreResponse(
                        table_name=score.table_name,
                        schema_name=score.schema_name,
                        column_name=score.column_name,
                        overall_score=score.overall_score,
                        status=score.status,
                        components=ScoreComponentResponse(
                            completeness=score.completeness_score,
                            validity=score.validity_score,
                            consistency=score.consistency_score,
                            freshness=score.freshness_score,
                            uniqueness=score.uniqueness_score,
                            accuracy=score.accuracy_score,
                        ),
                        calculated_at=score.calculated_at,
                        run_id=score.run_id,
                        period_start=score.period_start,
                        period_end=score.period_end,
                    )
                )

            return ColumnScoresListResponse(scores=responses, total=len(responses))
        except Exception as e:
            logger.error(f"Error getting column scores for {table_name}: {e}")
            return ColumnScoresListResponse(scores=[], total=0)

    def compare_scores(
        self,
        table_names: List[str],
        schema_name: Optional[str] = None,
    ) -> ScoreComparisonResponse:
        """
        Compare scores across multiple tables.

        Args:
            table_names: List of table names to compare
            schema_name: Optional schema name

        Returns:
            ScoreComparisonResponse with comparison data
        """
        if not self.storage:
            return ScoreComparisonResponse(tables=[], comparison_metrics={})

        try:
            scores = []
            for table_name in table_names:
                score = self.storage.get_latest_score(table_name, schema_name)
                if score:
                    scores.append(self._convert_score_to_response(score, include_trend=False))

            # Calculate comparison metrics
            if not scores:
                return ScoreComparisonResponse(tables=[], comparison_metrics={})

            overall_scores = [s.overall_score for s in scores]
            best_idx = overall_scores.index(max(overall_scores))
            worst_idx = overall_scores.index(min(overall_scores))

            comparison_metrics = {
                "best_performer": scores[best_idx].table_name,
                "worst_performer": scores[worst_idx].table_name,
                "average_score": round(sum(overall_scores) / len(overall_scores), 2),
                "score_range": {
                    "min": round(min(overall_scores), 2),
                    "max": round(max(overall_scores), 2),
                },
            }

            return ScoreComparisonResponse(
                tables=scores, comparison_metrics=comparison_metrics
            )
        except Exception as e:
            logger.error(f"Error comparing scores: {e}")
            return ScoreComparisonResponse(tables=[], comparison_metrics={})
