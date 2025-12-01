"""
Unit tests for smart selection table scorer.

Tests the scoring logic for table recommendations.
"""

import math
from datetime import datetime, timedelta

import pytest

from baselinr.smart_selection.config import SmartSelectionCriteria
from baselinr.smart_selection.metadata_collector import TableMetadata
from baselinr.smart_selection.scorer import TableScorer


class TestTableScorer:
    """Test TableScorer class."""

    @pytest.fixture
    def default_criteria(self):
        """Create default criteria for testing."""
        return SmartSelectionCriteria(
            min_query_count=10,
            min_queries_per_day=1.0,
            lookback_days=30,
            exclude_patterns=["temp_*", "*_backup"],
            min_rows=100,
            max_rows=None,
        )

    @pytest.fixture
    def scorer(self, default_criteria):
        """Create scorer instance."""
        return TableScorer(default_criteria)

    def test_score_high_usage_table(self, scorer):
        """Test scoring for a heavily used table."""
        table = TableMetadata(
            database="prod",
            schema="analytics",
            table="user_events",
            query_count=1247,
            queries_per_day=41.6,
            last_query_time=datetime.now() - timedelta(hours=2),
            row_count=5000000,
            last_modified_time=datetime.now() - timedelta(hours=12),
        )
        
        score = scorer._score_table(table)
        
        assert score is not None
        assert score.total_score > 80  # High score expected
        assert score.confidence >= 0.8  # High confidence
        assert len(score.reasons) > 0
        assert "Heavily used" in score.reasons[0] or "queried" in score.reasons[0].lower()

    def test_score_low_usage_table(self, scorer):
        """Test scoring for a rarely used table."""
        table = TableMetadata(
            database="prod",
            schema="analytics",
            table="legacy_data",
            query_count=5,
            queries_per_day=0.16,
            last_query_time=datetime.now() - timedelta(days=60),
            row_count=1000,
        )
        
        score = scorer._score_table(table)
        
        # Should be filtered out due to low query count
        assert score is None

    def test_exclude_pattern_matching(self, scorer):
        """Test that exclude patterns work correctly."""
        # Temp table - should be excluded
        temp_table = TableMetadata(
            database="prod",
            schema="staging",
            table="temp_load_2025",
            query_count=100,
            queries_per_day=10.0,
            row_count=1000,
        )
        
        score = scorer._score_table(temp_table)
        assert score is None
        
        # Backup table - should be excluded
        backup_table = TableMetadata(
            database="prod",
            schema="analytics",
            table="users_backup",
            query_count=100,
            queries_per_day=10.0,
            row_count=1000,
        )
        
        score = scorer._score_table(backup_table)
        assert score is None

    def test_row_count_filtering(self, scorer):
        """Test row count min/max filtering."""
        # Too small
        small_table = TableMetadata(
            database="prod",
            schema="config",
            table="settings",
            query_count=100,
            queries_per_day=5.0,
            row_count=10,  # Below min_rows=100
        )
        
        score = scorer._score_table(small_table)
        assert score is None
        
        # Just right
        good_table = TableMetadata(
            database="prod",
            schema="analytics",
            table="metrics",
            query_count=100,
            queries_per_day=5.0,
            row_count=50000,
        )
        
        score = scorer._score_table(good_table)
        assert score is not None

    def test_query_frequency_scoring(self, scorer):
        """Test query frequency component scoring."""
        # High query count
        score_high = scorer._score_query_frequency(
            TableMetadata(
                database="prod",
                schema="analytics",
                table="high_freq",
                query_count=1000,
            )
        )
        assert score_high > 90
        
        # Medium query count
        score_med = scorer._score_query_frequency(
            TableMetadata(
                database="prod",
                schema="analytics",
                table="med_freq",
                query_count=100,
            )
        )
        assert 60 < score_med < 80
        
        # Low query count
        score_low = scorer._score_query_frequency(
            TableMetadata(
                database="prod",
                schema="analytics",
                table="low_freq",
                query_count=10,
            )
        )
        assert score_low < 40
        
        # Verify logarithmic scaling
        assert score_high > score_med > score_low

    def test_query_recency_scoring(self, scorer):
        """Test query recency component scoring."""
        # Queried today
        score_today = scorer._score_query_recency(
            TableMetadata(
                database="prod",
                schema="analytics",
                table="recent",
                query_count=100,
                last_query_time=datetime.now(),
            )
        )
        assert score_today > 95
        
        # Queried 1 week ago
        score_week = scorer._score_query_recency(
            TableMetadata(
                database="prod",
                schema="analytics",
                table="week_old",
                query_count=100,
                last_query_time=datetime.now() - timedelta(days=7),
            )
        )
        assert 40 < score_week < 60
        
        # Queried 30 days ago
        score_month = scorer._score_query_recency(
            TableMetadata(
                database="prod",
                schema="analytics",
                table="month_old",
                query_count=100,
                last_query_time=datetime.now() - timedelta(days=30),
            )
        )
        assert score_month < 30
        
        # Verify exponential decay
        assert score_today > score_week > score_month

    def test_table_size_scoring(self, scorer):
        """Test table size component scoring."""
        # Sweet spot: 100K rows (actually 95.0 since 100K is at boundary)
        score_optimal = scorer._score_table_size(
            TableMetadata(
                database="prod",
                schema="analytics",
                table="optimal",
                query_count=100,
                row_count=100000,
            )
        )
        assert score_optimal == 95.0
        
        # Very small: 50 rows
        score_tiny = scorer._score_table_size(
            TableMetadata(
                database="prod",
                schema="analytics",
                table="tiny",
                query_count=100,
                row_count=50,
            )
        )
        assert score_tiny < 30
        
        # Very large: 1B rows
        score_huge = scorer._score_table_size(
            TableMetadata(
                database="prod",
                schema="analytics",
                table="huge",
                query_count=100,
                row_count=1000000000,
            )
        )
        assert score_huge < 60

    def test_confidence_calculation(self, scorer):
        """Test confidence score calculation."""
        # Complete metadata = high confidence
        complete_table = TableMetadata(
            database="prod",
            schema="analytics",
            table="complete",
            query_count=100,
            queries_per_day=5.0,
            last_query_time=datetime.now(),
            row_count=10000,
            last_modified_time=datetime.now(),
            table_type="BASE TABLE",
        )
        
        score = scorer._score_table(complete_table)
        assert score is not None
        assert score.confidence >= 0.9
        
        # Incomplete metadata = lower confidence
        incomplete_table = TableMetadata(
            database="prod",
            schema="analytics",
            table="incomplete",
            query_count=100,  # Only has query count
            queries_per_day=5.0,
        )
        
        score = scorer._score_table(incomplete_table)
        assert score is not None
        assert score.confidence < 0.8

    def test_score_tables_sorting(self, scorer):
        """Test that score_tables returns sorted results."""
        tables = [
            TableMetadata(
                database="prod",
                schema="analytics",
                table="low_score",
                query_count=20,
                queries_per_day=1.0,
                row_count=1000,
            ),
            TableMetadata(
                database="prod",
                schema="analytics",
                table="high_score",
                query_count=500,
                queries_per_day=20.0,
                last_query_time=datetime.now(),
                row_count=100000,
            ),
            TableMetadata(
                database="prod",
                schema="analytics",
                table="medium_score",
                query_count=100,
                queries_per_day=5.0,
                row_count=10000,
            ),
        ]
        
        scored = scorer.score_tables(tables)
        
        # Should be sorted by score (descending)
        assert len(scored) == 3
        assert scored[0].metadata.table == "high_score"
        assert scored[1].metadata.table == "medium_score"
        assert scored[2].metadata.table == "low_score"
        
        # Verify scores are in descending order
        for i in range(len(scored) - 1):
            assert scored[i].total_score >= scored[i + 1].total_score

    def test_warnings_generation(self, scorer):
        """Test warning generation for edge cases."""
        # Very large table
        large_table = TableMetadata(
            database="prod",
            schema="analytics",
            table="huge_table",
            query_count=100,
            queries_per_day=5.0,
            row_count=200000000,  # 200M rows
        )
        
        score = scorer._score_table(large_table)
        assert score is not None
        assert any("large" in w.lower() for w in score.warnings)
        
        # Stale table (not queried recently)
        stale_table = TableMetadata(
            database="prod",
            schema="analytics",
            table="stale_table",
            query_count=100,
            queries_per_day=5.0,
            last_query_time=datetime.now() - timedelta(days=60),
            row_count=10000,
        )
        
        score = scorer._score_table(stale_table)
        assert score is not None
        assert any("stale" in w.lower() or "days" in w.lower() for w in score.warnings)

    def test_custom_weights(self):
        """Test custom scoring weights."""
        # Emphasize query frequency
        criteria = SmartSelectionCriteria(
            min_query_count=10,
            min_queries_per_day=1.0,
            lookback_days=30,
            weights={
                "query_frequency": 0.7,  # High weight
                "query_recency": 0.1,
                "write_activity": 0.1,
                "table_size": 0.1,
            },
        )
        
        scorer = TableScorer(criteria)
        
        # High frequency table
        freq_table = TableMetadata(
            database="prod",
            schema="analytics",
            table="high_freq",
            query_count=1000,
            queries_per_day=50.0,
            row_count=10000,
        )
        
        score = scorer._score_table(freq_table)
        assert score is not None
        
        # Query frequency should dominate the total score
        freq_contribution = score.query_frequency_score * 0.7
        assert freq_contribution > score.total_score * 0.6  # At least 60% of total

    def test_reasons_generation(self, scorer):
        """Test that reasons are generated correctly."""
        table = TableMetadata(
            database="prod",
            schema="analytics",
            table="active_table",
            query_count=500,
            queries_per_day=25.0,
            last_query_time=datetime.now() - timedelta(hours=6),
            row_count=50000,
            last_modified_time=datetime.now() - timedelta(days=1),
        )
        
        score = scorer._score_table(table)
        assert score is not None
        assert len(score.reasons) >= 3
        
        # Should mention query activity
        assert any("queried" in r.lower() or "queries" in r.lower() for r in score.reasons)
        
        # Should mention recency
        assert any("day" in r.lower() or "hour" in r.lower() for r in score.reasons)
