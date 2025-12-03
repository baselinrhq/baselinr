"""
Unit tests for smart column selection learning module.

Tests pattern learner and pattern store.
"""

import os
import tempfile
from pathlib import Path

import pytest

from baselinr.smart_selection.learning import LearnedPattern, PatternLearner, PatternStore


class TestPatternLearner:
    """Tests for PatternLearner."""

    @pytest.fixture
    def learner(self):
        """Create a pattern learner."""
        return PatternLearner(min_occurrences=2, min_confidence=0.5)

    def test_learn_from_columns_suffix_pattern(self, learner):
        """Test learning suffix patterns from columns."""
        columns = [
            {"name": "created_at", "checks": [{"type": "freshness"}, {"type": "completeness"}]},
            {"name": "updated_at", "checks": [{"type": "freshness"}, {"type": "completeness"}]},
            {"name": "deleted_at", "checks": [{"type": "freshness"}]},
        ]

        patterns = learner.learn_from_columns(columns)

        # Should learn _at suffix pattern
        suffix_patterns = [p for p in patterns if p.pattern_type == "suffix"]
        assert len(suffix_patterns) > 0

        # Check for freshness in suggested checks
        at_pattern = next((p for p in suffix_patterns if "_at" in p.pattern), None)
        if at_pattern:
            assert "freshness" in at_pattern.suggested_checks

    def test_learn_from_columns_prefix_pattern(self, learner):
        """Test learning prefix patterns from columns."""
        columns = [
            {"name": "is_active", "checks": [{"type": "completeness"}]},
            {"name": "is_verified", "checks": [{"type": "completeness"}]},
            {"name": "is_deleted", "checks": [{"type": "completeness"}]},
        ]

        patterns = learner.learn_from_columns(columns)

        # Should learn is_ prefix pattern
        prefix_patterns = [p for p in patterns if p.pattern_type == "prefix"]
        assert len(prefix_patterns) > 0

    def test_learn_from_config(self, learner):
        """Test learning patterns from config dictionary."""
        config = {
            "profiling": {
                "tables": [
                    {
                        "schema": "public",
                        "table": "users",
                        "columns": [
                            {"name": "user_id", "checks": [{"type": "uniqueness"}]},
                            {"name": "org_id", "checks": [{"type": "referential_integrity"}]},
                        ],
                    },
                    {
                        "schema": "public",
                        "table": "orders",
                        "columns": [
                            {"name": "order_id", "checks": [{"type": "uniqueness"}]},
                            {"name": "customer_id", "checks": [{"type": "referential_integrity"}]},
                        ],
                    },
                ]
            }
        }

        patterns = learner.learn_from_config(config)

        # Should learn _id suffix pattern
        suffix_patterns = [p for p in patterns if p.pattern_type == "suffix"]
        id_pattern = next((p for p in suffix_patterns if "_id" in p.pattern), None)

        if id_pattern:
            assert "uniqueness" in id_pattern.suggested_checks or \
                   "referential_integrity" in id_pattern.suggested_checks

    def test_min_occurrences_filter(self):
        """Test that min_occurrences filter works."""
        learner = PatternLearner(min_occurrences=3, min_confidence=0.5)

        # Only 2 occurrences - should not create pattern
        columns = [
            {"name": "email_address", "checks": [{"type": "format_email"}]},
            {"name": "work_email", "checks": [{"type": "format_email"}]},
        ]

        patterns = learner.learn_from_columns(columns)

        # Pattern should not be created with only 2 occurrences
        email_patterns = [p for p in patterns if "email" in p.pattern.lower()]
        assert len(email_patterns) == 0

    def test_learning_summary(self, learner):
        """Test getting learning summary."""
        columns = [
            {"name": "created_at", "checks": [{"type": "freshness"}]},
            {"name": "updated_at", "checks": [{"type": "freshness"}]},
        ]

        learner.learn_from_columns(columns)

        summary = learner.get_learning_summary()

        assert "suffix_patterns" in summary
        assert "prefix_patterns" in summary
        assert "exact_patterns" in summary

    def test_reset(self, learner):
        """Test resetting learned patterns."""
        columns = [
            {"name": "created_at", "checks": [{"type": "freshness"}]},
            {"name": "updated_at", "checks": [{"type": "freshness"}]},
        ]

        learner.learn_from_columns(columns)
        learner.reset()

        summary = learner.get_learning_summary()
        assert summary["suffix_patterns"] == 0


class TestLearnedPattern:
    """Tests for LearnedPattern dataclass."""

    def test_learned_pattern_basic(self):
        """Test LearnedPattern basic attributes."""
        pattern = LearnedPattern(
            pattern="*_at",
            pattern_type="suffix",
            suggested_checks=["freshness", "completeness"],
            confidence=0.85,
            source_columns=["created_at", "updated_at"],
            occurrence_count=5,
        )

        assert pattern.pattern == "*_at"
        assert pattern.pattern_type == "suffix"
        assert "freshness" in pattern.suggested_checks
        assert pattern.confidence == 0.85
        assert pattern.occurrence_count == 5

    def test_learned_pattern_to_dict(self):
        """Test LearnedPattern serialization."""
        pattern = LearnedPattern(
            pattern="is_*",
            pattern_type="prefix",
            suggested_checks=["completeness"],
            confidence=0.9,
        )

        result = pattern.to_dict()

        assert result["pattern"] == "is_*"
        assert result["pattern_type"] == "prefix"
        assert len(result["checks"]) == 1
        assert result["confidence"] == 0.9

    def test_learned_pattern_to_config_format(self):
        """Test conversion to config file format."""
        pattern = LearnedPattern(
            pattern="*_email",
            pattern_type="suffix",
            suggested_checks=["format_email", "completeness"],
            confidence=0.95,
        )

        result = pattern.to_config_format()

        assert result["match"] == "*_email"
        assert len(result["checks"]) == 2
        assert result["checks"][0]["type"] == "format_email"


class TestPatternStore:
    """Tests for PatternStore."""

    @pytest.fixture
    def temp_store_path(self):
        """Create a temporary storage path."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            path = f.name
        yield path
        # Cleanup
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def store(self, temp_store_path):
        """Create a pattern store with temp path."""
        return PatternStore(storage_path=temp_store_path, auto_save=False)

    def test_add_patterns(self, store):
        """Test adding patterns to store."""
        patterns = [
            LearnedPattern(
                pattern="*_at",
                pattern_type="suffix",
                suggested_checks=["freshness"],
                confidence=0.85,
            ),
            LearnedPattern(
                pattern="is_*",
                pattern_type="prefix",
                suggested_checks=["completeness"],
                confidence=0.9,
            ),
        ]

        added = store.add_patterns(patterns)

        assert added == 2
        assert len(store.get_patterns()) == 2

    def test_get_patterns_by_type(self, store):
        """Test getting patterns by type."""
        patterns = [
            LearnedPattern("*_at", "suffix", ["freshness"], 0.85),
            LearnedPattern("is_*", "prefix", ["completeness"], 0.9),
            LearnedPattern("*_id", "suffix", ["uniqueness"], 0.88),
        ]

        store.add_patterns(patterns)

        suffix_patterns = store.get_patterns(pattern_type="suffix")
        assert len(suffix_patterns) == 2

        prefix_patterns = store.get_patterns(pattern_type="prefix")
        assert len(prefix_patterns) == 1

    def test_get_patterns_min_confidence(self, store):
        """Test filtering patterns by confidence."""
        patterns = [
            LearnedPattern("*_at", "suffix", ["freshness"], 0.95),
            LearnedPattern("is_*", "prefix", ["completeness"], 0.7),
            LearnedPattern("*_id", "suffix", ["uniqueness"], 0.85),
        ]

        store.add_patterns(patterns)

        high_conf = store.get_patterns(min_confidence=0.9)
        assert len(high_conf) == 1
        assert high_conf[0].pattern == "*_at"

    def test_get_specific_pattern(self, store):
        """Test getting a specific pattern."""
        pattern = LearnedPattern("*_email", "suffix", ["format_email"], 0.92)
        store.add_patterns([pattern])

        result = store.get_pattern("*_email")

        assert result is not None
        assert result.pattern == "*_email"
        assert result.confidence == 0.92

    def test_remove_pattern(self, store):
        """Test removing a pattern."""
        patterns = [
            LearnedPattern("*_at", "suffix", ["freshness"], 0.85),
            LearnedPattern("is_*", "prefix", ["completeness"], 0.9),
        ]

        store.add_patterns(patterns)
        assert len(store.get_patterns()) == 2

        removed = store.remove_pattern("*_at")
        assert removed is True
        assert len(store.get_patterns()) == 1

    def test_clear_patterns(self, store):
        """Test clearing all patterns."""
        patterns = [
            LearnedPattern("*_at", "suffix", ["freshness"], 0.85),
            LearnedPattern("is_*", "prefix", ["completeness"], 0.9),
        ]

        store.add_patterns(patterns)
        store.clear()

        assert len(store.get_patterns()) == 0

    def test_save_and_load(self, temp_store_path):
        """Test saving and loading patterns."""
        # Create store and add patterns
        store1 = PatternStore(storage_path=temp_store_path, auto_save=False)
        patterns = [
            LearnedPattern("*_at", "suffix", ["freshness"], 0.85),
            LearnedPattern("is_*", "prefix", ["completeness"], 0.9),
        ]
        store1.add_patterns(patterns)
        store1.save()

        # Create new store and load
        store2 = PatternStore(storage_path=temp_store_path, auto_save=False)

        loaded = store2.get_patterns()
        assert len(loaded) == 2

        at_pattern = store2.get_pattern("*_at")
        assert at_pattern is not None
        assert at_pattern.confidence == 0.85

    def test_update_existing_pattern(self, store):
        """Test that adding existing pattern increases confidence."""
        pattern1 = LearnedPattern("*_at", "suffix", ["freshness"], 0.8, occurrence_count=1)
        store.add_patterns([pattern1])

        pattern2 = LearnedPattern("*_at", "suffix", ["freshness"], 0.85, occurrence_count=1)
        store.add_patterns([pattern2])

        result = store.get_pattern("*_at")
        # Confidence should increase
        assert result.confidence > 0.8
        # Occurrence count should accumulate
        assert result.occurrence_count == 2

    def test_export_to_config(self, store):
        """Test exporting patterns to config format."""
        patterns = [
            LearnedPattern("*_email", "suffix", ["format_email"], 0.95),
            LearnedPattern("is_*", "prefix", ["completeness"], 0.9),
        ]
        store.add_patterns(patterns)

        config = store.export_to_config()

        assert "patterns" in config
        assert len(config["patterns"]) == 2

    def test_import_from_config(self, store):
        """Test importing patterns from config format."""
        config = {
            "patterns": [
                {
                    "match": "*_email",
                    "checks": [
                        {"type": "format_email", "confidence": 0.95}
                    ],
                    "confidence": 0.95,
                },
                {
                    "match": "is_*",
                    "checks": ["completeness"],
                    "confidence": 0.9,
                },
            ]
        }

        imported = store.import_from_config(config)

        assert imported == 2
        assert len(store.get_patterns()) == 2

    def test_metadata(self, store):
        """Test store metadata."""
        metadata = store.get_metadata()

        assert "version" in metadata
        assert "pattern_count" in metadata
        assert metadata["pattern_count"] == 0

        store.add_patterns([
            LearnedPattern("*_at", "suffix", ["freshness"], 0.85)
        ])

        metadata = store.get_metadata()
        assert metadata["pattern_count"] == 1
