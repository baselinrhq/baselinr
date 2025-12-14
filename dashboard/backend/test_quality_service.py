"""
Tests for quality service.
"""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text
from quality_service import QualityService
from baselinr.quality.models import DataQualityScore


@pytest.fixture
def db_engine():
    """Create a test database engine."""
    engine = create_engine('sqlite:///:memory:')
    
    # Create quality scores table
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE baselinr_quality_scores (
                table_name VARCHAR(255) NOT NULL,
                schema_name VARCHAR(255),
                run_id VARCHAR(36),
                overall_score REAL NOT NULL,
                completeness_score REAL NOT NULL,
                validity_score REAL NOT NULL,
                consistency_score REAL NOT NULL,
                freshness_score REAL NOT NULL,
                uniqueness_score REAL NOT NULL,
                accuracy_score REAL NOT NULL,
                status VARCHAR(20) NOT NULL,
                total_issues INTEGER NOT NULL,
                critical_issues INTEGER NOT NULL,
                warnings INTEGER NOT NULL,
                calculated_at TIMESTAMP NOT NULL,
                period_start TIMESTAMP NOT NULL,
                period_end TIMESTAMP NOT NULL
            )
        """))
        conn.commit()
    
    return engine


@pytest.fixture
def quality_service(db_engine):
    """Create a quality service instance."""
    return QualityService(db_engine)


@pytest.fixture
def sample_scores(db_engine):
    """Insert sample quality scores for testing."""
    now = datetime.now(timezone.utc)
    with db_engine.connect() as conn:
        # Insert scores for table1
        conn.execute(text("""
            INSERT INTO baselinr_quality_scores 
            (table_name, schema_name, run_id, overall_score, completeness_score,
             validity_score, consistency_score, freshness_score, uniqueness_score,
             accuracy_score, status, total_issues, critical_issues, warnings,
             calculated_at, period_start, period_end)
            VALUES 
                ('table1', 'public', 'run1', 85.5, 90.0, 88.0, 82.0, 95.0, 85.0, 78.0,
                 'healthy', 3, 1, 2, :timestamp1, :period_start1, :period_end1),
                ('table1', 'public', 'run2', 87.0, 92.0, 89.0, 83.0, 96.0, 86.0, 80.0,
                 'healthy', 2, 0, 2, :timestamp2, :period_start2, :period_end2)
        """), {
            "timestamp1": now - timedelta(days=2),
            "timestamp2": now - timedelta(days=1),
            "period_start1": now - timedelta(days=9),
            "period_end1": now - timedelta(days=2),
            "period_start2": now - timedelta(days=8),
            "period_end2": now - timedelta(days=1),
        })
        
        # Insert scores for table2
        conn.execute(text("""
            INSERT INTO baselinr_quality_scores 
            (table_name, schema_name, run_id, overall_score, completeness_score,
             validity_score, consistency_score, freshness_score, uniqueness_score,
             accuracy_score, status, total_issues, critical_issues, warnings,
             calculated_at, period_start, period_end)
            VALUES 
                ('table2', 'public', 'run3', 65.0, 70.0, 60.0, 65.0, 70.0, 65.0, 60.0,
                 'warning', 10, 3, 7, :timestamp3, :period_start3, :period_end3)
        """), {
            "timestamp3": now - timedelta(days=1),
            "period_start3": now - timedelta(days=8),
            "period_end3": now - timedelta(days=1),
        })
        
        # Insert scores for table3 in different schema
        conn.execute(text("""
            INSERT INTO baselinr_quality_scores 
            (table_name, schema_name, run_id, overall_score, completeness_score,
             validity_score, consistency_score, freshness_score, uniqueness_score,
             accuracy_score, status, total_issues, critical_issues, warnings,
             calculated_at, period_start, period_end)
            VALUES 
                ('table3', 'analytics', 'run4', 45.0, 50.0, 40.0, 45.0, 50.0, 45.0, 40.0,
                 'critical', 20, 10, 10, :timestamp4, :period_start4, :period_end4)
        """), {
            "timestamp4": now - timedelta(days=1),
            "period_start4": now - timedelta(days=8),
            "period_end4": now - timedelta(days=1),
        })
        
        conn.commit()


def test_get_table_score(quality_service, sample_scores):
    """Test getting a table score."""
    score = quality_service.get_table_score('table1', 'public')
    
    assert score is not None
    assert score.table_name == 'table1'
    assert score.schema_name == 'public'
    assert score.overall_score == 87.0  # Latest score
    assert score.status == 'healthy'
    assert score.components.completeness == 92.0


def test_get_table_score_not_found(quality_service):
    """Test getting a score for a non-existent table."""
    score = quality_service.get_table_score('nonexistent', 'public')
    assert score is None


def test_get_all_scores(quality_service, sample_scores):
    """Test getting all scores."""
    scores = quality_service.get_all_scores()
    
    assert len(scores) == 3  # Latest score for each table
    table_names = {s.table_name for s in scores}
    assert 'table1' in table_names
    assert 'table2' in table_names
    assert 'table3' in table_names


def test_get_all_scores_filtered_by_schema(quality_service, sample_scores):
    """Test getting scores filtered by schema."""
    scores = quality_service.get_all_scores(schema='public')
    
    assert len(scores) == 2
    assert all(s.schema_name == 'public' for s in scores)


def test_get_all_scores_filtered_by_status(quality_service, sample_scores):
    """Test getting scores filtered by status."""
    scores = quality_service.get_all_scores(status='healthy')
    
    assert len(scores) == 1
    assert scores[0].status == 'healthy'
    assert scores[0].table_name == 'table1'


def test_get_score_history(quality_service, sample_scores):
    """Test getting score history."""
    history = quality_service.get_score_history('table1', 'public', days=30)
    
    assert len(history) == 2
    # Should be ordered by calculated_at DESC (newest first)
    assert history[0].overall_score == 87.0
    assert history[1].overall_score == 85.5


def test_get_schema_score(quality_service, sample_scores):
    """Test getting schema-level score."""
    schema_score = quality_service.get_schema_score('public')
    
    assert schema_score is not None
    assert schema_score.schema_name == 'public'
    assert schema_score.table_count == 2
    # Average of table1 (87.0) and table2 (65.0) = 76.0
    assert schema_score.overall_score == 76.0
    assert schema_score.healthy_count == 1
    assert schema_score.warning_count == 1
    assert schema_score.critical_count == 0


def test_get_system_score(quality_service, sample_scores):
    """Test getting system-level score."""
    system_score = quality_service.get_system_score()
    
    assert system_score.total_tables == 3
    # Average of table1 (87.0), table2 (65.0), table3 (45.0) = 65.67
    assert abs(system_score.overall_score - 65.67) < 0.1
    assert system_score.healthy_count == 1
    assert system_score.warning_count == 1
    assert system_score.critical_count == 1


def test_get_component_breakdown(quality_service, sample_scores):
    """Test getting component breakdown."""
    components = quality_service.get_component_breakdown('table1', 'public')
    
    assert components is not None
    assert components.completeness == 92.0
    assert components.validity == 89.0
    assert components.consistency == 83.0
    assert components.freshness == 96.0
    assert components.uniqueness == 86.0
    assert components.accuracy == 80.0


def test_get_component_breakdown_not_found(quality_service):
    """Test getting component breakdown for non-existent table."""
    components = quality_service.get_component_breakdown('nonexistent', 'public')
    assert components is None


def test_service_without_db_engine():
    """Test service initialization without database engine."""
    service = QualityService(None)
    assert service.storage is None
    
    # All methods should return None or empty lists
    assert service.get_table_score('table1') is None
    assert service.get_all_scores() == []
    assert service.get_score_history('table1') == []
    assert service.get_schema_score('public') is None
    assert service.get_component_breakdown('table1') is None


def test_get_trend_analysis(quality_service, sample_scores):
    """Test getting trend analysis."""
    trend = quality_service.get_trend_analysis('table1', 'public', days=30)
    
    assert trend is not None
    assert trend.direction in ['improving', 'degrading', 'stable']
    assert trend.periods_analyzed == 2
    assert 0 <= trend.confidence <= 1


def test_get_trend_analysis_insufficient_data(quality_service):
    """Test trend analysis with insufficient data."""
    trend = quality_service.get_trend_analysis('nonexistent', 'public', days=30)
    assert trend is None


def test_get_column_scores(quality_service, db_engine):
    """Test getting column scores."""
    from datetime import datetime, timedelta, timezone
    from baselinr.quality.storage import QualityScoreStorage
    from baselinr.quality.models import ColumnQualityScore
    
    storage = QualityScoreStorage(db_engine)
    now = datetime.now(timezone.utc)
    
    # Store a column score
    column_score = ColumnQualityScore(
        overall_score=85.0,
        completeness_score=90.0,
        validity_score=88.0,
        consistency_score=82.0,
        freshness_score=95.0,
        uniqueness_score=85.0,
        accuracy_score=78.0,
        status='healthy',
        table_name='table1',
        schema_name='public',
        column_name='email',
        run_id='run1',
        calculated_at=now,
        period_start=now - timedelta(days=7),
        period_end=now,
    )
    storage.store_column_score(column_score)
    
    # Get column scores
    result = quality_service.get_column_scores('table1', 'public', days=30)
    
    assert result is not None
    assert len(result.scores) == 1
    assert result.scores[0].column_name == 'email'
    assert result.scores[0].overall_score == 85.0


def test_compare_scores(quality_service, sample_scores):
    """Test comparing scores across tables."""
    comparison = quality_service.compare_scores(['table1', 'table2'], 'public')
    
    assert comparison is not None
    assert len(comparison.tables) == 2
    assert comparison.comparison_metrics['best_performer'] == 'table1'
    assert comparison.comparison_metrics['worst_performer'] == 'table2'
    assert comparison.comparison_metrics['average_score'] > 0
    assert 'score_range' in comparison.comparison_metrics


def test_compare_scores_single_table(quality_service, sample_scores):
    """Test comparing scores with single table."""
    comparison = quality_service.compare_scores(['table1'], 'public')
    
    assert comparison is not None
    assert len(comparison.tables) == 1
    assert comparison.comparison_metrics['best_performer'] == 'table1'
    assert comparison.comparison_metrics['worst_performer'] == 'table1'
