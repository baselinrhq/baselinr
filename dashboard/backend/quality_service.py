"""
Service layer for quality scores API operations.
"""

import sys
import os
import logging
from typing import List, Optional
from sqlalchemy.engine import Engine

# Add parent directory to path to import baselinr
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from baselinr.quality.storage import QualityScoreStorage
from baselinr.quality.scorer import QualityScorer
from baselinr.quality.models import DataQualityScore
from quality_models import (
    QualityScoreResponse,
    ScoreComponentResponse,
    ScoreHistoryResponse,
    QualityScoresListResponse,
    SchemaScoreResponse,
    SystemScoreResponse,
    IssuesResponse,
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

    def get_schema_score(self, schema_name: str) -> Optional[SchemaScoreResponse]:
        """
        Calculate aggregated schema-level score.

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

            # Calculate aggregated metrics
            total_score = sum(s.overall_score for s in scores)
            avg_score = total_score / len(scores) if scores else 0.0

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
        Calculate system-level aggregated score.

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

            # Calculate aggregated metrics
            total_score = sum(s.overall_score for s in scores)
            avg_score = total_score / len(scores) if scores else 0.0

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
