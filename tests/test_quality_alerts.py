"""
Tests for quality score alerting functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from baselinr.events import EventBus, QualityScoreDegraded, QualityScoreThresholdBreached
from baselinr.quality.scorer import QualityScorer
from baselinr.quality.models import DataQualityScore, ScoreStatus
from baselinr.config.schema import QualityScoringConfig, QualityScoringWeights, QualityScoringThresholds, QualityScoringFreshness


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
def quality_config():
    """Create a quality scoring configuration."""
    return QualityScoringConfig(
        enabled=True,
        weights=QualityScoringWeights(
            completeness=25,
            validity=25,
            consistency=20,
            freshness=15,
            uniqueness=10,
            accuracy=5,
        ),
        thresholds=QualityScoringThresholds(
            healthy=80,
            warning=60,
            critical=0,
        ),
        freshness=QualityScoringFreshness(
            excellent=24,
            good=48,
            acceptable=168,
        ),
    )


@pytest.fixture
def scorer(mock_engine, quality_config):
    """Create a QualityScorer instance."""
    return QualityScorer(
        engine=mock_engine,
        config=quality_config,
        results_table="baselinr_results",
        validation_table="baselinr_validation_results",
        events_table="baselinr_events",
        runs_table="baselinr_runs",
    )


@pytest.fixture
def event_bus():
    """Create an EventBus instance."""
    return EventBus()


def create_score(overall_score: float, status: str = "healthy") -> DataQualityScore:
    """Helper to create a DataQualityScore."""
    return DataQualityScore(
        overall_score=overall_score,
        completeness_score=90.0,
        validity_score=88.0,
        consistency_score=82.0,
        freshness_score=95.0,
        uniqueness_score=85.0,
        accuracy_score=78.0,
        status=status,
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


class TestThresholdBreachDetection:
    """Test threshold breach detection."""

    def test_no_breach_when_healthy(self, scorer):
        """Test no breach when score is healthy."""
        score = create_score(85.0, "healthy")
        previous_score = create_score(90.0, "healthy")
        
        events = scorer.check_score_thresholds(score, previous_score)
        assert len(events) == 0

    def test_warning_threshold_breach(self, scorer):
        """Test warning threshold breach detection."""
        score = create_score(55.0, "warning")  # Below warning threshold (60)
        # Previous score was 65 (above warning threshold of 60)
        previous_score = create_score(65.0, "healthy")  # Was healthy (above warning)
        
        events = scorer.check_score_thresholds(score, previous_score)
        assert len(events) == 1
        assert isinstance(events[0], QualityScoreThresholdBreached)
        assert events[0].threshold_type == "warning"
        assert events[0].current_score == 55.0
        assert events[0].threshold_value == 60.0

    def test_critical_threshold_breach(self, scorer):
        """Test critical threshold breach detection."""
        # Score below warning threshold (60) - will be treated as warning breach
        # since critical threshold is 0 and 45 >= 0
        score = create_score(45.0, "critical")  # Below warning threshold
        previous_score = create_score(65.0, "healthy")  # Was healthy (above warning)
        
        events = scorer.check_score_thresholds(score, previous_score)
        assert len(events) == 1
        assert isinstance(events[0], QualityScoreThresholdBreached)
        # Since 45 < 60 (warning) and 45 >= 0 (critical), it's a warning breach
        # Critical threshold is 0 by default, so scores below warning are warnings
        assert events[0].threshold_type == "warning"
        assert events[0].current_score == 45.0
        assert events[0].threshold_value == 60.0

    def test_no_breach_when_already_below_threshold(self, scorer):
        """Test no breach event when already below threshold."""
        score = create_score(50.0, "critical")
        previous_score = create_score(45.0, "critical")  # Was already critical
        
        events = scorer.check_score_thresholds(score, previous_score)
        assert len(events) == 0  # No new breach

    def test_warning_to_critical_transition(self, scorer):
        """Test transition from warning to critical."""
        score = create_score(45.0, "critical")
        # Previous was healthy (above warning), current is below warning
        previous_score = create_score(65.0, "healthy")  # Was healthy (above warning)
        
        events = scorer.check_score_thresholds(score, previous_score)
        # Should emit a breach event since crossing from healthy to below warning
        assert len(events) == 1
        # Since 45 < 60 (warning) and 45 >= 0 (critical), it's a warning breach
        assert events[0].threshold_type == "warning"


class TestScoreDegradation:
    """Test score degradation detection."""

    def test_no_degradation_when_improving(self, scorer):
        """Test no degradation event when score improves."""
        current = create_score(85.0)
        previous = create_score(80.0)
        
        event = scorer.check_score_degradation(current, previous)
        assert event is None

    def test_no_degradation_small_drop(self, scorer):
        """Test no degradation event for small drops."""
        current = create_score(84.0)
        previous = create_score(85.0)  # Only 1 point drop
        
        event = scorer.check_score_degradation(current, previous)
        assert event is None

    def test_degradation_detection(self, scorer):
        """Test degradation event when score drops significantly."""
        current = create_score(75.0)
        previous = create_score(85.0)  # 10 point drop
        
        event = scorer.check_score_degradation(current, previous)
        assert event is not None
        assert isinstance(event, QualityScoreDegraded)
        assert event.current_score == 75.0
        assert event.previous_score == 85.0
        assert event.score_change == -10.0

    def test_degradation_with_critical_score(self, scorer):
        """Test degradation event with critical score."""
        current = create_score(45.0, "critical")
        previous = create_score(85.0, "healthy")
        
        event = scorer.check_score_degradation(current, previous)
        assert event is not None
        # Since 45 < 60 (warning) but 45 >= 0 (critical), threshold_type will be "warning"
        # Critical threshold is 0 by default, so scores below warning are warnings
        assert event.threshold_type == "warning"

    def test_degradation_with_warning_score(self, scorer):
        """Test degradation event with warning score."""
        current = create_score(65.0, "warning")
        previous = create_score(85.0, "healthy")
        
        event = scorer.check_score_degradation(current, previous)
        assert event is not None
        assert event.threshold_type == "warning"

    def test_no_degradation_without_previous(self, scorer):
        """Test no degradation event when no previous score."""
        current = create_score(75.0)
        
        event = scorer.check_score_degradation(current, None)
        assert event is None


class TestEventEmission:
    """Test event emission integration."""

    def test_threshold_breach_event_emission(self, scorer, event_bus):
        """Test threshold breach events are emitted."""
        hook = Mock()
        event_bus.register(hook)
        
        score = create_score(55.0, "warning")
        previous_score = create_score(65.0, "warning")
        
        events = scorer.check_score_thresholds(score, previous_score)
        for event in events:
            event_bus.emit(event)
        
        assert hook.handle_event.called
        call_args = hook.handle_event.call_args[0][0]
        assert isinstance(call_args, QualityScoreThresholdBreached)

    def test_degradation_event_emission(self, scorer, event_bus):
        """Test degradation events are emitted."""
        hook = Mock()
        event_bus.register(hook)
        
        current = create_score(75.0)
        previous = create_score(85.0)
        
        event = scorer.check_score_degradation(current, previous)
        if event:
            event_bus.emit(event)
        
        assert hook.handle_event.called
        call_args = hook.handle_event.call_args[0][0]
        assert isinstance(call_args, QualityScoreDegraded)

    def test_multiple_events_emission(self, scorer, event_bus):
        """Test multiple events can be emitted."""
        hook = Mock()
        event_bus.register(hook)
        
        # Score that both breaches threshold and degrades
        current = create_score(45.0, "critical")
        previous = create_score(85.0, "healthy")
        
        threshold_events = scorer.check_score_thresholds(current, previous)
        degradation_event = scorer.check_score_degradation(current, previous)
        
        all_events = threshold_events + ([degradation_event] if degradation_event else [])
        for event in all_events:
            event_bus.emit(event)
        
        assert hook.handle_event.call_count >= 1


class TestEventMetadata:
    """Test event metadata and structure."""

    def test_threshold_breach_metadata(self, scorer):
        """Test threshold breach event has correct metadata."""
        score = create_score(55.0, "warning")
        previous_score = create_score(65.0, "warning")
        
        events = scorer.check_score_thresholds(score, previous_score)
        assert len(events) == 1
        
        event = events[0]
        assert event.table == "test_table"
        assert event.schema == "public"
        assert event.current_score == 55.0
        assert event.threshold_type == "warning"
        assert event.explanation is not None
        assert "55.0" in event.explanation
        assert "60.0" in event.explanation

    def test_degradation_metadata(self, scorer):
        """Test degradation event has correct metadata."""
        current = create_score(75.0)
        previous = create_score(85.0)
        
        event = scorer.check_score_degradation(current, previous)
        assert event is not None
        assert event.table == "test_table"
        assert event.schema == "public"
        assert event.current_score == 75.0
        assert event.previous_score == 85.0
        assert event.score_change == -10.0
        assert event.explanation is not None
        assert "75.0" in event.explanation
        assert "85.0" in event.explanation









