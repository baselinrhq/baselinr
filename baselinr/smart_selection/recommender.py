"""
Recommendation engine for smart table selection.

Orchestrates metadata collection, scoring, and recommendation generation
for intelligent table selection.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml  # type: ignore

from ..config.schema import ConnectionConfig, DatabaseType, TablePattern
from .config import SmartSelectionConfig
from .metadata_collector import MetadataCollector, TableMetadata
from .scorer import TableScore, TableScorer

logger = logging.getLogger(__name__)


@dataclass
class TableRecommendation:
    """A recommendation for a table to monitor."""

    schema: str
    table: str
    database: Optional[str] = None
    confidence: float = 0.0
    score: float = 0.0
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggested_checks: List[str] = field(default_factory=list)

    # Metadata for context
    query_count: int = 0
    queries_per_day: float = 0.0
    row_count: Optional[int] = None
    last_query_days_ago: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML export."""
        result = {
            "schema": self.schema,
            "table": self.table,
            "confidence": round(self.confidence, 2),
        }

        if self.database:
            result["database"] = self.database

        if self.reasons:
            result["reasons"] = self.reasons

        if self.suggested_checks:
            result["suggested_checks"] = self.suggested_checks

        if self.warnings:
            result["warnings"] = self.warnings

        return result

    def to_table_pattern(self) -> TablePattern:
        """Convert to TablePattern for configuration."""
        return TablePattern(  # type: ignore[call-arg]
            database=self.database,
            schema=self.schema,
            table=self.table,
        )


@dataclass
class ExcludedTable:
    """A table that was excluded from recommendations."""

    schema: str
    table: str
    database: Optional[str] = None
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML export."""
        result = {
            "schema": self.schema,
            "table": self.table,
            "reasons": self.reasons,
        }

        if self.database:
            result["database"] = self.database

        return result


@dataclass
class RecommendationReport:
    """Complete recommendation report."""

    generated_at: datetime
    lookback_days: int
    database_type: str

    recommended_tables: List[TableRecommendation]
    excluded_tables: List[ExcludedTable]

    # Summary statistics
    total_tables_analyzed: int = 0
    total_recommended: int = 0
    total_excluded: int = 0

    confidence_distribution: Dict[str, int] = field(default_factory=dict)

    def to_yaml_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML export."""
        return {
            "metadata": {
                "generated_at": self.generated_at.isoformat(),
                "lookback_days": self.lookback_days,
                "database_type": self.database_type,
                "summary": {
                    "total_tables_analyzed": self.total_tables_analyzed,
                    "total_recommended": self.total_recommended,
                    "total_excluded": self.total_excluded,
                },
            },
            "recommended_tables": [rec.to_dict() for rec in self.recommended_tables],
            "excluded_tables": [exc.to_dict() for exc in self.excluded_tables],
        }


class RecommendationEngine:
    """Orchestrates table recommendation process."""

    def __init__(
        self,
        connection_config: ConnectionConfig,
        smart_config: SmartSelectionConfig,
    ):
        """
        Initialize recommendation engine.

        Args:
            connection_config: Database connection configuration
            smart_config: Smart selection configuration
        """
        self.connection_config = connection_config
        self.smart_config = smart_config
        self.database_type = DatabaseType(connection_config.type)

        # Initialize components
        self.scorer = TableScorer(smart_config.criteria)

    def generate_recommendations(
        self,
        engine,
        schema: Optional[str] = None,
        existing_tables: Optional[List[TablePattern]] = None,
    ) -> RecommendationReport:
        """
        Generate table recommendations.

        Args:
            engine: SQLAlchemy engine for querying metadata
            schema: Optional schema to limit recommendations to
            existing_tables: Existing table patterns to avoid duplicating

        Returns:
            RecommendationReport with recommendations and exclusions
        """
        logger.info("Starting recommendation generation")

        # Collect metadata
        collector = MetadataCollector(
            engine=engine,
            database_type=self.database_type,
            lookback_days=self.smart_config.criteria.lookback_days,
        )

        all_tables = collector.collect_metadata(schema=schema)
        logger.info(f"Collected metadata for {len(all_tables)} tables")

        # Score tables
        scored_tables = self.scorer.score_tables(all_tables)
        logger.info(f"Scored {len(scored_tables)} tables")

        # Filter existing tables if requested
        if existing_tables and self.smart_config.auto_apply.skip_existing:
            scored_tables = self._filter_existing(scored_tables, existing_tables)
            logger.info(f"Filtered to {len(scored_tables)} tables (excluding existing)")

        # Apply confidence threshold for auto mode
        if self.smart_config.mode == "auto":
            threshold = self.smart_config.auto_apply.confidence_threshold
            scored_tables = [t for t in scored_tables if t.confidence >= threshold]
            logger.info(f"Applied confidence threshold {threshold}: {len(scored_tables)} tables")

        # Limit number of recommendations
        max_tables = self.smart_config.auto_apply.max_tables
        recommended_scores = scored_tables[:max_tables]

        # Convert to recommendations
        recommendations = [self._create_recommendation(score) for score in recommended_scores]

        # Track excluded tables
        excluded = self._create_exclusions(
            all_tables=all_tables,
            scored_tables=scored_tables,
            recommended_scores=recommended_scores,
        )

        # Generate report
        report = RecommendationReport(
            generated_at=datetime.now(),
            lookback_days=self.smart_config.criteria.lookback_days,
            database_type=self.database_type.value,
            recommended_tables=recommendations,
            excluded_tables=excluded,
            total_tables_analyzed=len(all_tables),
            total_recommended=len(recommendations),
            total_excluded=len(excluded),
            confidence_distribution=self._calculate_confidence_distribution(recommended_scores),
        )

        logger.info(
            f"Generated {len(recommendations)} recommendations " f"and {len(excluded)} exclusions"
        )

        return report

    def save_recommendations(
        self,
        report: RecommendationReport,
        output_file: str,
    ):
        """
        Save recommendations to YAML file.

        Args:
            report: Recommendation report to save
            output_file: Path to output file
        """
        logger.info(f"Saving recommendations to {output_file}")

        yaml_dict = report.to_yaml_dict()

        with open(output_file, "w") as f:
            # Add header comment
            f.write("# Baselinr Table Recommendations\n")
            f.write(f"# Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Based on {report.lookback_days} days of usage data\n")
            f.write(f"# Database: {report.database_type}\n")
            f.write("#\n")
            f.write(
                f"# Summary: {report.total_recommended} recommended, "
                f"{report.total_excluded} excluded "
                f"(from {report.total_tables_analyzed} analyzed)\n"
            )
            f.write("#\n\n")

            yaml.dump(yaml_dict, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Saved recommendations to {output_file}")

    def _create_recommendation(self, score: TableScore) -> TableRecommendation:
        """
        Create a recommendation from a table score.

        Args:
            score: Scored table

        Returns:
            TableRecommendation
        """
        table = score.metadata

        # Determine suggested checks based on table characteristics
        suggested_checks = self._suggest_checks(table)

        return TableRecommendation(
            database=table.database,
            schema=table.schema,
            table=table.table,
            confidence=score.confidence,
            score=score.total_score,
            reasons=score.reasons,
            warnings=score.warnings,
            suggested_checks=suggested_checks,
            query_count=table.query_count,
            queries_per_day=table.queries_per_day,
            row_count=table.row_count,
            last_query_days_ago=table.days_since_last_query,
        )

    def _suggest_checks(self, table: TableMetadata) -> List[str]:
        """
        Suggest profiling checks based on table characteristics.

        Args:
            table: Table metadata

        Returns:
            List of suggested check names
        """
        if not self.smart_config.recommendations.include_suggested_checks:
            return []

        checks = []

        # Always suggest freshness for active tables
        if table.query_count > 0:
            checks.append("freshness")

        # Always suggest row count
        checks.append("row_count")

        # Completeness for moderate-sized tables
        if table.row_count and 1000 < table.row_count < 10000000:
            checks.append("completeness")

        # Numeric distribution for tables likely to have metrics
        if table.table_type != "VIEW":
            checks.append("numeric_distribution")

        # Schema stability for frequently queried tables
        if table.queries_per_day > 5:
            checks.append("schema_stability")

        return checks

    def _filter_existing(
        self,
        scored_tables: List[TableScore],
        existing_tables: List[TablePattern],
    ) -> List[TableScore]:
        """
        Filter out tables that already exist in configuration.

        Args:
            scored_tables: Scored tables
            existing_tables: Existing table patterns

        Returns:
            Filtered list of scored tables
        """
        # Build set of existing table identifiers
        existing_set = set()
        for pattern in existing_tables:
            if pattern.table:  # Only explicit tables
                identifier = (
                    pattern.database or "",
                    pattern.schema_ or "",
                    pattern.table,
                )
                existing_set.add(identifier)

        # Filter scored tables
        filtered = []
        for score in scored_tables:
            table = score.metadata
            identifier = (table.database or "", table.schema, table.table)
            if identifier not in existing_set:
                filtered.append(score)

        return filtered

    def _create_exclusions(
        self,
        all_tables: List[TableMetadata],
        scored_tables: List[TableScore],
        recommended_scores: List[TableScore],
    ) -> List[ExcludedTable]:
        """
        Create exclusion records for tables that weren't recommended.

        Args:
            all_tables: All tables analyzed
            scored_tables: Tables that passed scoring
            recommended_scores: Tables that were recommended

        Returns:
            List of excluded tables with reasons
        """
        # Build sets for quick lookup
        scored_ids = {
            (s.metadata.database, s.metadata.schema, s.metadata.table) for s in scored_tables
        }
        recommended_ids = {
            (s.metadata.database, s.metadata.schema, s.metadata.table) for s in recommended_scores
        }

        exclusions = []

        # Tables that didn't pass scoring criteria
        for table in all_tables:
            table_id = (table.database, table.schema, table.table)

            if table_id in recommended_ids:
                continue  # This was recommended

            reasons = []

            if table_id not in scored_ids:
                # Didn't pass scoring criteria
                reasons.extend(self._explain_exclusion(table))
            else:
                # Passed scoring but didn't make the cut
                reasons.append("Score too low for top recommendations")

            if reasons:
                exclusions.append(
                    ExcludedTable(
                        database=table.database,
                        schema=table.schema,
                        table=table.table,
                        reasons=reasons,
                    )
                )

        # Limit number of exclusions to report (top 20 most relevant)
        exclusions = exclusions[:20]

        return exclusions

    def _explain_exclusion(self, table: TableMetadata) -> List[str]:
        """
        Explain why a table was excluded.

        Args:
            table: Table metadata

        Returns:
            List of exclusion reasons
        """
        reasons = []
        criteria = self.smart_config.criteria

        # Check each criterion
        if table.query_count < criteria.min_query_count:
            reasons.append(
                f"Query count ({table.query_count}) below threshold "
                f"({criteria.min_query_count})"
            )

        if table.queries_per_day < criteria.min_queries_per_day:
            reasons.append(
                f"Queries per day ({table.queries_per_day:.1f}) below threshold "
                f"({criteria.min_queries_per_day})"
            )

        if criteria.min_rows and table.row_count:
            if table.row_count < criteria.min_rows:
                reasons.append(
                    f"Row count ({table.row_count:,}) below minimum ({criteria.min_rows:,})"
                )

        if criteria.max_rows and table.row_count:
            if table.row_count > criteria.max_rows:
                reasons.append(
                    f"Row count ({table.row_count:,}) above maximum ({criteria.max_rows:,})"
                )

        if criteria.max_days_since_query and table.days_since_last_query:
            if table.days_since_last_query > criteria.max_days_since_query:
                reasons.append(
                    f"Last queried {table.days_since_last_query} days ago "
                    f"(threshold: {criteria.max_days_since_query} days)"
                )

        # Check exclude patterns
        for pattern in criteria.exclude_patterns:
            if self._matches_pattern(table.table, pattern):
                reasons.append(f"Matches exclude pattern: {pattern}")

        if not reasons:
            reasons.append("Did not meet scoring criteria")

        return reasons

    def _matches_pattern(self, table_name: str, pattern: str) -> bool:
        """Check if table name matches a wildcard pattern."""
        import fnmatch

        return fnmatch.fnmatch(table_name.lower(), pattern.lower())

    def _calculate_confidence_distribution(self, scored_tables: List[TableScore]) -> Dict[str, int]:
        """
        Calculate distribution of confidence scores.

        Args:
            scored_tables: Scored tables

        Returns:
            Dictionary with confidence buckets and counts
        """
        distribution = {
            "high (0.8+)": 0,
            "medium (0.6-0.8)": 0,
            "low (<0.6)": 0,
        }

        for score in scored_tables:
            if score.confidence >= 0.8:
                distribution["high (0.8+)"] += 1
            elif score.confidence >= 0.6:
                distribution["medium (0.6-0.8)"] += 1
            else:
                distribution["low (<0.6)"] += 1

        return distribution
