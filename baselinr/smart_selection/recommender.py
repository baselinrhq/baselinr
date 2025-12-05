"""
Recommendation engine for smart table and column selection.

Orchestrates metadata collection, scoring, and recommendation generation
for intelligent table and column-level selection.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml  # type: ignore

from ..config.schema import ConnectionConfig, DatabaseType, TablePattern
from .column_analysis.check_inferencer import CheckInferencer, ColumnRecommendation
from .column_analysis.metadata_analyzer import MetadataAnalyzer
from .column_analysis.pattern_matcher import PatternMatcher
from .column_analysis.statistical_analyzer import StatisticalAnalyzer
from .config import SmartSelectionConfig
from .learning.pattern_learner import PatternLearner
from .learning.pattern_store import PatternStore
from .metadata_collector import MetadataCollector, TableMetadata
from .scorer import TableScore, TableScorer
from .scoring.check_prioritizer import CheckPrioritizer, PrioritizationConfig
from .scoring.confidence_scorer import ConfidenceScorer

logger = logging.getLogger(__name__)


@dataclass
class ColumnCheckRecommendation:
    """A recommended check for a column."""

    column: str
    data_type: str
    confidence: float
    signals: List[str]
    suggested_checks: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML export."""
        return {
            "column": self.column,
            "data_type": self.data_type,
            "confidence": round(self.confidence, 2),
            "signals": self.signals,
            "suggested_checks": self.suggested_checks,
        }


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

    # Column-level recommendations (Phase 2)
    column_recommendations: List[ColumnCheckRecommendation] = field(default_factory=list)
    low_confidence_columns: List[ColumnCheckRecommendation] = field(default_factory=list)

    # Metadata for context
    query_count: int = 0
    queries_per_day: float = 0.0
    row_count: Optional[int] = None
    last_query_days_ago: Optional[int] = None
    column_count: int = 0

    # Lineage-aware scoring (Phase 3)
    lineage_score: float = 0.0
    lineage_context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML export."""
        result: Dict[str, Any] = {
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

        # Add lineage context if available (Phase 3)
        if self.lineage_score > 0:
            result["lineage_score"] = round(self.lineage_score, 4)
        if self.lineage_context:
            result["lineage_context"] = self.lineage_context

        if self.warnings:
            result["warnings"] = self.warnings

        # Add column recommendations if available
        if self.column_recommendations:
            result["column_recommendations"] = [
                col.to_dict() for col in self.column_recommendations
            ]

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

    # Column-level summary (Phase 2)
    total_columns_analyzed: int = 0
    total_column_checks_recommended: int = 0
    column_confidence_distribution: Dict[str, int] = field(default_factory=dict)
    low_confidence_suggestions: List[Dict[str, Any]] = field(default_factory=list)

    def to_yaml_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML export."""
        result: Dict[str, Any] = {
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

        # Add column summary if available
        if self.total_columns_analyzed > 0:
            result["metadata"]["column_summary"] = {
                "total_columns_analyzed": self.total_columns_analyzed,
                "total_checks_recommended": self.total_column_checks_recommended,
                "confidence_distribution": self.column_confidence_distribution,
            }

        # Add low confidence suggestions separately
        if self.low_confidence_suggestions:
            result["low_confidence_suggestions"] = self.low_confidence_suggestions

        return result


class ColumnRecommendationEngine:
    """Orchestrates column-level check recommendation process."""

    def __init__(
        self,
        source_engine,
        storage_engine=None,
        smart_config: Optional[SmartSelectionConfig] = None,
        database_type: Optional[str] = None,
    ):
        """
        Initialize column recommendation engine.

        Args:
            source_engine: SQLAlchemy engine for source database
            storage_engine: Optional SQLAlchemy engine for profiling data storage
            smart_config: Smart selection configuration
            database_type: Type of database
        """
        self.source_engine = source_engine
        self.storage_engine = storage_engine
        self.smart_config = smart_config
        self.database_type = database_type or source_engine.dialect.name

        # Initialize components
        self.metadata_analyzer = MetadataAnalyzer(
            engine=source_engine,
            database_type=self.database_type,
        )

        # Pattern matcher with custom patterns from config
        custom_patterns = None
        if smart_config and smart_config.columns.patterns:
            custom_patterns = PatternMatcher.from_config(
                {"patterns": [p.model_dump() for p in smart_config.columns.patterns]}
            )
        self.pattern_matcher = custom_patterns or PatternMatcher()

        # Statistical analyzer (only if storage engine provided)
        self.statistical_analyzer = None
        if storage_engine:
            self.statistical_analyzer = StatisticalAnalyzer(storage_engine=storage_engine)

        # Check inferencer
        inference_config = smart_config.columns.inference if smart_config else None
        self.check_inferencer = CheckInferencer(
            pattern_matcher=self.pattern_matcher,
            confidence_threshold=inference_config.confidence_threshold if inference_config else 0.5,
            max_checks_per_column=inference_config.max_checks_per_column if inference_config else 5,
        )

        # Prioritizer
        prioritization_config = PrioritizationConfig(
            max_checks_per_column=inference_config.max_checks_per_column if inference_config else 5,
            min_confidence=inference_config.confidence_threshold if inference_config else 0.5,
            preferred_checks=inference_config.preferred_checks if inference_config else [],
            avoided_checks=inference_config.avoided_checks if inference_config else [],
            prioritize_primary_keys=(
                inference_config.prioritize_primary_keys if inference_config else True
            ),
            prioritize_foreign_keys=(
                inference_config.prioritize_foreign_keys if inference_config else True
            ),
            prioritize_timestamps=(
                inference_config.prioritize_timestamp_columns if inference_config else True
            ),
        )
        self.prioritizer = CheckPrioritizer(config=prioritization_config)

        # Confidence scorer
        self.confidence_scorer = ConfidenceScorer()

        # Pattern learning
        self.pattern_learner = None
        self.pattern_store = None
        if smart_config and smart_config.columns.learn_from_config:
            self.pattern_learner = PatternLearner()
            if smart_config.columns.learned_patterns_file:
                self.pattern_store = PatternStore(
                    storage_path=smart_config.columns.learned_patterns_file
                )

    def generate_column_recommendations(
        self,
        table_name: str,
        schema: Optional[str] = None,
        use_profiling_data: bool = True,
    ) -> List[ColumnRecommendation]:
        """
        Generate check recommendations for columns in a table.

        Args:
            table_name: Table name
            schema: Optional schema name
            use_profiling_data: Whether to use profiling data if available

        Returns:
            List of column recommendations
        """
        # Get column metadata
        columns_metadata = self.metadata_analyzer.analyze_table(table_name, schema)

        if not columns_metadata:
            logger.warning(f"No columns found for table {schema}.{table_name}")
            return []

        recommendations = []

        for col_metadata in columns_metadata:
            # Get statistics if available
            statistics = None
            if use_profiling_data and self.statistical_analyzer:
                statistics = self.statistical_analyzer.analyze_column(
                    table_name=table_name,
                    column_name=col_metadata.name,
                    schema_name=schema,
                )

            # Infer checks
            recommendation = self.check_inferencer.infer_checks(col_metadata, statistics)

            # Score confidence
            recommendation.overall_confidence = self.confidence_scorer.score_recommendation(
                recommendation
            )

            recommendations.append(recommendation)

        # Prioritize recommendations
        recommendations = self.prioritizer.prioritize_table_recommendations(recommendations)

        return recommendations

    def to_column_check_recommendation(
        self,
        rec: ColumnRecommendation,
    ) -> ColumnCheckRecommendation:
        """Convert internal recommendation to export format."""
        return ColumnCheckRecommendation(
            column=rec.column_name,
            data_type=rec.data_type,
            confidence=rec.overall_confidence,
            signals=rec.signals,
            suggested_checks=[check.to_dict() for check in rec.suggested_checks],
        )


class RecommendationEngine:
    """Orchestrates table and column recommendation process."""

    def __init__(
        self,
        connection_config: ConnectionConfig,
        smart_config: SmartSelectionConfig,
        storage_engine=None,
    ):
        """
        Initialize recommendation engine.

        Args:
            connection_config: Database connection configuration
            smart_config: Smart selection configuration
            storage_engine: Optional storage engine for profiling data
        """
        self.connection_config = connection_config
        self.smart_config = smart_config
        self.database_type = DatabaseType(connection_config.type)
        self.storage_engine = storage_engine

        # Initialize components
        self.scorer = TableScorer(smart_config.criteria)

        # Column recommendation engine (initialized when needed)
        self._column_engine: Optional[ColumnRecommendationEngine] = None

    def _get_column_engine(self, engine) -> ColumnRecommendationEngine:
        """Get or create column recommendation engine."""
        if self._column_engine is None:
            self._column_engine = ColumnRecommendationEngine(
                source_engine=engine,
                storage_engine=self.storage_engine,
                smart_config=self.smart_config,
                database_type=self.database_type.value,
            )
        return self._column_engine

    def generate_recommendations(
        self,
        engine,
        schema: Optional[str] = None,
        existing_tables: Optional[List[TablePattern]] = None,
        include_columns: bool = False,
    ) -> RecommendationReport:
        """
        Generate table recommendations with optional column-level recommendations.

        Args:
            engine: SQLAlchemy engine for querying metadata
            schema: Optional schema to limit recommendations to
            existing_tables: Existing table patterns to avoid duplicating
            include_columns: Whether to include column-level recommendations

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
        recommendations = [
            self._create_recommendation(score, engine, include_columns)
            for score in recommended_scores
        ]

        # Track excluded tables
        excluded = self._create_exclusions(
            all_tables=all_tables,
            scored_tables=scored_tables,
            recommended_scores=recommended_scores,
        )

        # Calculate column-level summary
        total_columns = 0
        total_checks = 0
        column_conf_dist: Dict[str, int] = {
            "high (0.8+)": 0,
            "medium (0.5-0.8)": 0,
            "low (<0.5)": 0,
        }
        low_confidence_suggestions = []

        if include_columns:
            for rec in recommendations:
                total_columns += len(rec.column_recommendations) + len(rec.low_confidence_columns)
                total_checks += sum(len(col.suggested_checks) for col in rec.column_recommendations)

                for col in rec.column_recommendations:
                    if col.confidence >= 0.8:
                        column_conf_dist["high (0.8+)"] += 1
                    elif col.confidence >= 0.5:
                        column_conf_dist["medium (0.5-0.8)"] += 1
                    else:
                        column_conf_dist["low (<0.5)"] += 1

                # Collect low confidence suggestions
                for col in rec.low_confidence_columns:
                    low_confidence_suggestions.append(
                        {
                            "schema": rec.schema,
                            "table": rec.table,
                            "column": col.column,
                            "data_type": col.data_type,
                            "confidence": col.confidence,
                            "signals": col.signals,
                            "suggested_checks": col.suggested_checks,
                            "note": "Consider manual inspection to define validation",
                        }
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
            total_columns_analyzed=total_columns,
            total_column_checks_recommended=total_checks,
            column_confidence_distribution=column_conf_dist if include_columns else {},
            low_confidence_suggestions=low_confidence_suggestions,
        )

        logger.info(
            f"Generated {len(recommendations)} table recommendations "
            f"and {len(excluded)} exclusions"
        )
        if include_columns:
            logger.info(
                f"Generated {total_checks} column check recommendations "
                f"across {total_columns} columns"
            )

        return report

    def generate_column_recommendations(
        self,
        engine,
        table_name: str,
        schema: Optional[str] = None,
    ) -> List[ColumnCheckRecommendation]:
        """
        Generate column recommendations for a specific table.

        Args:
            engine: SQLAlchemy engine
            table_name: Table name
            schema: Optional schema name

        Returns:
            List of column check recommendations
        """
        column_engine = self._get_column_engine(engine)

        # Check if column recommendations are enabled
        if not self.smart_config.columns.enabled:
            return []

        use_profiling = self.smart_config.columns.inference.use_profiling_data

        recommendations = column_engine.generate_column_recommendations(
            table_name=table_name,
            schema=schema,
            use_profiling_data=use_profiling,
        )

        return [column_engine.to_column_check_recommendation(rec) for rec in recommendations]

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

    def _create_recommendation(
        self,
        score: TableScore,
        engine=None,
        include_columns: bool = False,
    ) -> TableRecommendation:
        """
        Create a recommendation from a table score.

        Args:
            score: Scored table
            engine: SQLAlchemy engine (needed for column recommendations)
            include_columns: Whether to include column-level recommendations

        Returns:
            TableRecommendation
        """
        table = score.metadata

        # Determine suggested checks based on table characteristics
        suggested_checks = self._suggest_checks(table)

        # Get column recommendations if enabled
        column_recommendations = []
        low_confidence_columns = []
        column_count = 0

        if include_columns and engine and self.smart_config.columns.enabled:
            try:
                column_engine = self._get_column_engine(engine)
                use_profiling = self.smart_config.columns.inference.use_profiling_data
                conf_threshold = self.smart_config.columns.inference.confidence_threshold

                col_recs = column_engine.generate_column_recommendations(
                    table_name=table.table,
                    schema=table.schema,
                    use_profiling_data=use_profiling,
                )

                column_count = len(col_recs)

                for rec in col_recs:
                    col_check_rec = column_engine.to_column_check_recommendation(rec)
                    if rec.overall_confidence >= conf_threshold:
                        column_recommendations.append(col_check_rec)
                    else:
                        low_confidence_columns.append(col_check_rec)

            except Exception as e:
                logger.warning(
                    f"Failed to generate column recommendations for "
                    f"{table.schema}.{table.table}: {e}"
                )

        return TableRecommendation(
            database=table.database,
            schema=table.schema,
            table=table.table,
            confidence=score.confidence,
            score=score.total_score,
            reasons=score.reasons,
            warnings=score.warnings,
            suggested_checks=suggested_checks,
            column_recommendations=column_recommendations,
            low_confidence_columns=low_confidence_columns,
            query_count=table.query_count,
            queries_per_day=table.queries_per_day,
            row_count=table.row_count,
            last_query_days_ago=table.days_since_last_query,
            column_count=column_count,
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
