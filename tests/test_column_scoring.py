"""
Unit tests for smart column selection scoring module.

Tests confidence scorer and check prioritizer.
"""

import pytest

from baselinr.smart_selection.column_analysis import (
    ColumnMetadata,
    ColumnStatistics,
    InferredCheck,
)
from baselinr.smart_selection.column_analysis.check_inferencer import (
    CheckType,
    ColumnRecommendation,
)
from baselinr.smart_selection.column_analysis.metadata_analyzer import InferredColumnType
from baselinr.smart_selection.scoring import CheckPrioritizer, ConfidenceScorer
from baselinr.smart_selection.scoring.check_prioritizer import PrioritizationConfig


class TestConfidenceScorer:
    """Tests for ConfidenceScorer."""

    @pytest.fixture
    def scorer(self):
        """Create a default confidence scorer."""
        return ConfidenceScorer()

    def test_score_recommendation_basic(self, scorer):
        """Test basic recommendation scoring."""
        metadata = ColumnMetadata(
            name="id",
            data_type="INTEGER",
            nullable=False,
            is_primary_key=True,
            inferred_type=InferredColumnType.IDENTIFIER,
        )

        check = InferredCheck(
            check_type=CheckType.UNIQUENESS,
            confidence=0.95,
            signals=["Primary key"],
        )

        recommendation = ColumnRecommendation(
            column_name="id",
            data_type="INTEGER",
            overall_confidence=0.0,  # Will be calculated
            signals=["Primary key indicator"],
            suggested_checks=[check],
            metadata=metadata,
        )

        score = scorer.score_recommendation(recommendation)

        assert 0.0 <= score <= 1.0
        # Primary key should have high score
        assert score >= 0.5

    def test_score_recommendation_with_statistics(self, scorer):
        """Test scoring with statistical data."""
        metadata = ColumnMetadata(
            name="user_id",
            data_type="BIGINT",
            nullable=False,
            inferred_type=InferredColumnType.IDENTIFIER,
        )

        statistics = ColumnStatistics(
            row_count=10000,
            null_count=0,
            null_percentage=0.0,
            distinct_count=10000,
            unique_ratio=1.0,
            cardinality_type="unique",
        )

        check = InferredCheck(
            check_type=CheckType.UNIQUENESS,
            confidence=0.9,
            signals=["High uniqueness ratio"],
        )

        recommendation = ColumnRecommendation(
            column_name="user_id",
            data_type="BIGINT",
            overall_confidence=0.0,
            signals=["100% unique values"],
            suggested_checks=[check],
            metadata=metadata,
            statistics=statistics,
        )

        score = scorer.score_recommendation(recommendation)

        # Should score higher with statistics
        assert score >= 0.5

    def test_score_check(self, scorer):
        """Test scoring individual checks."""
        metadata = ColumnMetadata(
            name="email",
            data_type="VARCHAR(255)",
            nullable=True,
            inferred_type=InferredColumnType.STRING,
        )

        check = InferredCheck(
            check_type=CheckType.FORMAT_EMAIL,
            confidence=0.85,
            signals=["Email pattern match"],
        )

        score = scorer.score_check(check, metadata)

        assert 0.0 <= score <= 1.0
        assert score >= 0.8  # Base confidence is 0.85

    def test_categorize_confidence(self, scorer):
        """Test confidence categorization."""
        assert scorer.categorize_confidence(0.9) == "high"
        assert scorer.categorize_confidence(0.65) == "medium"
        assert scorer.categorize_confidence(0.4) == "low"

    def test_boost_primary_keys(self):
        """Test primary key boost."""
        scorer = ConfidenceScorer(boost_primary_keys=True)

        # With primary key
        pk_metadata = ColumnMetadata(
            name="id",
            data_type="INTEGER",
            is_primary_key=True,
            inferred_type=InferredColumnType.IDENTIFIER,
        )

        # Without primary key
        regular_metadata = ColumnMetadata(
            name="name",
            data_type="VARCHAR(255)",
            is_primary_key=False,
            inferred_type=InferredColumnType.STRING,
        )

        pk_rec = ColumnRecommendation(
            column_name="id",
            data_type="INTEGER",
            overall_confidence=0.0,
            signals=[],
            suggested_checks=[],
            metadata=pk_metadata,
        )

        regular_rec = ColumnRecommendation(
            column_name="name",
            data_type="VARCHAR(255)",
            overall_confidence=0.0,
            signals=[],
            suggested_checks=[],
            metadata=regular_metadata,
        )

        pk_score = scorer.score_recommendation(pk_rec)
        regular_score = scorer.score_recommendation(regular_rec)

        # Primary key should score at least as high
        assert pk_score >= regular_score

    def test_penalize_missing_stats(self):
        """Test penalty for missing statistics."""
        scorer = ConfidenceScorer(penalize_missing_stats=True)

        metadata = ColumnMetadata(
            name="test_col",
            data_type="VARCHAR(255)",
            inferred_type=InferredColumnType.STRING,
        )

        rec_no_stats = ColumnRecommendation(
            column_name="test_col",
            data_type="VARCHAR(255)",
            overall_confidence=0.0,
            signals=[],
            suggested_checks=[],
            metadata=metadata,
            statistics=None,
        )

        rec_with_stats = ColumnRecommendation(
            column_name="test_col",
            data_type="VARCHAR(255)",
            overall_confidence=0.0,
            signals=[],
            suggested_checks=[],
            metadata=metadata,
            statistics=ColumnStatistics(row_count=1000),
        )

        score_no_stats = scorer.score_recommendation(rec_no_stats)
        score_with_stats = scorer.score_recommendation(rec_with_stats)

        # Having stats should score higher
        assert score_with_stats >= score_no_stats


class TestCheckPrioritizer:
    """Tests for CheckPrioritizer."""

    @pytest.fixture
    def prioritizer(self):
        """Create a default check prioritizer."""
        return CheckPrioritizer()

    def test_prioritize_column_checks_basic(self, prioritizer):
        """Test basic check prioritization."""
        metadata = ColumnMetadata(
            name="id",
            data_type="INTEGER",
            is_primary_key=True,
            inferred_type=InferredColumnType.IDENTIFIER,
        )

        checks = [
            InferredCheck(
                check_type=CheckType.UNIQUENESS,
                confidence=0.95,
                signals=["Primary key"],
                priority=90,
            ),
            InferredCheck(
                check_type=CheckType.COMPLETENESS,
                confidence=0.90,
                signals=["Primary key should not be null"],
                priority=80,
            ),
            InferredCheck(
                check_type=CheckType.FORMAT_UUID,
                confidence=0.5,
                signals=["Might be UUID"],
                priority=60,
            ),
        ]

        recommendation = ColumnRecommendation(
            column_name="id",
            data_type="INTEGER",
            overall_confidence=0.9,
            signals=[],
            suggested_checks=checks,
            metadata=metadata,
        )

        prioritized = prioritizer.prioritize_column_checks(recommendation)

        # Should be ordered by priority/confidence
        assert len(prioritized.suggested_checks) <= len(checks)
        if len(prioritized.suggested_checks) > 1:
            # First check should have higher or equal priority
            first = prioritized.suggested_checks[0]
            second = prioritized.suggested_checks[1]
            assert first.priority >= second.priority or first.confidence >= second.confidence

    def test_prioritize_table_recommendations(self, prioritizer):
        """Test table-level prioritization."""
        metadata1 = ColumnMetadata(
            name="id",
            data_type="INTEGER",
            is_primary_key=True,
            inferred_type=InferredColumnType.IDENTIFIER,
        )

        metadata2 = ColumnMetadata(
            name="name",
            data_type="VARCHAR(255)",
            inferred_type=InferredColumnType.STRING,
        )

        rec1 = ColumnRecommendation(
            column_name="id",
            data_type="INTEGER",
            overall_confidence=0.95,
            signals=[],
            suggested_checks=[
                InferredCheck(CheckType.UNIQUENESS, confidence=0.95, priority=90)
            ],
            metadata=metadata1,
        )

        rec2 = ColumnRecommendation(
            column_name="name",
            data_type="VARCHAR(255)",
            overall_confidence=0.6,
            signals=[],
            suggested_checks=[
                InferredCheck(CheckType.COMPLETENESS, confidence=0.6, priority=70)
            ],
            metadata=metadata2,
        )

        results = prioritizer.prioritize_table_recommendations([rec1, rec2])

        assert len(results) >= 1
        # Primary key column should be prioritized
        assert results[0].column_name == "id"

    def test_max_checks_per_column(self):
        """Test max checks per column limit."""
        config = PrioritizationConfig(max_checks_per_column=2)
        prioritizer = CheckPrioritizer(config=config)

        metadata = ColumnMetadata(
            name="test",
            data_type="VARCHAR(255)",
            inferred_type=InferredColumnType.STRING,
        )

        checks = [
            InferredCheck(CheckType.COMPLETENESS, confidence=0.9, priority=90),
            InferredCheck(CheckType.FORMAT_EMAIL, confidence=0.85, priority=80),
            InferredCheck(CheckType.ALLOWED_VALUES, confidence=0.8, priority=70),
            InferredCheck(CheckType.DISTRIBUTION, confidence=0.7, priority=60),
        ]

        recommendation = ColumnRecommendation(
            column_name="test",
            data_type="VARCHAR(255)",
            overall_confidence=0.8,
            signals=[],
            suggested_checks=checks,
            metadata=metadata,
        )

        prioritized = prioritizer.prioritize_column_checks(recommendation)

        assert len(prioritized.suggested_checks) <= 2

    def test_confidence_filtering(self):
        """Test minimum confidence filtering."""
        config = PrioritizationConfig(min_confidence=0.7)
        prioritizer = CheckPrioritizer(config=config)

        metadata = ColumnMetadata(
            name="test",
            data_type="VARCHAR(255)",
            inferred_type=InferredColumnType.STRING,
        )

        checks = [
            InferredCheck(CheckType.COMPLETENESS, confidence=0.9, priority=90),
            InferredCheck(CheckType.FORMAT_EMAIL, confidence=0.5, priority=80),  # Below threshold
            InferredCheck(CheckType.ALLOWED_VALUES, confidence=0.8, priority=70),
        ]

        recommendation = ColumnRecommendation(
            column_name="test",
            data_type="VARCHAR(255)",
            overall_confidence=0.8,
            signals=[],
            suggested_checks=checks,
            metadata=metadata,
        )

        prioritized = prioritizer.prioritize_column_checks(recommendation)

        # Check below threshold should be filtered
        check_types = [c.check_type for c in prioritized.suggested_checks]
        assert CheckType.FORMAT_EMAIL not in check_types

    def test_preferred_checks_boost(self):
        """Test that preferred checks are boosted."""
        config = PrioritizationConfig(
            preferred_checks=["freshness"],
            max_checks_per_column=1,
        )
        prioritizer = CheckPrioritizer(config=config)

        metadata = ColumnMetadata(
            name="updated_at",
            data_type="TIMESTAMP",
            inferred_type=InferredColumnType.TIMESTAMP,
        )

        checks = [
            InferredCheck(CheckType.COMPLETENESS, confidence=0.9, priority=80),
            InferredCheck(CheckType.FRESHNESS, confidence=0.85, priority=70),
        ]

        recommendation = ColumnRecommendation(
            column_name="updated_at",
            data_type="TIMESTAMP",
            overall_confidence=0.8,
            signals=[],
            suggested_checks=checks,
            metadata=metadata,
        )

        prioritized = prioritizer.prioritize_column_checks(recommendation)

        # Freshness should be prioritized due to preference boost
        if prioritized.suggested_checks:
            assert prioritized.suggested_checks[0].check_type == CheckType.FRESHNESS

    def test_avoided_checks_filtered(self):
        """Test that avoided checks are filtered."""
        config = PrioritizationConfig(avoided_checks=["distribution"])
        prioritizer = CheckPrioritizer(config=config)

        metadata = ColumnMetadata(
            name="amount",
            data_type="DECIMAL(10,2)",
            inferred_type=InferredColumnType.NUMERIC,
        )

        checks = [
            InferredCheck(CheckType.COMPLETENESS, confidence=0.9, priority=80),
            InferredCheck(CheckType.DISTRIBUTION, confidence=0.85, priority=70),
            InferredCheck(CheckType.RANGE, confidence=0.8, priority=60),
        ]

        recommendation = ColumnRecommendation(
            column_name="amount",
            data_type="DECIMAL(10,2)",
            overall_confidence=0.8,
            signals=[],
            suggested_checks=checks,
            metadata=metadata,
        )

        prioritized = prioritizer.prioritize_column_checks(recommendation)

        check_types = [c.check_type for c in prioritized.suggested_checks]
        assert CheckType.DISTRIBUTION not in check_types

    def test_prioritization_summary(self, prioritizer):
        """Test prioritization summary generation."""
        metadata = ColumnMetadata(
            name="id",
            data_type="INTEGER",
            inferred_type=InferredColumnType.IDENTIFIER,
        )

        recommendations = [
            ColumnRecommendation(
                column_name="id",
                data_type="INTEGER",
                overall_confidence=0.9,
                signals=[],
                suggested_checks=[
                    InferredCheck(CheckType.UNIQUENESS, confidence=0.95, priority=90),
                    InferredCheck(CheckType.COMPLETENESS, confidence=0.9, priority=80),
                ],
                metadata=metadata,
            ),
            ColumnRecommendation(
                column_name="name",
                data_type="VARCHAR(255)",
                overall_confidence=0.7,
                signals=[],
                suggested_checks=[
                    InferredCheck(CheckType.COMPLETENESS, confidence=0.7, priority=70),
                ],
                metadata=metadata,
            ),
        ]

        summary = prioritizer.get_prioritization_summary(recommendations)

        assert summary["total_columns_with_recommendations"] == 2
        assert summary["total_checks"] == 3
        assert summary["high_confidence_checks"] >= 2
        assert "uniqueness" in summary["check_type_distribution"]


class TestPrioritizationConfig:
    """Tests for PrioritizationConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PrioritizationConfig()

        assert config.max_checks_per_column == 5
        assert config.max_checks_per_table == 50
        assert config.min_confidence == 0.5
        assert "completeness" in config.preferred_checks
        assert config.prioritize_primary_keys is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = PrioritizationConfig(
            max_checks_per_column=3,
            min_confidence=0.8,
            preferred_checks=["uniqueness", "freshness"],
            avoided_checks=["distribution"],
        )

        assert config.max_checks_per_column == 3
        assert config.min_confidence == 0.8
        assert "uniqueness" in config.preferred_checks
        assert "distribution" in config.avoided_checks
