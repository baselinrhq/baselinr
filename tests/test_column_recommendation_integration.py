"""
Integration tests for smart column selection recommendation engine.

Tests the full recommendation flow from analysis to output.
"""

import pytest

from baselinr.smart_selection import (
    ColumnCheckRecommendation,
    ColumnRecommendationEngine,
    RecommendationEngine,
    RecommendationReport,
)
from baselinr.smart_selection.column_analysis import (
    CheckInferencer,
    ColumnMetadata,
    ColumnStatistics,
    InferredCheck,
    MetadataAnalyzer,
    PatternMatcher,
    PatternMatch,
)
from baselinr.smart_selection.column_analysis.check_inferencer import CheckType
from baselinr.smart_selection.column_analysis.metadata_analyzer import InferredColumnType
from baselinr.smart_selection.scoring import CheckPrioritizer, ConfidenceScorer


class TestColumnRecommendationEngineIntegration:
    """Integration tests for ColumnRecommendationEngine."""

    @pytest.fixture
    def engine_components(self):
        """Create mocked engine components for testing."""
        return {
            "metadata_analyzer": None,  # Would need DB connection
            "pattern_matcher": PatternMatcher(),
            "check_inferencer": CheckInferencer(),
            "confidence_scorer": ConfidenceScorer(),
            "check_prioritizer": CheckPrioritizer(),
        }

    def test_pattern_to_check_flow(self, engine_components):
        """Test flow from pattern matching to check inference."""
        matcher = engine_components["pattern_matcher"]
        inferencer = engine_components["check_inferencer"]

        # Analyze column patterns
        column_name = "created_at"
        matches = matcher.match_column(column_name)

        assert len(matches) > 0
        assert any("timestamp" in m.pattern_name for m in matches)

        # Create metadata from patterns
        metadata = ColumnMetadata(
            name=column_name,
            data_type="TIMESTAMP",
            nullable=False,
            inferred_type=InferredColumnType.TIMESTAMP,
            name_patterns=[m.pattern_name for m in matches],
        )

        # Infer checks
        result = inferencer.infer_checks(metadata)

        assert result.column_name == column_name
        assert len(result.suggested_checks) > 0

        check_types = [c.check_type for c in result.suggested_checks]
        assert CheckType.FRESHNESS in check_types or CheckType.COMPLETENESS in check_types

    def test_email_column_full_flow(self, engine_components):
        """Test full recommendation flow for email column."""
        matcher = engine_components["pattern_matcher"]
        inferencer = engine_components["check_inferencer"]
        scorer = engine_components["confidence_scorer"]

        # Match patterns
        matches = matcher.match_column("user_email")
        assert any(m.pattern_name == "email" for m in matches)

        # Create metadata
        metadata = ColumnMetadata(
            name="user_email",
            data_type="VARCHAR(255)",
            nullable=True,
            inferred_type=InferredColumnType.STRING,
            name_patterns=["format:email"],
        )

        # Infer checks
        result = inferencer.infer_checks(metadata)

        check_types = [c.check_type for c in result.suggested_checks]
        assert CheckType.FORMAT_EMAIL in check_types

        # Score recommendation
        score = scorer.score_recommendation(result)
        assert score >= 0.5  # Should have reasonable confidence

    def test_primary_key_column_full_flow(self, engine_components):
        """Test full recommendation flow for primary key column."""
        inferencer = engine_components["check_inferencer"]
        scorer = engine_components["confidence_scorer"]
        prioritizer = engine_components["check_prioritizer"]

        # Create PK metadata
        metadata = ColumnMetadata(
            name="id",
            data_type="BIGINT",
            nullable=False,
            is_primary_key=True,
            inferred_type=InferredColumnType.IDENTIFIER,
            position=0,
        )

        # Infer checks
        result = inferencer.infer_checks(metadata)

        check_types = [c.check_type for c in result.suggested_checks]
        assert CheckType.UNIQUENESS in check_types
        assert CheckType.COMPLETENESS in check_types

        # Score - PK without stats still gets reasonable score
        score = scorer.score_recommendation(result)
        assert score >= 0.5  # PK has good base confidence

        # Prioritize
        prioritized = prioritizer.prioritize_column_checks(result)
        assert len(prioritized.suggested_checks) > 0

        # Uniqueness should be high priority for PK
        top_check = prioritized.suggested_checks[0]
        assert top_check.check_type in [CheckType.UNIQUENESS, CheckType.COMPLETENESS]

    def test_foreign_key_referential_integrity(self, engine_components):
        """Test that foreign keys get referential integrity check."""
        inferencer = engine_components["check_inferencer"]

        metadata = ColumnMetadata(
            name="customer_id",
            data_type="BIGINT",
            nullable=False,
            is_foreign_key=True,
            foreign_key_references="customers.id",
            inferred_type=InferredColumnType.IDENTIFIER,
        )

        result = inferencer.infer_checks(metadata)

        check_types = [c.check_type for c in result.suggested_checks]
        assert CheckType.REFERENTIAL_INTEGRITY in check_types

        # Check that reference is captured in config
        ref_check = next(
            c for c in result.suggested_checks
            if c.check_type == CheckType.REFERENTIAL_INTEGRITY
        )
        assert "reference" in ref_check.config or "references" in ref_check.config

    def test_categorical_column_with_statistics(self, engine_components):
        """Test categorical column with statistical data."""
        inferencer = engine_components["check_inferencer"]

        metadata = ColumnMetadata(
            name="status",
            data_type="VARCHAR(50)",
            nullable=False,
            inferred_type=InferredColumnType.CATEGORICAL,
        )

        statistics = ColumnStatistics(
            row_count=10000,
            null_count=0,
            null_percentage=0.0,
            distinct_count=5,
            unique_ratio=0.0005,
            cardinality_type="low",
            value_distribution={
                "active": 5000,
                "pending": 2000,
                "completed": 2000,
                "cancelled": 500,
                "refunded": 500,
            },
        )

        result = inferencer.infer_checks(metadata, statistics)

        check_types = [c.check_type for c in result.suggested_checks]
        assert CheckType.ALLOWED_VALUES in check_types

    def test_numeric_column_with_range(self, engine_components):
        """Test numeric column gets range check based on stats."""
        inferencer = engine_components["check_inferencer"]

        metadata = ColumnMetadata(
            name="price",
            data_type="DECIMAL(10,2)",
            nullable=True,
            inferred_type=InferredColumnType.NUMERIC,
            name_patterns=["monetary"],
        )

        statistics = ColumnStatistics(
            row_count=5000,
            null_count=100,
            null_percentage=2.0,
            min_value=0.01,
            max_value=999.99,
        )

        result = inferencer.infer_checks(metadata, statistics)

        check_types = [c.check_type for c in result.suggested_checks]
        assert CheckType.NON_NEGATIVE in check_types or CheckType.RANGE in check_types

    def test_multiple_columns_prioritization(self, engine_components):
        """Test prioritization across multiple columns."""
        from baselinr.smart_selection.column_analysis.check_inferencer import ColumnRecommendation

        prioritizer = engine_components["check_prioritizer"]

        # Create recommendations for multiple columns with checks
        pk_metadata = ColumnMetadata(
            name="id",
            data_type="BIGINT",
            is_primary_key=True,
            inferred_type=InferredColumnType.IDENTIFIER,
        )

        fk_metadata = ColumnMetadata(
            name="user_id",
            data_type="BIGINT",
            is_foreign_key=True,
            inferred_type=InferredColumnType.IDENTIFIER,
        )

        regular_metadata = ColumnMetadata(
            name="description",
            data_type="TEXT",
            nullable=True,
            inferred_type=InferredColumnType.STRING,
        )

        recommendations = [
            ColumnRecommendation(
                column_name="id",
                data_type="BIGINT",
                overall_confidence=0.95,
                signals=["Primary key"],
                suggested_checks=[
                    InferredCheck(CheckType.UNIQUENESS, confidence=0.95, priority=90),
                ],
                metadata=pk_metadata,
            ),
            ColumnRecommendation(
                column_name="user_id",
                data_type="BIGINT",
                overall_confidence=0.85,
                signals=["Foreign key"],
                suggested_checks=[
                    InferredCheck(CheckType.REFERENTIAL_INTEGRITY, confidence=0.85, priority=80),
                ],
                metadata=fk_metadata,
            ),
            ColumnRecommendation(
                column_name="description",
                data_type="TEXT",
                overall_confidence=0.5,
                signals=[],
                suggested_checks=[
                    InferredCheck(CheckType.COMPLETENESS, confidence=0.5, priority=60),
                ],
                metadata=regular_metadata,
            ),
        ]

        prioritized = prioritizer.prioritize_table_recommendations(recommendations)

        # All columns with checks should be returned
        assert len(prioritized) == 3

        # PK and FK should be prioritized over regular columns
        column_order = [r.column_name for r in prioritized]
        pk_pos = column_order.index("id")
        desc_pos = column_order.index("description")
        assert pk_pos < desc_pos  # PK should come before regular column


class TestRecommendationOutput:
    """Tests for recommendation output formatting."""

    def test_column_check_recommendation_format(self):
        """Test ColumnCheckRecommendation structure."""
        rec = ColumnCheckRecommendation(
            column="user_email",
            data_type="VARCHAR(255)",
            confidence=0.92,
            signals=["Email pattern match", "Non-nullable constraint"],
            suggested_checks=[
                {
                    "type": "format_email",
                    "confidence": 0.95,
                    "config": {"pattern": "email"},
                },
                {
                    "type": "completeness",
                    "confidence": 0.9,
                    "config": {"threshold": 0.99},
                },
            ],
        )

        assert rec.column == "user_email"
        assert rec.data_type == "VARCHAR(255)"
        assert rec.confidence == 0.92
        assert len(rec.signals) == 2
        assert len(rec.suggested_checks) == 2

    def test_recommendation_report_with_columns(self):
        """Test RecommendationReport includes column stats."""
        from datetime import datetime

        report = RecommendationReport(
            generated_at=datetime.now(),
            lookback_days=30,
            database_type="postgresql",
            recommended_tables=[],
            excluded_tables=[],
            total_tables_analyzed=5,
            total_recommended=3,
            total_excluded=2,
            confidence_distribution={"high": 3, "medium": 2, "low": 0},
            total_columns_analyzed=45,
            total_column_checks_recommended=120,
            column_confidence_distribution={
                "high": 80,
                "medium": 30,
                "low": 10,
            },
        )

        assert report.total_columns_analyzed == 45
        assert report.total_column_checks_recommended == 120
        assert report.column_confidence_distribution["high"] == 80


class TestPatternMatcherCustomRules:
    """Tests for custom pattern rules."""

    def test_add_custom_rule(self):
        """Test adding custom pattern rule."""
        matcher = PatternMatcher()

        # Add custom rule for company-specific pattern (using regex syntax)
        # Note: pattern_type must be "name" to match against column names
        from baselinr.smart_selection.column_analysis.pattern_matcher import PatternRule

        custom_rule = PatternRule(
            name="company_order_id",
            patterns=[r"^order_ref_.*", r".*_order_reference$"],  # regex patterns
            pattern_type="name",  # Must be "name" to match column names
            suggested_checks=["uniqueness", "format_alphanumeric"],
            confidence=0.9,
        )

        matcher.add_rule(custom_rule)

        # Should match custom pattern
        matches = matcher.match_column("order_ref_number")
        pattern_names = [m.pattern_name for m in matches]

        # Verify custom rule was added and can match
        assert len(matcher.rules) > len(PatternMatcher.DEFAULT_RULES)
        assert "company_order_id" in pattern_names

    def test_pattern_priority(self):
        """Test that more specific patterns have higher priority."""
        matcher = PatternMatcher()

        # Column that could match multiple patterns
        matches = matcher.match_column("created_at")

        if len(matches) > 1:
            # More specific matches should come first
            for i in range(len(matches) - 1):
                assert matches[i].confidence >= matches[i + 1].confidence


class TestEndToEndScenarios:
    """End-to-end scenario tests."""

    def test_ecommerce_table_columns(self):
        """Test recommendations for typical e-commerce table columns."""
        matcher = PatternMatcher()
        inferencer = CheckInferencer()

        columns = [
            ("order_id", "BIGINT", True, False),  # name, type, pk, fk
            ("customer_id", "BIGINT", False, True),
            ("order_date", "TIMESTAMP", False, False),
            ("total_amount", "DECIMAL(10,2)", False, False),
            ("status", "VARCHAR(50)", False, False),
            ("shipping_address", "TEXT", False, False),
            ("email", "VARCHAR(255)", False, False),
        ]

        recommendations = []
        for name, dtype, is_pk, is_fk in columns:
            matches = matcher.match_column(name)

            metadata = ColumnMetadata(
                name=name,
                data_type=dtype,
                is_primary_key=is_pk,
                is_foreign_key=is_fk,
                inferred_type=InferredColumnType.IDENTIFIER if "id" in name else InferredColumnType.STRING,
                name_patterns=[m.pattern_name for m in matches],
            )

            result = inferencer.infer_checks(metadata)
            recommendations.append(result)

        # Verify key columns got appropriate checks
        order_id_rec = next(r for r in recommendations if r.column_name == "order_id")
        assert any(c.check_type == CheckType.UNIQUENESS for c in order_id_rec.suggested_checks)

        customer_id_rec = next(r for r in recommendations if r.column_name == "customer_id")
        assert any(c.check_type == CheckType.REFERENTIAL_INTEGRITY for c in customer_id_rec.suggested_checks)

        email_rec = next(r for r in recommendations if r.column_name == "email")
        assert any(c.check_type == CheckType.FORMAT_EMAIL for c in email_rec.suggested_checks)

    def test_analytics_events_table(self):
        """Test recommendations for analytics events table."""
        matcher = PatternMatcher()
        inferencer = CheckInferencer()

        columns = [
            "event_id",
            "user_id",
            "event_timestamp",
            "event_type",
            "page_url",
            "session_id",
            "device_type",
            "is_mobile",
            "metadata_json",
        ]

        for column in columns:
            matches = matcher.match_column(column)

            # Just verify no crashes and reasonable output
            metadata = ColumnMetadata(
                name=column,
                data_type="VARCHAR(255)",  # Simplified
                inferred_type=InferredColumnType.STRING,
                name_patterns=[m.pattern_name for m in matches],
            )

            result = inferencer.infer_checks(metadata)
            assert result.column_name == column
