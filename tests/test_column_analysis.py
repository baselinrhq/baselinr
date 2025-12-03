"""
Unit tests for smart column selection column analysis module.

Tests metadata analyzer, statistical analyzer, pattern matcher, and check inferencer.
"""

import pytest

from baselinr.smart_selection.column_analysis import (
    CheckInferencer,
    ColumnMetadata,
    ColumnStatistics,
    InferredCheck,
    MetadataAnalyzer,
    PatternMatch,
    PatternMatcher,
    StatisticalAnalyzer,
)
from baselinr.smart_selection.column_analysis.check_inferencer import CheckType
from baselinr.smart_selection.column_analysis.metadata_analyzer import InferredColumnType


class TestMetadataAnalyzer:
    """Tests for MetadataAnalyzer and ColumnMetadata."""

    def test_column_metadata_basic(self):
        """Test ColumnMetadata basic attributes."""
        metadata = ColumnMetadata(
            name="user_id",
            data_type="INTEGER",
            nullable=False,
            position=0,
            is_primary_key=True,
        )

        assert metadata.name == "user_id"
        assert metadata.data_type == "INTEGER"
        assert metadata.nullable is False
        assert metadata.is_primary_key is True
        assert metadata.inferred_type == InferredColumnType.UNKNOWN

    def test_column_metadata_to_dict(self):
        """Test ColumnMetadata serialization."""
        metadata = ColumnMetadata(
            name="email",
            data_type="VARCHAR(255)",
            nullable=True,
            position=3,
            name_patterns=["format:email"],
            inferred_type=InferredColumnType.STRING,
        )

        result = metadata.to_dict()
        assert result["name"] == "email"
        assert result["data_type"] == "VARCHAR(255)"
        assert "format:email" in result["name_patterns"]
        assert result["inferred_type"] == "string"

    def test_inferred_column_types(self):
        """Test all InferredColumnType enum values."""
        assert InferredColumnType.TIMESTAMP.value == "timestamp"
        assert InferredColumnType.IDENTIFIER.value == "identifier"
        assert InferredColumnType.NUMERIC.value == "numeric"
        assert InferredColumnType.BOOLEAN.value == "boolean"
        assert InferredColumnType.JSON.value == "json"


class TestPatternMatcher:
    """Tests for PatternMatcher."""

    @pytest.fixture
    def matcher(self):
        """Create a default pattern matcher."""
        return PatternMatcher()

    def test_timestamp_patterns(self, matcher):
        """Test matching timestamp column patterns."""
        matches = matcher.match_column("created_at")
        assert len(matches) > 0

        # Check for timestamp-related pattern
        pattern_names = [m.pattern_name for m in matches]
        assert any("timestamp" in name for name in pattern_names)

    def test_identifier_patterns(self, matcher):
        """Test matching identifier column patterns."""
        matches = matcher.match_column("user_id")
        assert len(matches) > 0

        pattern_names = [m.pattern_name for m in matches]
        assert any("key" in name.lower() or "id" in name.lower() for name in pattern_names)

    def test_email_pattern(self, matcher):
        """Test matching email column pattern."""
        matches = matcher.match_column("email_address")
        assert len(matches) > 0

        pattern_names = [m.pattern_name for m in matches]
        assert "email" in pattern_names

    def test_phone_pattern(self, matcher):
        """Test matching phone column pattern."""
        matches = matcher.match_column("phone_number")
        assert len(matches) > 0

        pattern_names = [m.pattern_name for m in matches]
        assert "phone" in pattern_names

    def test_boolean_pattern(self, matcher):
        """Test matching boolean column patterns."""
        matches = matcher.match_column("is_active")
        assert len(matches) > 0

        pattern_names = [m.pattern_name for m in matches]
        assert any("boolean" in name for name in pattern_names)

    def test_status_pattern(self, matcher):
        """Test matching status/categorical column patterns."""
        matches = matcher.match_column("order_status")
        assert len(matches) > 0

        pattern_names = [m.pattern_name for m in matches]
        assert "status" in pattern_names

    def test_monetary_pattern(self, matcher):
        """Test matching monetary column patterns."""
        matches = matcher.match_column("total_amount")
        assert len(matches) > 0

        pattern_names = [m.pattern_name for m in matches]
        assert "monetary" in pattern_names

    def test_confidence_ordering(self, matcher):
        """Test that matches are ordered by confidence."""
        matches = matcher.match_column("user_id")

        if len(matches) > 1:
            for i in range(len(matches) - 1):
                assert matches[i].confidence >= matches[i + 1].confidence

    def test_no_match(self, matcher):
        """Test column with no pattern match."""
        matches = matcher.match_column("xyzzy_foobar_123")
        # May or may not match - just shouldn't crash
        assert isinstance(matches, list)

    def test_pattern_match_to_dict(self):
        """Test PatternMatch serialization."""
        match = PatternMatch(
            pattern_name="email",
            pattern_type="name",
            confidence=0.95,
            suggested_checks=["format_email", "completeness"],
        )

        result = match.to_dict()
        assert result["pattern_name"] == "email"
        assert result["confidence"] == 0.95
        assert "format_email" in result["suggested_checks"]

    def test_custom_pattern_from_config(self):
        """Test creating matcher from config."""
        config = {
            "patterns": [
                {
                    "match": "*_email",
                    "checks": [
                        {"type": "format_email", "confidence": 0.95}
                    ],
                    "confidence": 0.9,
                },
                {
                    "match": "revenue_*",
                    "checks": [
                        {"type": "non_negative"},
                        {"type": "distribution"},
                    ],
                    "confidence": 0.85,
                },
            ]
        }

        matcher = PatternMatcher.from_config(config)
        assert len(matcher.rules) > len(PatternMatcher.DEFAULT_RULES)


class TestColumnStatistics:
    """Tests for ColumnStatistics."""

    def test_column_statistics_basic(self):
        """Test ColumnStatistics basic attributes."""
        stats = ColumnStatistics(
            row_count=1000,
            null_count=50,
            null_percentage=5.0,
            distinct_count=100,
            unique_ratio=0.1,
        )

        assert stats.row_count == 1000
        assert stats.null_count == 50
        assert stats.null_percentage == 5.0
        assert stats.distinct_count == 100
        assert stats.unique_ratio == 0.1

    def test_column_statistics_to_dict(self):
        """Test ColumnStatistics serialization."""
        stats = ColumnStatistics(
            row_count=500,
            null_count=0,
            null_percentage=0.0,
            distinct_count=500,
            unique_ratio=1.0,
            cardinality_type="unique",
        )

        result = stats.to_dict()
        assert result["row_count"] == 500
        assert result["unique_ratio"] == 1.0
        assert result["cardinality_type"] == "unique"

    def test_cardinality_types(self):
        """Test different cardinality type classifications."""
        # Binary
        binary_stats = ColumnStatistics(distinct_count=2)
        assert binary_stats.cardinality_type is None  # Must be set externally

        # The analyzer sets cardinality_type based on thresholds
        stats = ColumnStatistics(cardinality_type="binary")
        assert stats.cardinality_type == "binary"


class TestCheckInferencer:
    """Tests for CheckInferencer."""

    @pytest.fixture
    def inferencer(self):
        """Create a default check inferencer."""
        return CheckInferencer()

    def test_infer_timestamp_checks(self, inferencer):
        """Test inferring checks for timestamp columns."""
        metadata = ColumnMetadata(
            name="created_at",
            data_type="TIMESTAMP",
            nullable=False,
            inferred_type=InferredColumnType.TIMESTAMP,
            name_patterns=["timestamp"],
        )

        result = inferencer.infer_checks(metadata)

        assert result.column_name == "created_at"
        check_types = [c.check_type for c in result.suggested_checks]

        # Should suggest freshness and/or completeness for timestamp
        assert any(ct in check_types for ct in [CheckType.FRESHNESS, CheckType.COMPLETENESS])

    def test_infer_primary_key_checks(self, inferencer):
        """Test inferring checks for primary key columns."""
        metadata = ColumnMetadata(
            name="id",
            data_type="INTEGER",
            nullable=False,
            is_primary_key=True,
            inferred_type=InferredColumnType.IDENTIFIER,
        )

        result = inferencer.infer_checks(metadata)

        check_types = [c.check_type for c in result.suggested_checks]

        # Primary key should have uniqueness and completeness
        assert CheckType.UNIQUENESS in check_types
        assert CheckType.COMPLETENESS in check_types

    def test_infer_foreign_key_checks(self, inferencer):
        """Test inferring checks for foreign key columns."""
        metadata = ColumnMetadata(
            name="user_id",
            data_type="INTEGER",
            nullable=True,
            is_foreign_key=True,
            foreign_key_references="users.id",
            inferred_type=InferredColumnType.IDENTIFIER,
        )

        result = inferencer.infer_checks(metadata)

        check_types = [c.check_type for c in result.suggested_checks]

        # Foreign key should have referential integrity
        assert CheckType.REFERENTIAL_INTEGRITY in check_types

    def test_infer_email_checks(self, inferencer):
        """Test inferring checks for email columns."""
        metadata = ColumnMetadata(
            name="email_address",
            data_type="VARCHAR(255)",
            nullable=True,
            inferred_type=InferredColumnType.STRING,
            name_patterns=["format:email"],
        )

        result = inferencer.infer_checks(metadata)

        check_types = [c.check_type for c in result.suggested_checks]

        # Email should have format validation
        assert CheckType.FORMAT_EMAIL in check_types

    def test_infer_numeric_checks(self, inferencer):
        """Test inferring checks for numeric columns."""
        metadata = ColumnMetadata(
            name="price_amount",
            data_type="DECIMAL(10,2)",
            nullable=True,
            inferred_type=InferredColumnType.NUMERIC,
            name_patterns=["numeric"],
        )

        statistics = ColumnStatistics(
            row_count=1000,
            null_count=0,
            null_percentage=0.0,
            distinct_count=500,
            unique_ratio=0.5,
            min_value=0.0,
            max_value=1000.0,
        )

        result = inferencer.infer_checks(metadata, statistics)

        check_types = [c.check_type for c in result.suggested_checks]

        # Monetary columns should have non_negative and/or range
        assert any(ct in check_types for ct in [CheckType.NON_NEGATIVE, CheckType.RANGE])

    def test_infer_boolean_checks(self, inferencer):
        """Test inferring checks for boolean columns."""
        metadata = ColumnMetadata(
            name="is_verified",
            data_type="BOOLEAN",
            nullable=True,
            inferred_type=InferredColumnType.BOOLEAN,
            name_patterns=["boolean"],
        )

        result = inferencer.infer_checks(metadata)

        check_types = [c.check_type for c in result.suggested_checks]

        # Boolean should have completeness
        assert CheckType.COMPLETENESS in check_types

    def test_infer_categorical_checks(self, inferencer):
        """Test inferring checks for categorical columns."""
        metadata = ColumnMetadata(
            name="status",
            data_type="VARCHAR(50)",
            nullable=False,
            inferred_type=InferredColumnType.CATEGORICAL,
            name_patterns=["categorical"],
        )

        statistics = ColumnStatistics(
            row_count=10000,
            null_count=0,
            null_percentage=0.0,
            distinct_count=5,
            unique_ratio=0.0005,
            cardinality_type="low",
            value_distribution={"active": 5000, "inactive": 3000, "pending": 2000},
        )

        result = inferencer.infer_checks(metadata, statistics)

        check_types = [c.check_type for c in result.suggested_checks]

        # Categorical should have allowed_values
        assert CheckType.ALLOWED_VALUES in check_types

    def test_infer_checks_max_limit(self):
        """Test that max_checks_per_column limit is respected."""
        inferencer = CheckInferencer(max_checks_per_column=2)

        metadata = ColumnMetadata(
            name="id",
            data_type="INTEGER",
            nullable=False,
            is_primary_key=True,
            inferred_type=InferredColumnType.IDENTIFIER,
        )

        result = inferencer.infer_checks(metadata)

        # Should not exceed max limit
        assert len(result.suggested_checks) <= 2

    def test_inferred_check_to_dict(self):
        """Test InferredCheck serialization."""
        check = InferredCheck(
            check_type=CheckType.UNIQUENESS,
            confidence=0.95,
            signals=["Primary key"],
            config={"threshold": 1.0},
            priority=90,
        )

        result = check.to_dict()
        assert result["type"] == "uniqueness"
        assert result["confidence"] == 0.95
        assert "Primary key" in result["signals"]

    def test_confidence_threshold(self):
        """Test that confidence threshold filters checks."""
        inferencer = CheckInferencer(confidence_threshold=0.9)

        metadata = ColumnMetadata(
            name="maybe_id",
            data_type="VARCHAR(255)",
            nullable=True,
            inferred_type=InferredColumnType.STRING,
        )

        result = inferencer.infer_checks(metadata)

        # All suggested checks should meet threshold
        for check in result.suggested_checks:
            assert check.confidence >= 0.9 or len(result.suggested_checks) == 0


class TestCheckType:
    """Tests for CheckType enum."""

    def test_check_type_values(self):
        """Test CheckType enum values."""
        assert CheckType.COMPLETENESS.value == "completeness"
        assert CheckType.UNIQUENESS.value == "uniqueness"
        assert CheckType.FRESHNESS.value == "freshness"
        assert CheckType.FORMAT_EMAIL.value == "format_email"
        assert CheckType.NON_NEGATIVE.value == "non_negative"
        assert CheckType.ALLOWED_VALUES.value == "allowed_values"
        assert CheckType.VALID_JSON.value == "valid_json"
