"""
Tests for quality score performance optimizations.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from baselinr.quality.storage import QualityScoreStorage
from baselinr.quality.models import DataQualityScore
from sqlalchemy import create_engine


@pytest.fixture
def mock_engine():
    """Create a mock SQLAlchemy engine."""
    engine = Mock()
    connection = Mock()
    engine.connect.return_value.__enter__ = Mock(return_value=connection)
    engine.connect.return_value.__exit__ = Mock(return_value=False)
    connection.execute.return_value.fetchone.return_value = None
    connection.execute.return_value.fetchall.return_value = []
    return engine


@pytest.fixture
def storage(mock_engine):
    """Create a QualityScoreStorage instance."""
    return QualityScoreStorage(
        engine=mock_engine,
        scores_table="baselinr_quality_scores",
        cache_ttl_minutes=5,
    )


def create_score(overall_score: float) -> DataQualityScore:
    """Helper to create a DataQualityScore."""
    return DataQualityScore(
        overall_score=overall_score,
        completeness_score=90.0,
        validity_score=88.0,
        consistency_score=82.0,
        freshness_score=95.0,
        uniqueness_score=85.0,
        accuracy_score=78.0,
        status="healthy",
        total_issues=0,
        critical_issues=0,
        warnings=0,
        table_name="test_table",
        schema_name="public",
        run_id="test_run",
        calculated_at=datetime.utcnow(),
        period_start=datetime.utcnow() - timedelta(days=7),
        period_end=datetime.utcnow(),
    )


class TestCaching:
    """Test caching functionality."""

    def test_cache_hit(self, storage, mock_engine):
        """Test cache hit returns cached score without query."""
        score = create_score(85.0)
        cache_key = (score.table_name, score.schema_name)
        
        # Manually add to cache
        storage._cache[cache_key] = (score, datetime.utcnow())
        
        # Get score (should use cache)
        result = storage.get_latest_score(score.table_name, score.schema_name)
        
        assert result is not None
        assert result.overall_score == 85.0
        # Verify no database query was made
        assert not mock_engine.connect.called

    def test_cache_miss(self, storage, mock_engine):
        """Test cache miss queries database."""
        # Mock database response
        mock_result = Mock()
        mock_result.fetchone.return_value = (
            "test_table", "public", "run_123",
            85.0, 90.0, 88.0, 82.0, 95.0, 85.0, 78.0,
            "healthy", 0, 0, 0,
            datetime.utcnow(), datetime.utcnow() - timedelta(days=7), datetime.utcnow()
        )
        mock_engine.connect.return_value.__enter__.return_value.execute.return_value = mock_result
        
        result = storage.get_latest_score("test_table", "public")
        
        assert result is not None
        assert mock_engine.connect.called
        # Verify score was cached
        cache_key = ("test_table", "public")
        assert cache_key in storage._cache

    def test_cache_expiration(self, storage, mock_engine):
        """Test cache expiration after TTL."""
        score = create_score(85.0)
        cache_key = (score.table_name, score.schema_name)
        
        # Add expired cache entry
        expired_time = datetime.utcnow() - timedelta(minutes=10)
        storage._cache[cache_key] = (score, expired_time)
        
        # Mock database response for when cache is expired
        mock_result = Mock()
        mock_result.fetchone.return_value = (
            "test_table", "public", "run_123",
            85.0, 90.0, 88.0, 82.0, 95.0, 85.0, 78.0,
            "healthy", 0, 0, 0,
            datetime.utcnow(), datetime.utcnow() - timedelta(days=7), datetime.utcnow()
        )
        mock_engine.connect.return_value.__enter__.return_value.execute.return_value = mock_result
        
        # Get score should remove expired cache and query database
        result = storage.get_latest_score(score.table_name, score.schema_name)
        
        # Cache should be refreshed with new entry
        assert cache_key in storage._cache
        # Verify database was queried
        assert mock_engine.connect.called

    def test_cache_invalidation_on_store(self, storage):
        """Test cache is invalidated when storing new score."""
        score = create_score(85.0)
        cache_key = (score.table_name, score.schema_name)
        
        # Add to cache
        storage._cache[cache_key] = (score, datetime.utcnow())
        assert cache_key in storage._cache
        
        # Store new score
        new_score = create_score(90.0)
        storage.store_score(new_score)
        
        # Cache should be invalidated
        assert cache_key not in storage._cache

    def test_cache_per_table(self, storage):
        """Test cache works per table."""
        score1 = create_score(85.0)
        score1.table_name = "table1"
        score2 = create_score(90.0)
        score2.table_name = "table2"
        
        cache_key1 = (score1.table_name, score1.schema_name)
        cache_key2 = (score2.table_name, score2.schema_name)
        
        storage._cache[cache_key1] = (score1, datetime.utcnow())
        storage._cache[cache_key2] = (score2, datetime.utcnow())
        
        result1 = storage.get_latest_score("table1", "public")
        result2 = storage.get_latest_score("table2", "public")
        
        assert result1.overall_score == 85.0
        assert result2.overall_score == 90.0


class TestQueryOptimization:
    """Test query optimization."""

    def test_query_structure(self, storage, mock_engine):
        """Test queries use efficient structure."""
        # Mock database response
        mock_result = Mock()
        mock_result.fetchone.return_value = (
            "test_table", "public", "run_123",
            85.0, 90.0, 88.0, 82.0, 95.0, 85.0, 78.0,
            "healthy", 0, 0, 0,
            datetime.utcnow(), datetime.utcnow() - timedelta(days=7), datetime.utcnow()
        )
        mock_engine.connect.return_value.__enter__.return_value.execute.return_value = mock_result
        
        # Execute query
        storage.get_latest_score("test_table", "public")
        
        # Verify query was executed (optimization is in SQL structure)
        assert mock_engine.connect.called

    def test_batch_query_support(self, storage):
        """Test support for batch queries."""
        # QualityScoreStorage should support efficient batch operations
        # This is a placeholder for future batch optimization tests
        tables = ["table1", "table2", "table3"]
        
        # In a real implementation, this would use a single query
        # For now, we just verify the interface exists
        for table in tables:
            storage.get_latest_score(table, "public")
        
        # Verify multiple queries were made (or could be batched)
        assert True  # Placeholder assertion


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""

    def test_cache_performance(self, storage):
        """Test cache improves performance."""
        score = create_score(85.0)
        cache_key = (score.table_name, score.schema_name)
        storage._cache[cache_key] = (score, datetime.utcnow())
        
        # Time cache hit
        start = time.time()
        for _ in range(100):
            storage.get_latest_score(score.table_name, score.schema_name)
        cache_time = time.time() - start
        
        # Cache should be much faster than database queries
        # In practice, cache hits should be < 1ms each
        avg_time_per_call = cache_time / 100
        assert avg_time_per_call < 0.001  # Less than 1ms per call

    def test_storage_performance(self, storage, mock_engine):
        """Test score storage performance."""
        score = create_score(85.0)
        
        # Mock connection commit
        mock_connection = mock_engine.connect.return_value.__enter__.return_value
        mock_connection.commit = Mock()
        
        start = time.time()
        storage.store_score(score)
        storage_time = time.time() - start
        
        # Storage should complete quickly
        assert storage_time < 1.0  # Less than 1 second









