"""
Tests for quality score trend analysis.
"""

import pytest
from datetime import datetime, timedelta, timezone
from baselinr.quality.scorer import QualityScorer
from baselinr.quality.models import DataQualityScore
from baselinr.config.schema import QualityScoringConfig


@pytest.fixture
def config():
    """Create a test quality scoring config."""
    return QualityScoringConfig()


@pytest.fixture
def scorer(config):
    """Create a quality scorer instance (no DB needed for trend analysis)."""
    from sqlalchemy import create_engine
    engine = create_engine('sqlite:///:memory:')
    return QualityScorer(engine, config)


def test_analyze_improving_trend(scorer):
    """Test trend analysis for improving scores."""
    now = datetime.now(timezone.utc)
    scores = [
        DataQualityScore(
            overall_score=70.0,
            completeness_score=75.0,
            validity_score=70.0,
            consistency_score=65.0,
            freshness_score=80.0,
            uniqueness_score=70.0,
            accuracy_score=60.0,
            status='warning',
            total_issues=10,
            critical_issues=2,
            warnings=8,
            table_name='test_table',
            schema_name='public',
            run_id='run1',
            calculated_at=now - timedelta(days=7),
            period_start=now - timedelta(days=14),
            period_end=now - timedelta(days=7),
        ),
        DataQualityScore(
            overall_score=80.0,
            completeness_score=85.0,
            validity_score=80.0,
            consistency_score=75.0,
            freshness_score=90.0,
            uniqueness_score=80.0,
            accuracy_score=70.0,
            status='healthy',
            total_issues=5,
            critical_issues=0,
            warnings=5,
            table_name='test_table',
            schema_name='public',
            run_id='run2',
            calculated_at=now,
            period_start=now - timedelta(days=7),
            period_end=now,
        ),
    ]
    
    trend = scorer.analyze_score_trend(scores)
    
    assert trend['direction'] == 'improving'
    assert trend['overall_change'] > 0
    assert trend['rate_of_change'] > 0
    assert trend['periods_analyzed'] == 2
    assert 0 <= trend['confidence'] <= 1


def test_analyze_degrading_trend(scorer):
    """Test trend analysis for degrading scores."""
    now = datetime.now(timezone.utc)
    scores = [
        DataQualityScore(
            overall_score=85.0,
            completeness_score=90.0,
            validity_score=85.0,
            consistency_score=80.0,
            freshness_score=95.0,
            uniqueness_score=85.0,
            accuracy_score=75.0,
            status='healthy',
            total_issues=2,
            critical_issues=0,
            warnings=2,
            table_name='test_table',
            schema_name='public',
            run_id='run1',
            calculated_at=now - timedelta(days=7),
            period_start=now - timedelta(days=14),
            period_end=now - timedelta(days=7),
        ),
        DataQualityScore(
            overall_score=65.0,
            completeness_score=70.0,
            validity_score=60.0,
            consistency_score=55.0,
            freshness_score=75.0,
            uniqueness_score=65.0,
            accuracy_score=55.0,
            status='warning',
            total_issues=15,
            critical_issues=3,
            warnings=12,
            table_name='test_table',
            schema_name='public',
            run_id='run2',
            calculated_at=now,
            period_start=now - timedelta(days=7),
            period_end=now,
        ),
    ]
    
    trend = scorer.analyze_score_trend(scores)
    
    assert trend['direction'] == 'degrading'
    assert trend['overall_change'] < 0
    assert trend['rate_of_change'] < 0
    assert trend['periods_analyzed'] == 2


def test_analyze_stable_trend(scorer):
    """Test trend analysis for stable scores."""
    now = datetime.now(timezone.utc)
    scores = [
        DataQualityScore(
            overall_score=80.0,
            completeness_score=85.0,
            validity_score=80.0,
            consistency_score=75.0,
            freshness_score=90.0,
            uniqueness_score=80.0,
            accuracy_score=70.0,
            status='healthy',
            total_issues=5,
            critical_issues=0,
            warnings=5,
            table_name='test_table',
            schema_name='public',
            run_id='run1',
            calculated_at=now - timedelta(days=7),
            period_start=now - timedelta(days=14),
            period_end=now - timedelta(days=7),
        ),
        DataQualityScore(
            overall_score=80.5,
            completeness_score=85.0,
            validity_score=80.0,
            consistency_score=75.0,
            freshness_score=90.0,
            uniqueness_score=80.0,
            accuracy_score=70.0,
            status='healthy',
            total_issues=5,
            critical_issues=0,
            warnings=5,
            table_name='test_table',
            schema_name='public',
            run_id='run2',
            calculated_at=now,
            period_start=now - timedelta(days=7),
            period_end=now,
        ),
    ]
    
    trend = scorer.analyze_score_trend(scores)
    
    assert trend['direction'] == 'stable'
    assert abs(trend['overall_change']) < 1.0
    assert abs(trend['rate_of_change']) < 1.0


def test_analyze_trend_insufficient_data(scorer):
    """Test trend analysis with insufficient data."""
    now = datetime.now(timezone.utc)
    scores = [
        DataQualityScore(
            overall_score=80.0,
            completeness_score=85.0,
            validity_score=80.0,
            consistency_score=75.0,
            freshness_score=90.0,
            uniqueness_score=80.0,
            accuracy_score=70.0,
            status='healthy',
            total_issues=5,
            critical_issues=0,
            warnings=5,
            table_name='test_table',
            schema_name='public',
            run_id='run1',
            calculated_at=now,
            period_start=now - timedelta(days=7),
            period_end=now,
        ),
    ]
    
    trend = scorer.analyze_score_trend(scores, min_periods=2)
    
    assert trend['direction'] == 'stable'
    assert trend['rate_of_change'] == 0.0
    assert trend['confidence'] == 0.0
    assert trend['periods_analyzed'] == 1


def test_analyze_trend_multiple_periods(scorer):
    """Test trend analysis with multiple periods."""
    now = datetime.now(timezone.utc)
    scores = [
        DataQualityScore(
            overall_score=60.0,
            completeness_score=65.0,
            validity_score=60.0,
            consistency_score=55.0,
            freshness_score=70.0,
            uniqueness_score=60.0,
            accuracy_score=50.0,
            status='warning',
            total_issues=20,
            critical_issues=5,
            warnings=15,
            table_name='test_table',
            schema_name='public',
            run_id='run1',
            calculated_at=now - timedelta(days=14),
            period_start=now - timedelta(days=21),
            period_end=now - timedelta(days=14),
        ),
        DataQualityScore(
            overall_score=70.0,
            completeness_score=75.0,
            validity_score=70.0,
            consistency_score=65.0,
            freshness_score=80.0,
            uniqueness_score=70.0,
            accuracy_score=60.0,
            status='warning',
            total_issues=15,
            critical_issues=3,
            warnings=12,
            table_name='test_table',
            schema_name='public',
            run_id='run2',
            calculated_at=now - timedelta(days=7),
            period_start=now - timedelta(days=14),
            period_end=now - timedelta(days=7),
        ),
        DataQualityScore(
            overall_score=80.0,
            completeness_score=85.0,
            validity_score=80.0,
            consistency_score=75.0,
            freshness_score=90.0,
            uniqueness_score=80.0,
            accuracy_score=70.0,
            status='healthy',
            total_issues=5,
            critical_issues=0,
            warnings=5,
            table_name='test_table',
            schema_name='public',
            run_id='run3',
            calculated_at=now,
            period_start=now - timedelta(days=7),
            period_end=now,
        ),
    ]
    
    trend = scorer.analyze_score_trend(scores)
    
    assert trend['direction'] == 'improving'
    assert trend['overall_change'] > 0
    assert trend['periods_analyzed'] == 3
    assert trend['confidence'] > 0
