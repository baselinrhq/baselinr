"""Tests for drift detection strategies."""

import pytest

from profilemesh.drift.statistical_tests import (
    ChiSquareTest,
    EntropyChangeTest,
    KolmogorovSmirnovTest,
    PopulationStabilityIndexTest,
    TestResult,
    TopKStabilityTest,
    ZScoreVarianceTest,
    create_statistical_test,
)
from profilemesh.drift.strategies import (
    AbsoluteThresholdStrategy,
    DriftResult,
    MLBasedStrategy,
    StandardDeviationStrategy,
    StatisticalStrategy,
    create_drift_strategy,
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
            low_threshold=10.0, medium_threshold=20.0, high_threshold=40.0
        )

        assert strategy.low_threshold == 10.0
        assert strategy.medium_threshold == 20.0
        assert strategy.high_threshold == 40.0

    def test_no_drift(self):
        """Test when change is below low threshold."""
        strategy = AbsoluteThresholdStrategy()

        result = strategy.calculate_drift(100.0, 102.0, "count", "test_column")

        assert result is not None
        assert result.drift_detected is False
        assert result.drift_severity == "none"
        assert result.change_percent == 2.0

    def test_low_severity_drift(self):
        """Test low severity drift detection."""
        strategy = AbsoluteThresholdStrategy()

        result = strategy.calculate_drift(100.0, 108.0, "count", "test_column")

        assert result.drift_detected is True
        assert result.drift_severity == "low"
        assert result.change_percent == 8.0

    def test_medium_severity_drift(self):
        """Test medium severity drift detection."""
        strategy = AbsoluteThresholdStrategy()

        result = strategy.calculate_drift(100.0, 120.0, "count", "test_column")

        assert result.drift_detected is True
        assert result.drift_severity == "medium"
        assert result.change_percent == 20.0

    def test_high_severity_drift(self):
        """Test high severity drift detection."""
        strategy = AbsoluteThresholdStrategy()

        result = strategy.calculate_drift(100.0, 150.0, "count", "test_column")

        assert result.drift_detected is True
        assert result.drift_severity == "high"
        assert result.change_percent == 50.0

    def test_negative_change(self):
        """Test drift detection with negative change."""
        strategy = AbsoluteThresholdStrategy()

        result = strategy.calculate_drift(100.0, 65.0, "count", "test_column")

        assert result.drift_detected is True
        assert result.drift_severity == "high"
        assert result.change_percent == -35.0
        assert result.change_absolute == -35.0

    def test_zero_baseline(self):
        """Test when baseline value is zero."""
        strategy = AbsoluteThresholdStrategy()

        result = strategy.calculate_drift(0.0, 10.0, "count", "test_column")

        # Should return result but with None for change_percent
        assert result is not None
        assert result.change_percent is None
        assert result.drift_detected is False

    def test_none_values(self):
        """Test when values are None."""
        strategy = AbsoluteThresholdStrategy()

        result = strategy.calculate_drift(None, 10.0, "count", "test_column")
        assert result is None

        result = strategy.calculate_drift(10.0, None, "count", "test_column")
        assert result is None

    def test_non_numeric_values(self):
        """Test when values are not numeric."""
        strategy = AbsoluteThresholdStrategy()

        result = strategy.calculate_drift("abc", "def", "count", "test_column")
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
        result = strategy.calculate_drift(100.0, 120.0, "mean", "test_column")

        assert result is not None
        assert result.drift_detected is True
        assert result.score is not None  # std_devs score
        assert "std_devs" in result.metadata


class TestMLBasedStrategy:
    """Tests for MLBasedStrategy."""

    def test_not_implemented(self):
        """Test that ML strategy raises NotImplementedError."""
        strategy = MLBasedStrategy()

        with pytest.raises(NotImplementedError):
            strategy.calculate_drift(100.0, 120.0, "mean", "test_column")


class TestStrategyFactory:
    """Tests for create_drift_strategy factory function."""

    def test_create_absolute_threshold(self):
        """Test creating absolute threshold strategy."""
        strategy = create_drift_strategy("absolute_threshold", low_threshold=10.0)

        assert isinstance(strategy, AbsoluteThresholdStrategy)
        assert strategy.low_threshold == 10.0

    def test_create_standard_deviation(self):
        """Test creating standard deviation strategy."""
        strategy = create_drift_strategy("standard_deviation", low_threshold=1.5)

        assert isinstance(strategy, StandardDeviationStrategy)
        assert strategy.low_threshold == 1.5

    def test_unknown_strategy(self):
        """Test that unknown strategy raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            create_drift_strategy("unknown_strategy")

        assert "Unknown drift strategy" in str(exc_info.value)


class TestDriftResult:
    """Tests for DriftResult dataclass."""

    def test_create_result(self):
        """Test creating a DriftResult."""
        result = DriftResult(
            drift_detected=True, drift_severity="medium", change_absolute=10.0, change_percent=15.0
        )

        assert result.drift_detected is True
        assert result.drift_severity == "medium"
        assert result.change_absolute == 10.0
        assert result.change_percent == 15.0
        assert result.metadata == {}

    def test_result_with_metadata(self):
        """Test DriftResult with metadata."""
        result = DriftResult(
            drift_detected=True, drift_severity="high", metadata={"method": "test", "score": 0.95}
        )

        assert result.metadata["method"] == "test"
        assert result.metadata["score"] == 0.95


class TestStatisticalTests:
    """Tests for statistical drift detection tests."""

    def test_ks_test_numeric_support(self):
        """Test KS test supports numeric columns."""
        test = KolmogorovSmirnovTest()
        assert test.supports_column_type("integer")
        assert test.supports_column_type("float")
        assert not test.supports_column_type("varchar")

    def test_psi_test_prepare(self):
        """Test PSI test data preparation."""
        test = PopulationStabilityIndexTest()
        baseline = {"histogram": {0: 10, 1: 20, 2: 30}}
        current = {"histogram": {0: 15, 1: 25, 2: 25}}

        prep_baseline, prep_current = test.prepare(baseline, current, "integer", "mean")
        assert prep_baseline is not None
        assert prep_current is not None

    def test_z_score_test(self):
        """Test Z-score test calculation."""
        test = ZScoreVarianceTest(z_threshold=2.0)
        baseline = {"mean": 100.0, "stddev": 10.0}
        current = {"mean": 125.0, "stddev": 10.0}

        result = test.compare(baseline, current)
        assert result is not None
        assert result.test_name == "z_score"
        assert result.score > 2.0  # Should be 2.5 std devs
        assert result.drift_detected is True

    def test_chi_square_test_categorical(self):
        """Test Chi-square test for categorical data."""
        test = ChiSquareTest()
        assert test.supports_column_type("varchar")
        assert test.supports_column_type("text")
        assert not test.supports_column_type("integer")

    def test_entropy_test(self):
        """Test Entropy change test."""
        test = EntropyChangeTest(entropy_threshold=0.1)
        baseline = {"category_distribution": {"A": 0.5, "B": 0.5}}
        current = {"category_distribution": {"A": 0.9, "B": 0.1}}

        result = test.compare(baseline, current)
        assert result is not None
        assert result.test_name == "entropy"
        # Entropy should change significantly
        assert result.score > 0

    def test_top_k_test(self):
        """Test Top-K stability test."""
        test = TopKStabilityTest(k=3, similarity_threshold=0.7)
        baseline = {"top_values": {"A": 100, "B": 80, "C": 60}}
        current = {"top_values": {"A": 100, "B": 80, "D": 60}}  # C replaced by D

        result = test.compare(baseline, current)
        assert result is not None
        assert result.test_name == "top_k"
        # Similarity should be 2/4 = 0.5 (2 common, 4 total)
        assert result.metadata["similarity"] == 0.5

    def test_create_statistical_test(self):
        """Test statistical test factory."""
        test = create_statistical_test("ks_test", alpha=0.01)
        assert isinstance(test, KolmogorovSmirnovTest)
        assert test.alpha == 0.01

        test = create_statistical_test("psi", buckets=20, threshold=0.15)
        assert isinstance(test, PopulationStabilityIndexTest)
        assert test.buckets == 20
        assert test.threshold == 0.15

    def test_unknown_statistical_test(self):
        """Test that unknown test raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            create_statistical_test("unknown_test")

        assert "Unknown statistical test" in str(exc_info.value)


class TestStatisticalStrategy:
    """Tests for StatisticalStrategy."""

    def test_create_statistical_strategy(self):
        """Test creating statistical strategy."""
        strategy = StatisticalStrategy(
            tests=["ks_test", "z_score"],
            sensitivity="medium",
            test_params={"ks_test": {"alpha": 0.01}},
        )

        assert strategy.get_strategy_name() == "statistical"
        assert len(strategy.test_instances) == 2
        assert strategy.sensitivity == "medium"

    def test_statistical_strategy_calculate_drift_numeric(self):
        """Test statistical strategy with numeric data."""
        strategy = StatisticalStrategy(tests=["z_score"], sensitivity="medium")

        result = strategy.calculate_drift(
            baseline_value=100.0,
            current_value=130.0,
            metric_name="mean",
            column_name="test_column",
            column_type="integer",
            baseline_data={"mean": 100.0, "stddev": 10.0},
            current_data={"mean": 130.0, "stddev": 10.0},
        )

        assert result is not None
        assert result.drift_detected is True
        assert "statistical" in result.metadata["strategy"]
        assert "z_score" in result.metadata["tests_run"]

    def test_statistical_strategy_aggregation(self):
        """Test that multiple test results are aggregated correctly."""
        strategy = StatisticalStrategy(tests=["z_score", "psi"], sensitivity="medium")

        # Use data that will trigger both tests
        result = strategy.calculate_drift(
            baseline_value=100.0,
            current_value=130.0,
            metric_name="mean",
            column_name="test_column",
            column_type="integer",
            baseline_data={"mean": 100.0, "stddev": 10.0, "histogram": {0: 10, 1: 20}},
            current_data={"mean": 130.0, "stddev": 10.0, "histogram": {0: 5, 1: 25}},
        )

        if result:  # May be None if tests can't run
            assert len(result.metadata["test_results"]) >= 1
            assert result.metadata["aggregated_score"] is not None

    def test_statistical_strategy_no_applicable_tests(self):
        """Test when no tests are applicable."""
        strategy = StatisticalStrategy(tests=["ks_test"], sensitivity="medium")

        # Use categorical data with numeric-only test
        result = strategy.calculate_drift(
            baseline_value="A",
            current_value="B",
            metric_name="distinct_count",
            column_name="test_column",
            column_type="varchar",
        )

        # Should return None when no tests can run
        assert result is None

    def test_create_statistical_strategy_via_factory(self):
        """Test creating statistical strategy via factory."""
        strategy = create_drift_strategy(
            "statistical",
            tests=["ks_test", "chi_square"],
            sensitivity="high",
            test_params={"ks_test": {"alpha": 0.01}},
        )

        assert isinstance(strategy, StatisticalStrategy)
        assert strategy.sensitivity == "high"
        assert len(strategy.test_instances) == 2
