"""
Table pattern matching engine for Baselinr.

Handles wildcard pattern matching, regex pattern matching, schema pattern matching,
and priority-based resolution for table selection.
"""

import re
from typing import List, Optional, Pattern, Tuple


class RegexValidator:
    """Utility class for validating and compiling regex patterns."""

    @staticmethod
    def validate_and_compile(pattern: str) -> Pattern[str]:
        """
        Validate and compile a regex pattern.

        Args:
            pattern: Regex pattern string to validate

        Returns:
            Compiled regex pattern object

        Raises:
            ValueError: If pattern is invalid
        """
        try:
            return re.compile(pattern)
        except re.error as e:
            raise ValueError(
                f"Invalid regex pattern '{pattern}': {e}. " "Please check your regex syntax."
            ) from e

    @staticmethod
    def validate_pattern(pattern: str) -> bool:
        """
        Validate a regex pattern without compiling.

        Args:
            pattern: Regex pattern string to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            re.compile(pattern)
            return True
        except re.error:
            return False

    @staticmethod
    def wildcard_to_regex(pattern: str) -> str:
        """
        Convert wildcard pattern to regex pattern.

        Supports:
        - `*` matches zero or more characters
        - `?` matches exactly one character
        - Character classes like `[abc]` or `[a-z]` are preserved

        Args:
            pattern: Wildcard pattern string

        Returns:
            Regex pattern string (anchored with ^ and $)
        """
        regex_parts = []
        i = 0
        pattern_len = len(pattern)

        while i < pattern_len:
            char = pattern[i]

            if char == "*":
                regex_parts.append(".*")
            elif char == "?":
                regex_parts.append(".")
            elif char == "[":
                # Character class - copy until closing ]
                regex_parts.append("[")
                i += 1
                in_class = True
                while i < pattern_len and in_class:
                    next_char = pattern[i]
                    regex_parts.append(next_char)
                    if next_char == "]":
                        in_class = False
                    elif next_char == "\\" and i + 1 < pattern_len:
                        # Escape sequence in character class
                        i += 1
                        if i < pattern_len:
                            regex_parts.append(pattern[i])
                    i += 1
                if in_class:
                    # Unclosed bracket, escape as literal
                    regex_parts = regex_parts[:-1]  # Remove the '['
                    regex_parts.append("\\[")

                # Don't increment i at end, already past closing bracket
                continue
            elif char == "\\":
                # Escape sequence - preserve next character as-is
                if i + 1 < pattern_len:
                    i += 1
                    regex_parts.append(pattern[i])
                else:
                    # Backslash at end, escape it
                    regex_parts.append("\\\\")
            else:
                # Escape special regex characters
                if char in r".+^$(){}|":
                    regex_parts.append(f"\\{char}")
                else:
                    regex_parts.append(char)

            i += 1

        return "^" + "".join(regex_parts) + "$"

    @staticmethod
    def escape_literal(text: str) -> str:
        """Escape literal text for use in regex."""
        return re.escape(text)


class TableMatcher:
    """Table pattern matcher for wildcard, regex, and schema patterns."""

    def __init__(self, validate_regex: bool = True):
        """
        Initialize table matcher.

        Args:
            validate_regex: Whether to validate regex patterns at initialization
        """
        self.validate_regex = validate_regex
        self._compiled_patterns: dict[str, Pattern[str]] = {}

    def match_table(
        self, table_name: str, pattern: str, pattern_type: Optional[str] = None
    ) -> bool:
        """
        Check if table name matches pattern.

        Args:
            table_name: Name of the table to match
            pattern: Pattern to match against (wildcard or regex)
            pattern_type: Type of pattern - 'wildcard', 'regex', or None (defaults to wildcard)

        Returns:
            True if table matches pattern, False otherwise

        Raises:
            ValueError: If pattern is invalid regex and validate_regex is True
        """
        if pattern_type == "regex":
            return self._match_regex(table_name, pattern)
        else:
            # Default to wildcard
            return self._match_wildcard(table_name, pattern)

    def _match_wildcard(self, table_name: str, pattern: str) -> bool:
        """Match table name against wildcard pattern."""
        regex_pattern = RegexValidator.wildcard_to_regex(pattern)
        return bool(re.match(regex_pattern, table_name))

    def _match_regex(self, table_name: str, pattern: str) -> bool:
        """Match table name against regex pattern."""
        # Cache compiled patterns
        if pattern not in self._compiled_patterns:
            if self.validate_regex:
                compiled = RegexValidator.validate_and_compile(pattern)
            else:
                try:
                    compiled = re.compile(pattern)
                except re.error as e:
                    raise ValueError(f"Invalid regex pattern '{pattern}': {e}") from e
            self._compiled_patterns[pattern] = compiled

        compiled_pattern = self._compiled_patterns[pattern]
        return bool(compiled_pattern.match(table_name))

    def match_schema(
        self, schema_name: str, pattern: str, pattern_type: Optional[str] = None
    ) -> bool:
        """
        Check if schema name matches pattern.

        Args:
            schema_name: Name of the schema to match
            pattern: Pattern to match against (wildcard or regex)
            pattern_type: Type of pattern - 'wildcard', 'regex', or None (defaults to wildcard)

        Returns:
            True if schema matches pattern, False otherwise

        Raises:
            ValueError: If pattern is invalid regex and validate_regex is True
        """
        return self.match_table(schema_name, pattern, pattern_type)

    def matches_exclude_patterns(
        self, table_name: str, exclude_patterns: List[str], pattern_type: Optional[str] = None
    ) -> bool:
        """
        Check if table name matches any exclude pattern.

        Args:
            table_name: Name of the table to check
            exclude_patterns: List of patterns to exclude
            pattern_type: Type of pattern - 'wildcard', 'regex', or None

        Returns:
            True if table matches any exclude pattern, False otherwise
        """
        if not exclude_patterns:
            return False

        for exclude_pattern in exclude_patterns:
            if self.match_table(table_name, exclude_pattern, pattern_type):
                return True
        return False

    def filter_tables(
        self,
        tables: List[str],
        pattern: Optional[str] = None,
        pattern_type: Optional[str] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Filter list of table names based on patterns.

        Args:
            tables: List of table names to filter
            pattern: Optional pattern to match (if None, all tables pass)
            pattern_type: Type of pattern - 'wildcard', 'regex', or None
            exclude_patterns: Optional list of patterns to exclude

        Returns:
            Filtered list of table names

        Raises:
            ValueError: If pattern is invalid regex and validate_regex is True
        """
        if not tables:
            return []

        filtered = tables

        # Apply include pattern
        if pattern:
            filtered = [
                table for table in filtered if self.match_table(table, pattern, pattern_type)
            ]

        # Apply exclude patterns
        if exclude_patterns:
            filtered = [
                table
                for table in filtered
                if not self.matches_exclude_patterns(table, exclude_patterns, pattern_type)
            ]

        return filtered

    def resolve_priority(
        self, table_matches: List[Tuple[str, int]], keep_highest: bool = True
    ) -> List[str]:
        """
        Resolve table matches by priority.

        Args:
            table_matches: List of (table_name, priority) tuples
            keep_highest: If True, keep highest priority matches (default: True)

        Returns:
            List of table names after priority resolution
        """
        if not table_matches:
            return []

        # Group by table name
        table_priorities: dict[str, int] = {}
        for table_name, priority in table_matches:
            if table_name not in table_priorities:
                table_priorities[table_name] = priority
            else:
                if keep_highest:
                    table_priorities[table_name] = max(table_priorities[table_name], priority)
                else:
                    table_priorities[table_name] = min(table_priorities[table_name], priority)

        # Sort by priority (highest first) and return table names
        sorted_matches = sorted(table_priorities.items(), key=lambda x: x[1], reverse=keep_highest)
        return [table_name for table_name, _ in sorted_matches]
