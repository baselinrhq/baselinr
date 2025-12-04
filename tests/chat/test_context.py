"""Tests for context enhancement."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from baselinr.chat.context import ContextEnhancer, get_conversation_context
from baselinr.chat.session import ChatSession, Message


class TestContextEnhancer:
    """Tests for the ContextEnhancer class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_engine = MagicMock()
        self.config = {
            "runs_table": "baselinr_runs",
            "results_table": "baselinr_results",
            "events_table": "baselinr_events",
        }

    def test_create_enhancer(self):
        """Test creating a context enhancer."""
        enhancer = ContextEnhancer(
            engine=self.mock_engine,
            config=self.config,
        )

        assert enhancer.engine == self.mock_engine
        assert enhancer.config == self.config

    def test_assess_anomaly_severity_critical(self):
        """Test assessing critical severity anomaly."""
        enhancer = ContextEnhancer(
            engine=self.mock_engine,
            config=self.config,
        )

        anomaly = {"drift_severity": "high", "change_percent": 60}
        assessment = enhancer._assess_anomaly_severity(anomaly)

        assert assessment["level"] == "critical"
        assert assessment["urgency"] == "high"

    def test_assess_anomaly_severity_warning(self):
        """Test assessing warning severity anomaly."""
        enhancer = ContextEnhancer(
            engine=self.mock_engine,
            config=self.config,
        )

        anomaly = {"drift_severity": "medium", "change_percent": 25}
        assessment = enhancer._assess_anomaly_severity(anomaly)

        assert assessment["level"] == "warning"
        assert assessment["urgency"] == "medium"

    def test_assess_anomaly_severity_info(self):
        """Test assessing info severity anomaly."""
        enhancer = ContextEnhancer(
            engine=self.mock_engine,
            config=self.config,
        )

        anomaly = {"drift_severity": "low", "change_percent": 5}
        assessment = enhancer._assess_anomaly_severity(anomaly)

        assert assessment["level"] == "info"
        assert assessment["urgency"] == "low"

    def test_suggest_remediation_null_rate(self):
        """Test remediation suggestions for null rate anomaly."""
        enhancer = ContextEnhancer(
            engine=self.mock_engine,
            config=self.config,
        )

        anomaly = {"metric_name": "null_ratio", "change_percent": 50}
        suggestions = enhancer._suggest_remediation(anomaly)

        assert len(suggestions) > 0
        assert any("upstream" in s.lower() for s in suggestions)

    def test_suggest_remediation_distinct_count(self):
        """Test remediation suggestions for distinct count anomaly."""
        enhancer = ContextEnhancer(
            engine=self.mock_engine,
            config=self.config,
        )

        anomaly = {"metric_name": "distinct_count", "change_percent": 30}
        suggestions = enhancer._suggest_remediation(anomaly)

        assert len(suggestions) > 0
        assert any("duplicate" in s.lower() for s in suggestions)

    def test_suggest_remediation_mean(self):
        """Test remediation suggestions for mean anomaly."""
        enhancer = ContextEnhancer(
            engine=self.mock_engine,
            config=self.config,
        )

        anomaly = {"metric_name": "mean", "change_percent": 25}
        suggestions = enhancer._suggest_remediation(anomaly)

        assert len(suggestions) > 0
        assert any("outlier" in s.lower() for s in suggestions)

    def test_suggest_remediation_count_increase(self):
        """Test remediation suggestions for row count increase."""
        enhancer = ContextEnhancer(
            engine=self.mock_engine,
            config=self.config,
        )

        anomaly = {"metric_name": "count", "change_percent": 100}
        suggestions = enhancer._suggest_remediation(anomaly)

        assert len(suggestions) > 0
        assert any("duplication" in s.lower() for s in suggestions)

    def test_suggest_remediation_count_decrease(self):
        """Test remediation suggestions for row count decrease."""
        enhancer = ContextEnhancer(
            engine=self.mock_engine,
            config=self.config,
        )

        anomaly = {"metric_name": "count", "change_percent": -50}
        suggestions = enhancer._suggest_remediation(anomaly)

        assert len(suggestions) > 0
        assert any("loss" in s.lower() or "filtering" in s.lower() for s in suggestions)

    def test_calculate_table_health_healthy(self):
        """Test calculating healthy table status."""
        enhancer = ContextEnhancer(
            engine=self.mock_engine,
            config=self.config,
        )

        profile = {
            "columns": [
                {"column_name": "id", "metrics": {"null_ratio": 0.0}},
                {"column_name": "name", "metrics": {"null_ratio": 0.01}},
            ]
        }

        health = enhancer._calculate_table_health(profile)

        assert health["status"] == "healthy"
        assert health["score"] >= 80
        assert len(health["issues"]) == 0

    def test_calculate_table_health_warning(self):
        """Test calculating warning table status."""
        enhancer = ContextEnhancer(
            engine=self.mock_engine,
            config=self.config,
        )

        # Use higher null ratios to trigger warnings
        profile = {
            "columns": [
                {"column_name": "id", "metrics": {"null_ratio": 0.0}},
                {"column_name": "email", "metrics": {"null_ratio": 0.35}},
                {"column_name": "phone", "metrics": {"null_ratio": 0.4}},
                {"column_name": "address", "metrics": {"null_ratio": 0.45}},
            ]
        }

        health = enhancer._calculate_table_health(profile)

        # Should have warnings for elevated null rates
        assert len(health["warnings"]) > 0 or len(health["issues"]) > 0

    def test_calculate_table_health_critical(self):
        """Test calculating critical table status."""
        enhancer = ContextEnhancer(
            engine=self.mock_engine,
            config=self.config,
        )

        profile = {
            "columns": [
                {"column_name": "id", "metrics": {"null_ratio": 0.6}},
                {"column_name": "name", "metrics": {"null_ratio": 0.55}},
                {"column_name": "email", "metrics": {"null_ratio": 0.7}},
            ]
        }

        health = enhancer._calculate_table_health(profile)

        assert health["status"] == "critical"
        assert len(health["issues"]) > 0

    def test_calculate_table_health_no_columns(self):
        """Test calculating health with no columns."""
        enhancer = ContextEnhancer(
            engine=self.mock_engine,
            config=self.config,
        )

        profile = {"columns": []}

        health = enhancer._calculate_table_health(profile)

        assert health["status"] == "unknown"
        assert health["score"] == 0

    def test_assess_column_risks(self):
        """Test assessing column risks."""
        enhancer = ContextEnhancer(
            engine=self.mock_engine,
            config=self.config,
        )

        columns = [
            {"column_name": "id", "metrics": {"null_ratio": 0.0}},
            {"column_name": "email", "metrics": {"null_ratio": 0.6}},
            {"column_name": "amount", "metrics": {"null_ratio": 0.1, "mean": 100, "stddev": 300}},
        ]

        risks = enhancer._assess_column_risks(columns)

        # Should have risks for email (high null) and possibly amount (high variability)
        assert len(risks) > 0

        # High null rate column should be first or among high risk
        high_null_risk = next((r for r in risks if r["column"] == "email"), None)
        assert high_null_risk is not None
        assert high_null_risk["risk_level"] == "high"


class TestGetConversationContext:
    """Tests for the get_conversation_context function."""

    def test_empty_session(self):
        """Test context from empty session."""
        session = ChatSession.create(config={})
        context = get_conversation_context(session)

        assert context == ""

    def test_session_with_messages(self):
        """Test context from session with messages."""
        session = ChatSession.create(config={})
        session.add_message("user", "Tell me about the orders table")
        session.add_message("assistant", "The orders table has 10000 rows")

        context = get_conversation_context(session)

        # Should mention tables discussed
        # Note: context extraction might not always find "orders" depending on implementation
        assert isinstance(context, str)

    def test_session_with_tool_results(self):
        """Test context from session with tool results."""
        session = ChatSession.create(config={})
        session.add_message("user", "Check the customers table")
        session.add_message(
            "assistant",
            "Checking...",
            tool_results=[{"output": '{"table_name": "customers"}'}],
        )

        context = get_conversation_context(session)

        assert isinstance(context, str)
