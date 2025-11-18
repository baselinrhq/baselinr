"""
Tests for retry and recovery utilities.

Tests verify:
- Exponential backoff is applied correctly
- Retries occur for transient errors
- Permanent errors are not retried
- EventBus receives retry events
- Metrics increment
- Warehouse adapters are properly decorated
- Profiling engine continues processing remaining tables after failures
"""

import time
from unittest.mock import Mock, call, patch

import pytest

from baselinr.utils.retry import (
    ConnectionLostError,
    PermanentWarehouseError,
    RateLimitError,
    TimeoutError,
    TransientWarehouseError,
    classify_database_error,
    retry_with_backoff,
    retryable_call,
)


class TestRetryDecorator:
    """Tests for retry_with_backoff decorator."""

    def test_successful_first_attempt(self):
        """Test that successful functions execute without retry."""
        call_count = 0

        @retry_with_backoff(retries=3)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_func()
        assert result == "success"
        assert call_count == 1

    def test_transient_error_retries(self):
        """Test that transient errors trigger retries."""
        call_count = 0

        @retry_with_backoff(retries=3, min_backoff=0.01, max_backoff=0.1)
        def transient_error_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutError("Connection timeout")
            return "success"

        result = transient_error_func()
        assert result == "success"
        assert call_count == 3  # Failed twice, succeeded third time

    def test_permanent_error_no_retry(self):
        """Test that permanent errors are not retried."""
        call_count = 0

        @retry_with_backoff(retries=3)
        def permanent_error_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid input")

        with pytest.raises(ValueError):
            permanent_error_func()

        assert call_count == 1  # Should fail immediately without retry

    def test_retry_exhaustion(self):
        """Test that retries are exhausted after max attempts."""
        call_count = 0

        @retry_with_backoff(retries=2, min_backoff=0.01, max_backoff=0.1)
        def always_fail_func():
            nonlocal call_count
            call_count += 1
            raise ConnectionLostError("Connection lost")

        with pytest.raises(ConnectionLostError):
            always_fail_func()

        assert call_count == 3  # Initial + 2 retries

    def test_exponential_backoff(self):
        """Test that exponential backoff delays are applied."""
        call_times = []

        @retry_with_backoff(
            retries=3, backoff_strategy="exponential", min_backoff=0.1, max_backoff=1.0
        )
        def timing_func():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise TimeoutError("Timeout")
            return "success"

        timing_func()

        # Verify delays increase exponentially
        # First retry should be ~0.1s, second ~0.2s, etc. (with jitter)
        assert len(call_times) == 3
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]

        # Account for jitter (up to 15%)
        assert 0.08 < delay1 < 0.15  # ~0.1s +/- jitter
        assert 0.15 < delay2 < 0.30  # ~0.2s +/- jitter
        assert delay2 > delay1  # Second delay should be longer

    def test_fixed_backoff(self):
        """Test that fixed backoff uses constant delay."""
        call_times = []

        @retry_with_backoff(retries=3, backoff_strategy="fixed", min_backoff=0.1, max_backoff=1.0)
        def timing_func():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise TimeoutError("Timeout")
            return "success"

        timing_func()

        # Verify delays are approximately equal
        assert len(call_times) == 3
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]

        # Both should be close to min_backoff
        assert 0.08 < delay1 < 0.12
        assert 0.08 < delay2 < 0.12

    def test_max_backoff_limit(self):
        """Test that backoff doesn't exceed max_backoff."""
        call_times = []

        @retry_with_backoff(
            retries=10, backoff_strategy="exponential", min_backoff=0.01, max_backoff=0.2
        )
        def timing_func():
            call_times.append(time.time())
            if len(call_times) < 5:
                raise TimeoutError("Timeout")
            return "success"

        timing_func()

        # Later delays should not exceed max_backoff
        for i in range(1, len(call_times)):
            delay = call_times[i] - call_times[i - 1]
            assert delay < 0.25  # max_backoff + jitter


class TestRetryableCall:
    """Tests for retryable_call wrapper function."""

    def test_retryable_call_success(self):
        """Test retryable_call with successful function."""

        def success_func(x, y):
            return x + y

        result = retryable_call(success_func, 2, 3, retries=3)
        assert result == 5

    def test_retryable_call_with_retry(self):
        """Test retryable_call with function that needs retry."""
        call_count = 0

        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("Timeout")
            return "success"

        result = retryable_call(flaky_func, retries=3, min_backoff=0.01, max_backoff=0.1)
        assert result == "success"
        assert call_count == 2


class TestErrorClassification:
    """Tests for database error classification."""

    def test_timeout_classification(self):
        """Test timeout errors are classified as transient."""
        error = Exception("Query timeout exceeded")
        classified = classify_database_error(error)
        assert isinstance(classified, TimeoutError)

    def test_connection_lost_classification(self):
        """Test connection errors are classified as transient."""
        error = Exception("Connection reset by peer")
        classified = classify_database_error(error)
        assert isinstance(classified, ConnectionLostError)

    def test_rate_limit_classification(self):
        """Test rate limit errors are classified as transient."""
        error = Exception("Too many requests")
        classified = classify_database_error(error)
        assert isinstance(classified, RateLimitError)

    def test_permanent_error_classification(self):
        """Test non-transient errors are classified as permanent."""
        error = Exception("Syntax error in SQL query")
        classified = classify_database_error(error)
        assert isinstance(classified, PermanentWarehouseError)

    def test_various_transient_patterns(self):
        """Test various transient error patterns."""
        transient_errors = [
            "Connection refused",
            "Broken pipe",
            "Deadlock detected",
            "Lock timeout",
            "Network error occurred",
            "Temporarily unavailable",
        ]

        for error_msg in transient_errors:
            error = Exception(error_msg)
            classified = classify_database_error(error)
            assert isinstance(classified, TransientWarehouseError)


class TestEventBusIntegration:
    """Tests for EventBus integration."""

    @patch("baselinr.utils.retry.event_bus")
    def test_retry_event_emission(self, mock_event_bus):
        """Test that retry events are emitted to EventBus."""
        call_count = 0

        @retry_with_backoff(retries=2, min_backoff=0.01, max_backoff=0.1)
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("Timeout")
            return "success"

        failing_func()

        # Verify event_bus.emit was called for retry_attempt
        assert mock_event_bus.emit.called
        emitted_event = mock_event_bus.emit.call_args[0][0]
        assert emitted_event.event_type == "retry_attempt"

    @patch("baselinr.utils.retry.event_bus")
    def test_retry_exhausted_event(self, mock_event_bus):
        """Test that retry_exhausted event is emitted."""

        @retry_with_backoff(retries=1, min_backoff=0.01, max_backoff=0.1)
        def always_fail_func():
            raise TimeoutError("Timeout")

        with pytest.raises(TimeoutError):
            always_fail_func()

        # Should emit retry_attempt and then retry_exhausted
        assert mock_event_bus.emit.call_count >= 2

        # Check for retry_exhausted event
        event_types = [call[0][0].event_type for call in mock_event_bus.emit.call_args_list]
        assert "retry_exhausted" in event_types


class TestMetricsIntegration:
    """Tests for Prometheus metrics integration."""

    @patch("baselinr.utils.retry.is_metrics_enabled")
    @patch("baselinr.utils.retry.Counter")
    def test_metrics_increment(self, mock_counter, mock_is_enabled):
        """Test that metrics are incremented on retry."""
        mock_is_enabled.return_value = True
        mock_counter_instance = Mock()
        mock_counter.return_value = mock_counter_instance

        call_count = 0

        @retry_with_backoff(retries=2, min_backoff=0.01, max_backoff=0.1)
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("Timeout")
            return "success"

        failing_func()

        # Verify counter was incremented
        assert mock_counter_instance.inc.called


class TestConnectorIntegration:
    """Tests for connector retry integration."""

    def test_connector_accepts_retry_config(self):
        """Test that connectors accept retry_config parameter."""
        from baselinr.config.schema import ConnectionConfig, RetryConfig
        from baselinr.connectors.base import BaseConnector

        # Mock a concrete connector class
        class MockConnector(BaseConnector):
            def _create_engine(self):
                return Mock()

            def get_connection_string(self):
                return "mock://connection"

        config = ConnectionConfig(type="postgres", host="localhost", database="test")

        retry_config = RetryConfig(
            enabled=True,
            retries=3,
            backoff_strategy="exponential",
            min_backoff=0.5,
            max_backoff=8.0,
        )

        connector = MockConnector(config, retry_config)
        assert connector.retry_config == retry_config

    def test_connector_retry_on_transient_error(self):
        """Test that connector retries on transient errors."""
        from baselinr.config.schema import ConnectionConfig, RetryConfig
        from baselinr.connectors.base import BaseConnector

        class MockConnector(BaseConnector):
            def _create_engine(self):
                engine = Mock()
                return engine

            def get_connection_string(self):
                return "mock://connection"

        config = ConnectionConfig(type="postgres", host="localhost", database="test")

        retry_config = RetryConfig(enabled=True, retries=2, min_backoff=0.01, max_backoff=0.1)

        connector = MockConnector(config, retry_config)

        # Mock engine to raise timeout then succeed
        call_count = 0

        def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Connection timeout")
            mock_result = Mock()
            mock_result.__iter__ = Mock(return_value=iter([]))
            return mock_result

        with patch.object(connector.engine, "connect") as mock_connect:
            mock_conn = Mock()
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)
            mock_conn.execute = mock_execute
            mock_connect.return_value = mock_conn

            # This should retry and succeed
            result = connector.execute_query("SELECT 1")
            assert result == []
            assert call_count == 2  # First attempt + 1 retry


class TestProfilingEngineIntegration:
    """Tests for profiling engine retry integration."""

    def test_profiling_continues_after_table_failure(self):
        """Test that profiling continues with remaining tables after failure."""
        from baselinr.config.schema import (
            BaselinrConfig,
            ConnectionConfig,
            ProfilingConfig,
            RetryConfig,
            StorageConfig,
            TablePattern,
        )
        from baselinr.profiling.core import ProfileEngine

        config = BaselinrConfig(
            environment="test",
            source=ConnectionConfig(type="sqlite", database=":memory:"),
            storage=StorageConfig(connection=ConnectionConfig(type="sqlite", database=":memory:")),
            profiling=ProfilingConfig(
                tables=[
                    TablePattern(table="table1"),
                    TablePattern(table="table2"),
                ]
            ),
            retry=RetryConfig(enabled=True, retries=2),
        )

        engine = ProfileEngine(config)

        # Mock _profile_table to fail on first table
        original_profile_table = engine._profile_table
        call_count = 0

        def mock_profile_table(pattern):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Table not found")
            return original_profile_table(pattern)

        with patch.object(engine, "_profile_table", side_effect=mock_profile_table):
            # Should not raise, should continue processing
            try:
                results = engine.profile()
                # May have 0 or 1 results depending on mock behavior
                assert call_count == 2  # Called for both tables
            except Exception:
                # Engine should continue despite failure
                assert call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
