"""
Tests for quality scores API routes.
"""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text
from fastapi.testclient import TestClient
from main import app
from database import DatabaseClient


@pytest.fixture
def db_client(monkeypatch):
    """Create a test database client."""
    test_engine = create_engine('sqlite:///:memory:')
    monkeypatch.setenv('BASELINR_DB_URL', 'sqlite:///:memory:')
    
    client = DatabaseClient()
    client.engine = test_engine
    
    # Create quality scores table
    with test_engine.connect() as conn:
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
    
    return client


@pytest.fixture
def sample_scores(db_client):
    """Insert sample quality scores for testing."""
    now = datetime.now(timezone.utc)
    with db_client.engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO baselinr_quality_scores 
            (table_name, schema_name, run_id, overall_score, completeness_score,
             validity_score, consistency_score, freshness_score, uniqueness_score,
             accuracy_score, status, total_issues, critical_issues, warnings,
             calculated_at, period_start, period_end)
            VALUES 
                ('customers', 'public', 'run1', 85.5, 90.0, 88.0, 82.0, 95.0, 85.0, 78.0,
                 'healthy', 3, 1, 2, :timestamp, :period_start, :period_end)
        """), {
            "timestamp": now - timedelta(days=1),
            "period_start": now - timedelta(days=8),
            "period_end": now - timedelta(days=1),
        })
        conn.commit()


@pytest.fixture
def client(db_client, monkeypatch):
    """Create a test client with mocked database."""
    # Mock the DatabaseClient to return our test client
    monkeypatch.setattr('quality_routes.get_db_client', lambda: db_client)
    return TestClient(app)


def test_get_all_scores(client, sample_scores):
    """Test GET /api/quality/scores endpoint."""
    response = client.get("/api/quality/scores")
    
    assert response.status_code == 200
    data = response.json()
    assert "scores" in data
    assert "total" in data
    assert data["total"] == 1
    assert len(data["scores"]) == 1
    assert data["scores"][0]["table_name"] == "customers"


def test_get_all_scores_filtered_by_status(client, sample_scores):
    """Test GET /api/quality/scores with status filter."""
    response = client.get("/api/quality/scores?status=healthy")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["scores"]) == 1
    assert data["scores"][0]["status"] == "healthy"


def test_get_table_score(client, sample_scores):
    """Test GET /api/quality/scores/{table_name} endpoint."""
    response = client.get("/api/quality/scores/customers")
    
    assert response.status_code == 200
    data = response.json()
    assert data["table_name"] == "customers"
    assert data["overall_score"] == 85.5
    assert data["status"] == "healthy"
    assert "components" in data
    assert "issues" in data


def test_get_table_score_not_found(client):
    """Test GET /api/quality/scores/{table_name} for non-existent table."""
    response = client.get("/api/quality/scores/nonexistent")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_schema_score(client, sample_scores):
    """Test GET /api/quality/scores/schema/{schema_name} endpoint."""
    response = client.get("/api/quality/scores/schema/public")
    
    assert response.status_code == 200
    data = response.json()
    assert data["schema_name"] == "public"
    assert "overall_score" in data
    assert "table_count" in data
    assert "tables" in data


def test_get_schema_score_not_found(client):
    """Test GET /api/quality/scores/schema/{schema_name} for non-existent schema."""
    response = client.get("/api/quality/scores/schema/nonexistent")
    
    assert response.status_code == 404


def test_get_system_score(client, sample_scores):
    """Test GET /api/quality/scores/system endpoint."""
    response = client.get("/api/quality/scores/system")
    
    assert response.status_code == 200
    data = response.json()
    assert "overall_score" in data
    assert "status" in data
    assert "total_tables" in data
    assert "healthy_count" in data
    assert "warning_count" in data
    assert "critical_count" in data


def test_get_score_history(client, sample_scores):
    """Test GET /api/quality/scores/{table_name}/history endpoint."""
    response = client.get("/api/quality/scores/customers/history")
    
    assert response.status_code == 200
    data = response.json()
    assert "scores" in data
    assert "total" in data
    assert len(data["scores"]) >= 1


def test_get_score_history_with_days(client, sample_scores):
    """Test GET /api/quality/scores/{table_name}/history with days parameter."""
    response = client.get("/api/quality/scores/customers/history?days=7")
    
    assert response.status_code == 200
    data = response.json()
    assert "scores" in data


def test_get_component_breakdown(client, sample_scores):
    """Test GET /api/quality/scores/{table_name}/components endpoint."""
    response = client.get("/api/quality/scores/customers/components")
    
    assert response.status_code == 200
    data = response.json()
    assert "completeness" in data
    assert "validity" in data
    assert "consistency" in data
    assert "freshness" in data
    assert "uniqueness" in data
    assert "accuracy" in data
    assert data["completeness"] == 90.0


def test_get_component_breakdown_not_found(client):
    """Test GET /api/quality/scores/{table_name}/components for non-existent table."""
    response = client.get("/api/quality/scores/nonexistent/components")
    
    assert response.status_code == 404
