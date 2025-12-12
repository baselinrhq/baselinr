"""
Integration tests for recommendation_routes module.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from recommendation_routes import router
from fastapi import FastAPI
from recommendation_service import RecommendationService


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_recommendation_service():
    """Mock recommendation service."""
    service = Mock(spec=RecommendationService)
    return service


@pytest.fixture
def mock_recommendation_report():
    """Mock recommendation report."""
    from baselinr.smart_selection.recommender import (
        RecommendationReport,
        TableRecommendation,
        ExcludedTable,
    )
    
    return RecommendationReport(
        generated_at=datetime.now(),
        lookback_days=30,
        database_type="postgres",
        recommended_tables=[
            TableRecommendation(
                schema="public",
                table="users",
                confidence=0.85,
                score=0.9,
                reasons=["High query frequency", "Recent activity"],
                warnings=[],
                suggested_checks=["completeness", "freshness"],
                query_count=100,
                queries_per_day=10.0,
                row_count=1000,
                column_count=5,
            )
        ],
        excluded_tables=[
            ExcludedTable(
                schema="public",
                table="temp_table",
                reasons=["Temporary table"],
            )
        ],
        total_tables_analyzed=10,
        total_recommended=1,
        total_excluded=1,
        confidence_distribution={"high": 1, "medium": 0, "low": 0},
    )


@pytest.fixture
def mock_column_recommendations():
    """Mock column recommendations."""
    from baselinr.smart_selection.recommender import ColumnCheckRecommendation
    
    return [
        ColumnCheckRecommendation(
            column="email",
            data_type="varchar",
            confidence=0.9,
            signals=["Column name pattern", "Data type"],
            suggested_checks=[{"type": "format_email"}],
        )
    ]


class TestRecommendationRoutes:
    """Test cases for recommendation routes."""
    
    @patch('recommendation_routes.get_recommendation_service')
    def test_get_recommendations_success(
        self, mock_get_service, client, mock_recommendation_service, mock_recommendation_report
    ):
        """Test GET /api/recommendations success."""
        mock_recommendation_service.generate_recommendations.return_value = mock_recommendation_report
        mock_get_service.return_value = mock_recommendation_service
        
        response = client.get("/api/recommendations?connection_id=test-conn")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_recommended"] == 1
        assert len(data["recommended_tables"]) == 1
        assert data["recommended_tables"][0]["table"] == "users"
    
    @patch('recommendation_routes.get_recommendation_service')
    def test_get_recommendations_with_schema(
        self, mock_get_service, client, mock_recommendation_service, mock_recommendation_report
    ):
        """Test GET /api/recommendations with schema filter."""
        mock_recommendation_service.generate_recommendations.return_value = mock_recommendation_report
        mock_get_service.return_value = mock_recommendation_service
        
        response = client.get("/api/recommendations?connection_id=test-conn&schema=public")
        
        assert response.status_code == 200
        mock_recommendation_service.generate_recommendations.assert_called_once_with(
            connection_id="test-conn",
            schema="public",
            include_columns=False,
        )
    
    @patch('recommendation_routes.get_recommendation_service')
    def test_get_recommendations_connection_not_found(
        self, mock_get_service, client, mock_recommendation_service
    ):
        """Test GET /api/recommendations when connection not found."""
        mock_recommendation_service.generate_recommendations.side_effect = ValueError("Connection not found")
        mock_get_service.return_value = mock_recommendation_service
        
        response = client.get("/api/recommendations?connection_id=invalid")
        
        assert response.status_code == 400
        assert "Connection not found" in response.json()["detail"]
    
    @patch('recommendation_routes.get_recommendation_service')
    def test_get_column_recommendations_success(
        self, mock_get_service, client, mock_recommendation_service, mock_column_recommendations
    ):
        """Test GET /api/recommendations/columns success."""
        mock_recommendation_service.get_column_recommendations.return_value = mock_column_recommendations
        mock_get_service.return_value = mock_recommendation_service
        
        response = client.get("/api/recommendations/columns?connection_id=test-conn&table=users")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["column"] == "email"
        assert data[0]["confidence"] == 0.9
    
    @patch('recommendation_routes.get_recommendation_service')
    def test_get_column_recommendations_with_schema(
        self, mock_get_service, client, mock_recommendation_service, mock_column_recommendations
    ):
        """Test GET /api/recommendations/columns with schema."""
        mock_recommendation_service.get_column_recommendations.return_value = mock_column_recommendations
        mock_get_service.return_value = mock_recommendation_service
        
        response = client.get("/api/recommendations/columns?connection_id=test-conn&table=users&schema=public")
        
        assert response.status_code == 200
        mock_recommendation_service.get_column_recommendations.assert_called_once_with(
            connection_id="test-conn",
            table="users",
            schema="public",
            use_profiling_data=True,
        )
    
    @patch('recommendation_routes.get_recommendation_service')
    def test_apply_recommendations_success(
        self, mock_get_service, client, mock_recommendation_service
    ):
        """Test POST /api/recommendations/apply success."""
        mock_recommendation_service.apply_recommendations.return_value = {
            "success": True,
            "applied_tables": [
                {
                    "schema": "public",
                    "table": "users",
                    "database": None,
                    "column_checks_applied": 0,
                }
            ],
            "total_tables_applied": 1,
            "total_column_checks_applied": 0,
            "message": "Successfully applied 1 table(s) and 0 column check(s)",
        }
        mock_get_service.return_value = mock_recommendation_service
        
        response = client.post(
            "/api/recommendations/apply",
            json={
                "connection_id": "test-conn",
                "selected_tables": [{"schema": "public", "table": "users"}],
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total_tables_applied"] == 1
    
    @patch('recommendation_routes.get_recommendation_service')
    def test_apply_recommendations_invalid_request(
        self, mock_get_service, client, mock_recommendation_service
    ):
        """Test POST /api/recommendations/apply with invalid request."""
        mock_recommendation_service.apply_recommendations.side_effect = ValueError("No configuration found")
        mock_get_service.return_value = mock_recommendation_service
        
        response = client.post(
            "/api/recommendations/apply",
            json={
                "connection_id": "test-conn",
                "selected_tables": [],
            }
        )
        
        assert response.status_code == 400
    
    @patch('recommendation_routes.get_recommendation_service')
    def test_refresh_recommendations_success(
        self, mock_get_service, client, mock_recommendation_service, mock_recommendation_report
    ):
        """Test POST /api/recommendations/refresh success."""
        mock_recommendation_service.generate_recommendations.return_value = mock_recommendation_report
        mock_get_service.return_value = mock_recommendation_service
        
        response = client.post(
            "/api/recommendations/refresh",
            json={
                "connection_id": "test-conn",
                "schema": None,
                "include_columns": False,
                "refresh": True,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_recommended"] == 1


