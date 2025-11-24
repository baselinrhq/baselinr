"""
Tests for table pattern matching and expansion functionality.
"""

import re

import pytest

from baselinr.config.schema import TablePattern
from baselinr.profiling.table_matcher import RegexValidator, TableMatcher


class TestRegexValidator:
    """Tests for RegexValidator utility class."""

    def test_validate_valid_regex(self):
        """Test validation of valid regex patterns."""
        assert RegexValidator.validate_pattern("^test.*$") is True
        assert RegexValidator.validate_pattern(r"\d{4}") is True
        assert RegexValidator.validate_pattern("[a-z]+") is True

    def test_validate_invalid_regex(self):
        """Test validation of invalid regex patterns."""
        assert RegexValidator.validate_pattern("[unclosed") is False
        assert RegexValidator.validate_pattern("*invalid") is False  # * at start without anchor

    def test_compile_valid_regex(self):
        """Test compiling valid regex patterns."""
        pattern = RegexValidator.validate_and_compile("^test.*$")
        assert pattern.match("test123") is not None
        assert pattern.match("not_test") is None

    def test_compile_invalid_regex(self):
        """Test compiling invalid regex raises ValueError."""
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            RegexValidator.validate_and_compile("[unclosed")

    def test_wildcard_to_regex_simple(self):
        """Test simple wildcard to regex conversion."""
        regex = RegexValidator.wildcard_to_regex("test*")
        assert regex == "^test.*$"
        assert re.match(regex, "test123") is not None
        assert re.match(regex, "not_test") is None

    def test_wildcard_to_regex_question_mark(self):
        """Test wildcard with question mark."""
        regex = RegexValidator.wildcard_to_regex("test?")
        assert regex == "^test.$"
        assert re.match(regex, "test1") is not None
        assert re.match(regex, "test") is None
        assert re.match(regex, "test12") is None

    def test_wildcard_to_regex_escapes(self):
        """Test wildcard with special characters."""
        regex = RegexValidator.wildcard_to_regex("test*.csv")
        # Pattern: test*.csv
        # * becomes .*, . needs escaping to \.
        # So: test.*\.csv
        assert regex == "^test.*\\.csv$"
        assert re.match(regex, "test123.csv") is not None
        assert re.match(regex, "test_file.csv") is not None
        assert re.match(regex, "test.csv") is not None
        assert re.match(regex, "test123csv") is None  # Missing .

    def test_wildcard_character_class(self):
        """Test wildcard with character class."""
        regex = RegexValidator.wildcard_to_regex("test[0-9]*")
        assert regex.startswith("^test")
        assert "[0-9]" in regex
        assert regex.endswith(".*$")


class TestTableMatcher:
    """Tests for TableMatcher class."""

    def test_wildcard_matching(self):
        """Test wildcard pattern matching."""
        matcher = TableMatcher(validate_regex=False)

        # Basic wildcard
        assert matcher.match_table("users", "users") is True
        assert matcher.match_table("users", "user*") is True
        assert matcher.match_table("users", "user") is False

        # Prefix matching
        assert matcher.match_table("user_profile", "user_*") is True
        assert matcher.match_table("customer_profile", "user_*") is False

        # Suffix matching
        assert matcher.match_table("data_staging", "*_staging") is True
        assert matcher.match_table("data_production", "*_staging") is False

        # Question mark
        assert matcher.match_table("test1", "test?") is True
        assert matcher.match_table("test", "test?") is False

    def test_regex_matching(self):
        """Test regex pattern matching."""
        matcher = TableMatcher(validate_regex=True)

        # Simple regex
        assert matcher.match_table("test123", "^test\\d+$", "regex") is True
        assert matcher.match_table("testabc", "^test\\d+$", "regex") is False

        # Complex regex
        assert matcher.match_table("customer_2024", "^(customer|order)_\\d{4}$", "regex") is True
        assert matcher.match_table("order_2024", "^(customer|order)_\\d{4}$", "regex") is True
        assert matcher.match_table("product_2024", "^(customer|order)_\\d{4}$", "regex") is False

    def test_regex_validation_error(self):
        """Test that invalid regex raises error."""
        matcher = TableMatcher(validate_regex=True)

        with pytest.raises(ValueError, match="Invalid regex pattern"):
            matcher.match_table("test", "[unclosed", "regex")

    def test_exclude_patterns(self):
        """Test exclude pattern matching."""
        matcher = TableMatcher(validate_regex=False)

        assert matcher.matches_exclude_patterns("users", ["*_temp", "*_backup"]) is False
        assert matcher.matches_exclude_patterns("users_temp", ["*_temp", "*_backup"]) is True
        assert matcher.matches_exclude_patterns("users_backup", ["*_temp", "*_backup"]) is True

    def test_filter_tables(self):
        """Test filtering list of tables."""
        matcher = TableMatcher(validate_regex=False)

        tables = ["users", "user_profile", "user_settings", "customers", "orders"]

        # Include pattern
        filtered = matcher.filter_tables(tables, pattern="user*", pattern_type="wildcard")
        assert filtered == ["users", "user_profile", "user_settings"]

        # Exclude patterns
        filtered = matcher.filter_tables(
            tables, pattern="*", exclude_patterns=["*_temp", "*_backup"]
        )
        assert all("_temp" not in t and "_backup" not in t for t in filtered)

        # Combined
        filtered = matcher.filter_tables(
            tables, pattern="user*", exclude_patterns=["*_temp"]
        )
        assert "user_profile" in filtered
        assert "user_temp" not in filtered if "user_temp" in tables else True

    def test_resolve_priority(self):
        """Test priority-based resolution."""
        matcher = TableMatcher()

        # Test deduplication with priorities
        matches = [
            ("users", 10),  # Pattern match
            ("users", 100),  # Explicit table (higher priority)
            ("orders", 10),
        ]

        resolved = matcher.resolve_priority(matches, keep_highest=True)
        assert len(resolved) == 2
        assert "users" in resolved
        assert "orders" in resolved
        # Highest priority should come first
        assert resolved[0] == "users"  # priority 100

        # Test with lower priority
        matches = [
            ("users", 100),
            ("users", 10),
        ]
        resolved = matcher.resolve_priority(matches, keep_highest=True)
        assert resolved == ["users"]


class TestTablePatternSchema:
    """Tests for TablePattern schema validation."""

    def test_explicit_table(self):
        """Test explicit table pattern."""
        pattern = TablePattern(table="users", schema="public")
        assert pattern.table == "users"
        assert pattern.schema_ == "public"

    def test_pattern_table(self):
        """Test pattern-based table selection."""
        pattern = TablePattern(pattern="user_*", schema="public", pattern_type="wildcard")
        assert pattern.pattern == "user_*"
        assert pattern.pattern_type == "wildcard"
        assert pattern.table is None

    def test_regex_pattern(self):
        """Test regex pattern."""
        pattern = TablePattern(
            pattern="^(user|customer)_\\d{4}$", schema="public", pattern_type="regex"
        )
        assert pattern.pattern_type == "regex"

    def test_schema_level_selection(self):
        """Test schema-level selection."""
        pattern = TablePattern(select_schema=True, schema="analytics")
        assert pattern.select_schema is True
        assert pattern.schema_ == "analytics"

    def test_database_level_selection(self):
        """Test database-level selection."""
        pattern = TablePattern(select_all_schemas=True)
        assert pattern.select_all_schemas is True

    def test_tag_based_selection(self):
        """Test tag-based selection."""
        # Tags require at least one selection method
        pattern = TablePattern(
            tags=["critical", "customer_data"],
            schema="public",
            select_schema=True,
        )
        assert pattern.tags == ["critical", "customer_data"]

    def test_exclude_patterns(self):
        """Test exclude patterns."""
        pattern = TablePattern(
            pattern="*", schema="public", exclude_patterns=["*_temp", "*_backup"]
        )
        assert pattern.exclude_patterns == ["*_temp", "*_backup"]

    def test_override_priority(self):
        """Test override priority."""
        pattern = TablePattern(table="users", schema="public", override_priority=50)
        assert pattern.override_priority == 50

    def test_validation_requires_table_or_pattern(self):
        """Test that pattern requires either table or pattern/select fields."""
        # Explicit table - valid
        TablePattern(table="users")

        # Pattern - valid
        TablePattern(pattern="user_*")

        # Select schema - valid
        TablePattern(select_schema=True, schema="public")

        # Select all schemas - valid
        TablePattern(select_all_schemas=True)

        # None of the above - invalid
        with pytest.raises(ValueError, match="must specify either"):
            TablePattern()

    def test_pattern_type_validation(self):
        """Test pattern type validation."""
        # Valid types
        TablePattern(pattern="test", pattern_type="wildcard")
        TablePattern(pattern="test", pattern_type="regex")

        # Invalid type
        with pytest.raises(ValueError, match="pattern_type must be"):
            TablePattern(pattern="test", pattern_type="invalid")

    def test_database_field(self):
        """Test database field in TablePattern."""
        # Explicit table with database
        pattern = TablePattern(table="users", schema="public", database="analytics_db")
        assert pattern.database == "analytics_db"
        assert pattern.table == "users"
        assert pattern.schema_ == "public"

        # Pattern with database
        pattern = TablePattern(pattern="user_*", schema="public", database="warehouse_db")
        assert pattern.database == "warehouse_db"
        assert pattern.pattern == "user_*"

        # Schema selection with database
        pattern = TablePattern(select_schema=True, schema="analytics", database="production_db")
        assert pattern.database == "production_db"
        assert pattern.select_schema is True

        # Database-level selection with database (redundant but valid)
        pattern = TablePattern(select_all_schemas=True, database="staging_db")
        assert pattern.database == "staging_db"
        assert pattern.select_all_schemas is True

        # Database field is optional (backward compatible)
        pattern = TablePattern(table="users", schema="public")
        assert pattern.database is None

