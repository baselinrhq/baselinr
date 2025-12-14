"""
Tests for column-level quality scoring.
"""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text
from baselinr.quality.scorer import QualityScorer
from baselinr.quality.storage import QualityScoreStorage
from baselinr.quality.models import ColumnQualityScore
from baselinr.config.schema import QualityScoringConfig


@pytest.fixture
def db_engine():
    """Create a test database engine."""
    engine = create_engine('sqlite:///:memory:')
    
    # Create required tables
    with engine.connect() as conn:
        # Create baselinr_results table
        conn.execute(text("""
            CREATE TABLE baselinr_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id VARCHAR(36) NOT NULL,
                dataset_name VARCHAR(255) NOT NULL,
                schema_name VARCHAR(255),
                column_name VARCHAR(255) NOT NULL,
                column_type VARCHAR(100),
                metric_name VARCHAR(100) NOT NULL,
                metric_value TEXT,
                profiled_at TIMESTAMP NOT NULL
            )
        """))
        
        # Create baselinr_validation_results table
        conn.execute(text("""
            CREATE TABLE baselinr_validation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id VARCHAR(36) NOT NULL,
                table_name VARCHAR(255) NOT NULL,
                schema_name VARCHAR(255),
                column_name VARCHAR(255),
                rule_type VARCHAR(50) NOT NULL,
                passed BOOLEAN NOT NULL,
                severity VARCHAR(20),
                validated_at TIMESTAMP NOT NULL
            )
        """))
        
        # Create baselinr_events table
        conn.execute(text("""
            CREATE TABLE baselinr_events (
                event_id VARCHAR(36) PRIMARY KEY,
                event_type VARCHAR(100) NOT NULL,
                table_name VARCHAR(255),
                column_name VARCHAR(255),
                drift_severity VARCHAR(20),
                timestamp TIMESTAMP NOT NULL
            )
        """))
        
        # Create baselinr_runs table
        conn.execute(text("""
            CREATE TABLE baselinr_runs (
                run_id VARCHAR(36) NOT NULL,
                dataset_name VARCHAR(255) NOT NULL,
                schema_name VARCHAR(255),
                profiled_at TIMESTAMP NOT NULL,
                PRIMARY KEY (run_id, dataset_name)
            )
        """))
        
        # Create baselinr_column_quality_scores table
        conn.execute(text("""
            CREATE TABLE baselinr_column_quality_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name VARCHAR(255) NOT NULL,
                schema_name VARCHAR(255),
                column_name VARCHAR(255) NOT NULL,
                run_id VARCHAR(36),
                overall_score REAL NOT NULL,
                completeness_score REAL NOT NULL,
                validity_score REAL NOT NULL,
                consistency_score REAL NOT NULL,
                freshness_score REAL NOT NULL,
                uniqueness_score REAL NOT NULL,
                accuracy_score REAL NOT NULL,
                status VARCHAR(20) NOT NULL,
                calculated_at TIMESTAMP NOT NULL,
                period_start TIMESTAMP NOT NULL,
                period_end TIMESTAMP NOT NULL
            )
        """))
        
        conn.commit()
    
    return engine


@pytest.fixture
def config():
    """Create a test quality scoring config."""
    return QualityScoringConfig()


@pytest.fixture
def scorer(db_engine, config):
    """Create a quality scorer instance."""
    return QualityScorer(db_engine, config)


@pytest.fixture
def storage(db_engine):
    """Create a quality score storage instance."""
    return QualityScoreStorage(db_engine)


@pytest.fixture
def sample_data(db_engine):
    """Insert sample data for testing."""
    now = datetime.now(timezone.utc)
    with db_engine.connect() as conn:
        # Insert profiling results
        conn.execute(text("""
            INSERT INTO baselinr_results 
            (run_id, dataset_name, schema_name, column_name, metric_name, metric_value, profiled_at)
            VALUES 
                ('run1', 'customers', 'public', 'email', 'null_ratio', '0.1', :now),
                ('run1', 'customers', 'public', 'email', 'unique_ratio', '0.95', :now),
                ('run1', 'customers', 'public', 'name', 'null_ratio', '0.05', :now),
                ('run1', 'customers', 'public', 'name', 'unique_ratio', '0.8', :now)
        """), {"now": now})
        
        # Insert validation results
        conn.execute(text("""
            INSERT INTO baselinr_validation_results
            (run_id, table_name, schema_name, column_name, rule_type, passed, severity, validated_at)
            VALUES
                ('run1', 'customers', 'public', 'email', 'not_null', 1, 'high', :now),
                ('run1', 'customers', 'public', 'email', 'is_email', 1, 'medium', :now),
                ('run1', 'customers', 'public', 'name', 'not_null', 1, 'high', :now)
        """), {"now": now})
        
        # Insert run data
        conn.execute(text("""
            INSERT INTO baselinr_runs
            (run_id, dataset_name, schema_name, profiled_at)
            VALUES
                ('run1', 'customers', 'public', :now)
        """), {"now": now})
        
        conn.commit()


def test_calculate_column_score(scorer, sample_data):
    """Test calculating a column score."""
    score = scorer.calculate_column_score(
        'customers', 'email', 'public', 'run1', period_days=7
    )
    
    assert score is not None
    assert score.table_name == 'customers'
    assert score.column_name == 'email'
    assert score.schema_name == 'public'
    assert 0 <= score.overall_score <= 100
    assert 0 <= score.completeness_score <= 100
    assert score.status in ['healthy', 'warning', 'critical']


def test_store_column_score(storage, sample_data):
    """Test storing a column score."""
    now = datetime.now(timezone.utc)
    score = ColumnQualityScore(
        overall_score=85.0,
        completeness_score=90.0,
        validity_score=88.0,
        consistency_score=82.0,
        freshness_score=95.0,
        uniqueness_score=85.0,
        accuracy_score=78.0,
        status='healthy',
        table_name='customers',
        schema_name='public',
        column_name='email',
        run_id='run1',
        calculated_at=now,
        period_start=now - timedelta(days=7),
        period_end=now,
    )
    
    storage.store_column_score(score)
    
    # Verify it was stored
    retrieved = storage.get_latest_column_score('customers', 'email', 'public')
    assert retrieved is not None
    assert retrieved.overall_score == 85.0
    assert retrieved.column_name == 'email'


def test_get_column_scores_for_table(storage, db_engine):
    """Test getting all column scores for a table."""
    now = datetime.now(timezone.utc)
    
    # Store scores for multiple columns
    columns = ['email', 'name', 'age']
    for col in columns:
        score = ColumnQualityScore(
            overall_score=80.0 + len(col),
            completeness_score=85.0,
            validity_score=88.0,
            consistency_score=82.0,
            freshness_score=95.0,
            uniqueness_score=85.0,
            accuracy_score=78.0,
            status='healthy',
            table_name='customers',
            schema_name='public',
            column_name=col,
            run_id='run1',
            calculated_at=now,
            period_start=now - timedelta(days=7),
            period_end=now,
        )
        storage.store_column_score(score)
    
    # Retrieve all column scores
    scores = storage.get_column_scores_for_table('customers', 'public', days=30)
    
    assert len(scores) == 3
    column_names = {s.column_name for s in scores}
    assert 'email' in column_names
    assert 'name' in column_names
    assert 'age' in column_names


def test_column_score_not_found(storage):
    """Test getting a column score that doesn't exist."""
    score = storage.get_latest_column_score('nonexistent', 'column', 'public')
    assert score is None
