"""
Main root cause analyzer that orchestrates all RCA components.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy.engine import Engine

from ..models import ImpactAnalysis, RCAResult
from .lineage_analyzer import LineageAnalyzer
from .pattern_matcher import PatternMatcher
from .temporal_correlator import TemporalCorrelator

logger = logging.getLogger(__name__)


class RootCauseAnalyzer:
    """
    Main RCA engine that combines all analysis components.

    Orchestrates temporal correlation, lineage analysis, and pattern
    matching to identify probable root causes of anomalies.
    """

    def __init__(
        self,
        engine: Engine,
        lookback_window_hours: int = 24,
        max_depth: int = 5,
        max_causes_to_return: int = 5,
        min_confidence_threshold: float = 0.3,
        enable_pattern_learning: bool = True,
    ):
        """
        Initialize root cause analyzer.

        Args:
            engine: SQLAlchemy engine
            lookback_window_hours: Time window for finding causes
            max_depth: Maximum depth for lineage traversal
            max_causes_to_return: Maximum number of causes to return
            min_confidence_threshold: Minimum confidence to include a cause
            enable_pattern_learning: Whether to use pattern matching
        """
        self.engine = engine
        self.max_causes_to_return = max_causes_to_return
        self.min_confidence_threshold = min_confidence_threshold
        self.enable_pattern_learning = enable_pattern_learning

        # Initialize analyzers
        self.temporal_correlator = TemporalCorrelator(
            engine=engine,
            lookback_window_hours=lookback_window_hours,
            max_causes_to_return=max_causes_to_return * 2,  # Get more for merging
        )

        self.lineage_analyzer = LineageAnalyzer(
            engine=engine,
            max_depth=max_depth,
            lookback_window_hours=lookback_window_hours,
        )

        # Pattern matcher is optional
        self.pattern_matcher: Optional[PatternMatcher] = None
        if enable_pattern_learning:
            self.pattern_matcher = PatternMatcher(
                engine=engine,
                min_pattern_occurrences=3,
                historical_window_days=90,
            )

    def analyze(
        self,
        anomaly_id: str,
        table_name: str,
        anomaly_timestamp: datetime,
        database_name: Optional[str] = None,
        schema_name: Optional[str] = None,
        column_name: Optional[str] = None,
        metric_name: Optional[str] = None,
        anomaly_type: Optional[str] = None,
    ) -> RCAResult:
        """
        Perform complete root cause analysis for an anomaly.

        Args:
            anomaly_id: Unique identifier for the anomaly
            table_name: Table with the anomaly
            anomaly_timestamp: When the anomaly occurred
            database_name: Database name (for multi-database warehouses)
            schema_name: Schema name
            column_name: Column with anomaly
            metric_name: Metric that is anomalous
            anomaly_type: Type of anomaly

        Returns:
            RCAResult with probable causes and impact analysis
        """
        table_identifier = (
            f"{database_name}.{schema_name}.{table_name}"
            if database_name and schema_name
            else f"{schema_name}.{table_name}" if schema_name else table_name
        )
        logger.info(
            f"Starting RCA for anomaly {anomaly_id} in {table_identifier} "
            f"at {anomaly_timestamp}"
        )

        all_causes: List[Dict[str, Any]] = []

        # 1. Temporal correlation analysis
        logger.debug("Running temporal correlation analysis...")
        try:
            pipeline_causes, deployment_causes = (
                self.temporal_correlator.find_all_correlated_events(
                    anomaly_timestamp=anomaly_timestamp,
                    table_name=table_name,
                    database_name=database_name,
                    schema_name=schema_name,
                )
            )

            # Convert to dicts
            all_causes.extend([c.to_dict() for c in pipeline_causes])
            all_causes.extend([c.to_dict() for c in deployment_causes])

            logger.debug(
                f"Found {len(pipeline_causes)} pipeline causes, "
                f"{len(deployment_causes)} deployment causes"
            )

        except Exception as e:
            logger.error(f"Error in temporal correlation: {e}")

        # 2. Lineage-based analysis
        logger.debug("Running lineage-based analysis...")
        try:
            upstream_causes = self.lineage_analyzer.find_upstream_anomalies(
                table_name=table_name,
                database_name=database_name,
                schema_name=schema_name,
                anomaly_timestamp=anomaly_timestamp,
                column_name=column_name,
                metric_name=metric_name,
            )

            all_causes.extend([c.to_dict() for c in upstream_causes])

            logger.debug(f"Found {len(upstream_causes)} upstream anomaly causes")

        except Exception as e:
            logger.error(f"Error in lineage analysis: {e}")

        # 3. Pattern matching (if enabled)
        if self.pattern_matcher:
            logger.debug("Applying pattern matching...")
            try:
                all_causes = self.pattern_matcher.boost_confidence_from_patterns(
                    causes=all_causes,
                    table_name=table_name,
                    column_name=column_name,
                    metric_name=metric_name,
                )

                logger.debug("Pattern matching complete")

            except Exception as e:
                logger.error(f"Error in pattern matching: {e}")

        # 4. Filter and rank causes
        filtered_causes = self._filter_and_rank_causes(all_causes)

        # 5. Calculate impact analysis
        logger.debug("Calculating impact analysis...")
        try:
            impact_analysis = self.lineage_analyzer.calculate_impact_analysis(
                table_name=table_name, database_name=database_name, schema_name=schema_name
            )
        except Exception as e:
            logger.error(f"Error calculating impact: {e}")
            impact_analysis = ImpactAnalysis()

        # 6. Create RCA result
        result = RCAResult(
            anomaly_id=anomaly_id,
            database_name=database_name,
            table_name=table_name,
            schema_name=schema_name,
            column_name=column_name,
            metric_name=metric_name,
            analyzed_at=datetime.utcnow(),
            rca_status="analyzed",
            probable_causes=filtered_causes,
            impact_analysis=impact_analysis,
            metadata={
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "total_causes_found": len(all_causes),
                "causes_after_filtering": len(filtered_causes),
                "pattern_learning_enabled": self.enable_pattern_learning,
            },
        )

        logger.info(f"RCA complete for {anomaly_id}. Found {len(filtered_causes)} probable causes.")

        return result

    def analyze_multiple_anomalies(
        self,
        anomalies: List[Dict[str, Any]],
    ) -> List[RCAResult]:
        """
        Analyze multiple anomalies and find common root causes.

        Useful when multiple tables are anomalous at the same time.

        Args:
            anomalies: List of anomaly dicts with required fields

        Returns:
            List of RCAResult objects
        """
        results = []

        # Analyze each anomaly individually
        for anomaly in anomalies:
            try:
                result = self.analyze(
                    anomaly_id=anomaly.get("anomaly_id", str(uuid4())),
                    table_name=anomaly["table_name"],
                    anomaly_timestamp=anomaly["anomaly_timestamp"],
                    schema_name=anomaly.get("schema_name"),
                    column_name=anomaly.get("column_name"),
                    metric_name=anomaly.get("metric_name"),
                    anomaly_type=anomaly.get("anomaly_type"),
                )
                results.append(result)

            except Exception as e:
                logger.error(f"Error analyzing anomaly {anomaly.get('anomaly_id')}: {e}")

        # Find common ancestors if multiple tables are affected
        if len(results) > 1:
            try:
                table_names = [r.table_name for r in results]
                schema_name = results[0].schema_name  # Assume same schema

                common_ancestors = self.lineage_analyzer.find_common_ancestors(
                    table_names=table_names, schema_name=schema_name
                )

                if common_ancestors:
                    logger.info(
                        f"Found {len(common_ancestors)} common ancestors for "
                        f"{len(results)} anomalous tables"
                    )

                    # Add to metadata
                    for result in results:
                        result.metadata["common_ancestors"] = [
                            {"table": table, "distance": dist} for table, dist in common_ancestors
                        ]

            except Exception as e:
                logger.error(f"Error finding common ancestors: {e}")

        return results

    def _filter_and_rank_causes(self, causes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter and rank causes by confidence.

        Args:
            causes: List of cause dictionaries

        Returns:
            Filtered and sorted list of top causes
        """
        # Filter by minimum confidence
        filtered = [
            c for c in causes if c.get("confidence_score", 0) >= self.min_confidence_threshold
        ]

        # Remove duplicates (same cause_id)
        seen_ids = set()
        unique_causes = []

        for cause in filtered:
            cause_id = cause.get("cause_id")
            if cause_id and cause_id not in seen_ids:
                seen_ids.add(cause_id)
                unique_causes.append(cause)

        # Sort by confidence (highest first)
        unique_causes.sort(key=lambda c: c.get("confidence_score", 0), reverse=True)

        # Limit to top N
        return unique_causes[: self.max_causes_to_return]

    def _calculate_multi_signal_score(self, cause: Dict[str, Any]) -> float:
        """
        Calculate combined score from multiple signals.

        Combines temporal proximity, lineage distance, historical correlation,
        and change magnitude.

        Args:
            cause: Cause dictionary with evidence

        Returns:
            Combined confidence score (0-1)
        """
        evidence = cause.get("evidence", {}) or {}

        # Extract individual scores
        temporal = float(evidence.get("temporal_proximity", 0.0) or 0.0)
        lineage = float(evidence.get("distance_score", 0.0) or 0.0)
        historical_dict = evidence.get("historical_pattern", {}) or {}
        historical = float(historical_dict.get("confidence_boost", 0.0) or 0.0)

        # Weighted combination
        score = (temporal * 0.4) + (lineage * 0.3) + (historical * 0.3)

        return min(1.0, float(score))

    def get_rca_summary(self, result: RCAResult) -> str:
        """
        Generate human-readable summary of RCA results.

        Args:
            result: RCAResult object

        Returns:
            Text summary
        """
        summary_lines = [
            f"Root Cause Analysis for anomaly in {result.schema_name}.{result.table_name}",
            f"Analyzed at: {result.analyzed_at.isoformat()}",
            "",
        ]

        if result.column_name:
            summary_lines.append(f"Column: {result.column_name}")
        if result.metric_name:
            summary_lines.append(f"Metric: {result.metric_name}")

        summary_lines.append("")
        summary_lines.append(f"Found {len(result.probable_causes)} probable causes:")
        summary_lines.append("")

        for i, cause in enumerate(result.probable_causes, 1):
            confidence = cause.get("confidence_score", 0) * 100
            summary_lines.append(f"{i}. [{confidence:.1f}%] {cause.get('description')}")

            if cause.get("suggested_action"):
                summary_lines.append(f"   → {cause['suggested_action']}")

        if result.impact_analysis:
            summary_lines.append("")
            summary_lines.append("Impact Analysis:")
            summary_lines.append(
                f"  - Upstream affected: {len(result.impact_analysis.upstream_affected)} tables"
            )
            summary_lines.append(
                f"  - Downstream affected: {len(result.impact_analysis.downstream_affected)} tables"
            )
            summary_lines.append(
                f"  - Blast radius: {result.impact_analysis.blast_radius_score:.2f}"
            )

        return "\n".join(summary_lines)
