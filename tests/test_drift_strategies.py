"""Tests for drift detection strategies."""

import pytest
from profilemesh.drift.strategies import (
    AbsoluteThresholdStrategy,
    StandardDeviationStrategy,
    MLBasedStrategy,
    create_drift_strategy,
    DriftResult
)


class TestAbsoluteThresholdStrategy:
    """Tests for AbsoluteThresholdStrategy."""
    
    def test_default_thresholds(self):
        """Test strategy with default thresholds."""
        strategy = AbsoluteThresholdStrategy()
        
        assert strategy.low_threshold == 5.0
        assert strategy.medium_threshold == 15.0
        assert strategy.high_threshold == 30.0
    
    def test_custom_thresholds(self):
        """Test strategy with custom thresholds."""
        strategy = AbsoluteThresholdStrategy(
            low_threshold=10.0,
            medium_threshold=20.0,
            high_threshold=40.0
        )
        
        assert strategy.low_threshold == 10.0
        assert strategy.medium_threshold == 20.0
        assert strategy.high_threshold == 40.0
    
    def test_no_drift(self):
        """Test when change is below low threshold."""
        strategy = AbsoluteThresholdStrategy()
        
        result = strategy.calculate_drift(100.0, 102.0, 'count', 'test_column')
        
        assert result is not None
        assert result.drift_detected is False
        assert result.drift_severity == "none"
        assert result.change_percent == 2.0
    
    def test_low_severity_drift(self):
        """Test low severity drift detection."""
        strategy = AbsoluteThresholdStrategy()
        
        result = strategy.calculate_drift(100.0, 108.0, 'count', 'test_column')
        
        assert result.drift_detected is True
        assert result.drift_severity == "low"
        assert result.change_percent == 8.0
    
    def test_medium_severity_drift(self):
        """Test medium severity drift detection."""
        strategy = AbsoluteThresholdStrategy()
        
        result = strategy.calculate_drift(100.0, 120.0, 'count', 'test_column')
        
        assert result.drift_detected is True
        assert result.drift_severity == "medium"
        assert result.change_percent == 20.0
    
    def test_high_severity_drift(self):
        """Test high severity drift detection."""
        strategy = AbsoluteThresholdStrategy()
        
        result = strategy.calculate_drift(100.0, 150.0, 'count', 'test_column')
        
        assert result.drift_detected is True
        assert result.drift_severity == "high"
        assert result.change_percent == 50.0
    
    def test_negative_change(self):
        """Test drift detection with negative change."""
        strategy = AbsoluteThresholdStrategy()
        
        result = strategy.calculate_drift(100.0, 65.0, 'count', 'test_column')
        
        assert result.drift_detected is True
        assert result.drift_severity == "high"
        assert result.change_percent == -35.0
        assert result.change_absolute == -35.0
    
    def test_zero_baseline(self):
        """Test when baseline value is zero."""
        strategy = AbsoluteThresholdStrategy()
        
        result = strategy.calculate_drift(0.0, 10.0, 'count', 'test_column')
        
        # Should return result but with None for change_percent
        assert result is not None
        assert result.change_percent is None
        assert result.drift_detected is False
    
    def test_none_values(self):
        """Test when values are None."""
        strategy = AbsoluteThresholdStrategy()
        
        result = strategy.calculate_drift(None, 10.0, 'count', 'test_column')
        assert result is None
        
        result = strategy.calculate_drift(10.0, None, 'count', 'test_column')
        assert result is None
    
    def test_non_numeric_values(self):
        """Test when values are not numeric."""
        strategy = AbsoluteThresholdStrategy()
        
        result = strategy.calculate_drift("abc", "def", 'count', 'test_column')
        assert result is None


class TestStandardDeviationStrategy:
    """Tests for StandardDeviationStrategy."""
    
    def test_default_thresholds(self):
        """Test strategy with default thresholds."""
        strategy = StandardDeviationStrategy()
        
        assert strategy.low_threshold == 1.0
        assert strategy.medium_threshold == 2.0
        assert strategy.high_threshold == 3.0
    
    def test_drift_calculation(self):
        """Test standard deviation drift calculation."""
        strategy = StandardDeviationStrategy()
        
        # 20% change ≈ 2 std devs in the simplified implementation
        result = strategy.calculate_drift(100.0, 120.0, 'mean', 'test_column')
        
        assert result is not None
        assert result.drift_detected is True
        assert result.score is not None  # std_devs score
        assert 'std_devs' in result.metadata


class TestMLBasedStrategy:
    """Tests for MLBasedStrategy."""
    
    def test_not_implemented(self):
        """Test that ML strategy raises NotImplementedError."""
        strategy = MLBasedStrategy()
        
        with pytest.raises(NotImplementedError):
            strategy.calculate_drift(100.0, 120.0, 'mean', 'test_column')


class TestStrategyFactory:
    """Tests for create_drift_strategy factory function."""
    
    def test_create_absolute_threshold(self):
        """Test creating absolute threshold strategy."""
        strategy = create_drift_strategy('absolute_threshold', low_threshold=10.0)
        
        assert isinstance(strategy, AbsoluteThresholdStrategy)
        assert strategy.low_threshold == 10.0
    
    def test_create_standard_deviation(self):
        """Test creating standard deviation strategy."""
        strategy = create_drift_strategy('standard_deviation', low_threshold=1.5)
        
        assert isinstance(strategy, StandardDeviationStrategy)
        assert strategy.low_threshold == 1.5
    
    def test_unknown_strategy(self):
        """Test that unknown strategy raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            create_drift_strategy('unknown_strategy')
        
        assert 'Unknown drift strategy' in str(exc_info.value)


class TestDriftResult:
    """Tests for DriftResult dataclass."""
    
    def test_create_result(self):
        """Test creating a DriftResult."""
        result = DriftResult(
            drift_detected=True,
            drift_severity="medium",
            change_absolute=10.0,
            change_percent=15.0
        )
        
        assert result.drift_detected is True
        assert result.drift_severity == "medium"
        assert result.change_absolute == 10.0
        assert result.change_percent == 15.0
        assert result.metadata == {}
    
    def test_result_with_metadata(self):
        """Test DriftResult with metadata."""
        result = DriftResult(
            drift_detected=True,
            drift_severity="high",
            metadata={'method': 'test', 'score': 0.95}
        )
        
        assert result.metadata['method'] == 'test'
        assert result.metadata['score'] == 0.95

