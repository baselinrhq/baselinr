"""
Tests for worker pool functionality.

Verifies:
- Backward compatibility (sequential execution)
- Worker pool creation and configuration
- Parallel execution
- Error isolation
- Metrics integration
- Event emission
- Thread safety
"""

import time
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from baselinr.config.schema import ExecutionConfig, TablePattern
from baselinr.utils.worker_pool import WorkerPool, profile_table_task


class TestExecutionConfig:
    """Test ExecutionConfig defaults and validation."""

    def test_default_config_is_sequential(self):
        """Default config should have max_workers=1 (sequential)."""
        config = ExecutionConfig()
        assert config.max_workers == 1
        assert config.batch_size == 10
        assert config.queue_size == 100

    def test_parallel_config(self):
        """Can create config with parallelism enabled."""
        config = ExecutionConfig(max_workers=8)
        assert config.max_workers == 8

    def test_validate_max_workers_exceeds_limit(self):
        """Should raise error if max_workers exceeds reasonable limit."""
        import os

        cpu_count = os.cpu_count() or 4
        excessive_workers = cpu_count * 4 + 1

        with pytest.raises(ValueError, match="should not exceed"):
            ExecutionConfig(max_workers=excessive_workers)

    def test_warehouse_limits(self):
        """Can specify warehouse-specific limits."""
        config = ExecutionConfig(
            max_workers=16, warehouse_limits={"snowflake": 20, "postgres": 8, "sqlite": 1}
        )
        assert config.warehouse_limits["snowflake"] == 20
        assert config.warehouse_limits["postgres"] == 8
        assert config.warehouse_limits["sqlite"] == 1


class TestWorkerPool:
    """Test WorkerPool creation and lifecycle."""

    def test_cannot_create_with_single_worker(self):
        """WorkerPool requires max_workers > 1."""
        with pytest.raises(ValueError, match="requires max_workers > 1"):
            WorkerPool(max_workers=1)

    def test_create_worker_pool(self):
        """Can create worker pool with multiple workers."""
        pool = WorkerPool(max_workers=4, queue_size=10, warehouse_type="postgres")
        assert pool.max_workers == 4
        assert pool.queue_size == 10
        assert pool.warehouse_type == "postgres"
        pool.shutdown(wait=False)

    def test_submit_task(self):
        """Can submit tasks to worker pool."""
        pool = WorkerPool(max_workers=2)

        def simple_task(x):
            return x * 2

        future = pool.submit(simple_task, 5)
        result = future.result(timeout=5)

        assert result == 10
        pool.shutdown(wait=True)

    def test_submit_batch(self):
        """Can submit multiple tasks as a batch."""
        pool = WorkerPool(max_workers=4)

        def square(x):
            return x**2

        tasks = [(square, (2,), {}), (square, (3,), {}), (square, (4,), {}), (square, (5,), {})]

        futures = pool.submit_batch(tasks)
        results = [f.result(timeout=5) for f in futures]

        assert results == [4, 9, 16, 25]
        pool.shutdown(wait=True)

    def test_wait_for_completion(self):
        """Can wait for all futures to complete."""
        pool = WorkerPool(max_workers=4)

        def slow_task(x):
            time.sleep(0.1)
            return x

        futures = []
        for i in range(8):
            future = pool.submit(slow_task, i)
            futures.append(future)

        results = pool.wait_for_completion(futures, timeout=5)

        assert len(results) == 8
        assert set(results) == {0, 1, 2, 3, 4, 5, 6, 7}
        pool.shutdown(wait=True)

    def test_error_isolation(self):
        """Errors in one task should not affect others."""
        pool = WorkerPool(max_workers=4)

        def failing_task(x):
            if x == 2:
                raise ValueError("Intentional failure")
            return x * 2

        futures = []
        for i in range(5):
            future = pool.submit(failing_task, i)
            futures.append(future)

        results = pool.wait_for_completion(futures, timeout=5)

        # Failed task should return None
        assert results[0] == 0
        assert results[1] == 2
        assert results[2] is None  # Failed task
        assert results[3] == 6
        assert results[4] == 8

        pool.shutdown(wait=True)

    def test_shutdown_gracefully(self):
        """Worker pool can shutdown gracefully."""
        pool = WorkerPool(max_workers=2)

        def task():
            time.sleep(0.1)
            return "done"

        # Submit some tasks
        futures = [pool.submit(task) for _ in range(4)]

        # Shutdown and wait
        pool.shutdown(wait=True, timeout=5)

        # All tasks should complete
        for future in futures:
            assert future.result(timeout=1) == "done"


class TestProfileTableTask:
    """Test profile_table_task wrapper function."""

    def test_profile_table_success(self):
        """Successful table profiling returns result."""
        # Mock engine
        mock_engine = Mock()
        mock_result = Mock()
        mock_result.dataset_name = "test_table"
        mock_engine._profile_table = Mock(return_value=mock_result)

        # Mock pattern
        pattern = TablePattern(table="test_table", schema="public")

        # Execute task
        result = profile_table_task(mock_engine, pattern)

        assert result == mock_result
        mock_engine._profile_table.assert_called_once_with(pattern)

    def test_profile_table_failure_returns_none(self):
        """Failed table profiling returns None (error isolation)."""
        # Mock engine that raises error
        mock_engine = Mock()
        mock_engine._profile_table = Mock(side_effect=ValueError("Connection lost"))

        # Mock pattern
        pattern = TablePattern(table="test_table")

        # Execute task
        result = profile_table_task(mock_engine, pattern)

        # Should return None on failure
        assert result is None

    def test_profile_table_with_event_bus(self):
        """Task emits events to event bus."""
        # Mock engine
        mock_engine = Mock()
        mock_result = Mock()
        mock_engine._profile_table = Mock(return_value=mock_result)

        # Mock event bus
        mock_event_bus = Mock()

        # Mock pattern
        pattern = TablePattern(table="test_table")

        # Execute task
        result = profile_table_task(mock_engine, pattern, event_bus=mock_event_bus)

        assert result == mock_result
        # Should emit at least 2 events (started, completed)
        assert mock_event_bus.emit.call_count >= 2


class TestBackwardCompatibility:
    """Test backward compatibility with sequential execution."""

    def test_default_execution_config_no_worker_pool(self):
        """Default config (max_workers=1) should not create worker pool."""
        from baselinr.config.schema import BaselinrConfig, ConnectionConfig, StorageConfig

        config = BaselinrConfig(
            source=ConnectionConfig(type="sqlite", database="test.db"),
            storage=StorageConfig(connection=ConnectionConfig(type="sqlite", database="test.db")),
        )

        # Execution config should default to sequential
        assert config.execution.max_workers == 1

    @patch("baselinr.connectors.factory.create_connector")
    def test_sequential_execution_no_worker_pool(self, mock_create_conn):
        """Sequential execution should not use worker pool."""
        from baselinr.config.schema import (
            BaselinrConfig,
            ConnectionConfig,
            ProfilingConfig,
            StorageConfig,
            TablePattern,
        )
        from baselinr.profiling.core import ProfileEngine

        # Setup mock connector
        mock_connector = Mock()
        mock_connector.engine = Mock()
        mock_create_conn.return_value = mock_connector

        config = BaselinrConfig(
            source=ConnectionConfig(type="postgres", database="test", host="localhost"),
            storage=StorageConfig(
                connection=ConnectionConfig(type="postgres", database="test", host="localhost")
            ),
            profiling=ProfilingConfig(
                tables=[TablePattern(table="test1"), TablePattern(table="test2")]
            ),
        )

        engine = ProfileEngine(config)

        # Should NOT have worker pool
        assert engine.worker_pool is None

    @patch("baselinr.connectors.factory.create_connector")
    def test_parallel_execution_creates_worker_pool(self, mock_create_conn):
        """Parallel execution (max_workers > 1) should create worker pool."""
        from baselinr.config.schema import (
            BaselinrConfig,
            ConnectionConfig,
            ExecutionConfig,
            ProfilingConfig,
            StorageConfig,
            TablePattern,
        )
        from baselinr.profiling.core import ProfileEngine

        # Setup mock connector
        mock_connector = Mock()
        mock_connector.engine = Mock()
        mock_create_conn.return_value = mock_connector

        config = BaselinrConfig(
            source=ConnectionConfig(type="postgres", database="test", host="localhost"),
            storage=StorageConfig(
                connection=ConnectionConfig(type="postgres", database="test", host="localhost")
            ),
            profiling=ProfilingConfig(
                tables=[TablePattern(table="test1"), TablePattern(table="test2")]
            ),
            execution=ExecutionConfig(max_workers=4),
        )

        engine = ProfileEngine(config)

        # Should have worker pool
        assert engine.worker_pool is not None
        assert engine.worker_pool.max_workers == 4


class TestWarehouseSpecificLimits:
    """Test warehouse-specific worker limits."""

    @patch("baselinr.connectors.factory.create_connector")
    def test_sqlite_forces_sequential(self, mock_create_conn):
        """SQLite should force sequential execution even if parallel configured."""
        from baselinr.config.schema import (
            BaselinrConfig,
            ConnectionConfig,
            ExecutionConfig,
            ProfilingConfig,
            StorageConfig,
        )
        from baselinr.profiling.core import ProfileEngine

        # Setup mock connector
        mock_connector = Mock()
        mock_connector.engine = Mock()
        mock_create_conn.return_value = mock_connector

        config = BaselinrConfig(
            source=ConnectionConfig(type="sqlite", database="test.db"),
            storage=StorageConfig(connection=ConnectionConfig(type="sqlite", database="test.db")),
            execution=ExecutionConfig(max_workers=8),  # Request parallelism
        )

        engine = ProfileEngine(config)

        # Should NOT create worker pool for SQLite
        assert engine.worker_pool is None

    @patch("baselinr.connectors.factory.create_connector")
    def test_warehouse_limit_overrides_max_workers(self, mock_create_conn):
        """Warehouse-specific limit should override max_workers."""
        from baselinr.config.schema import (
            BaselinrConfig,
            ConnectionConfig,
            ExecutionConfig,
            ProfilingConfig,
            StorageConfig,
        )
        from baselinr.profiling.core import ProfileEngine

        # Setup mock connector
        mock_connector = Mock()
        mock_connector.engine = Mock()
        mock_create_conn.return_value = mock_connector

        config = BaselinrConfig(
            source=ConnectionConfig(type="postgres", database="test", host="localhost"),
            storage=StorageConfig(
                connection=ConnectionConfig(type="postgres", database="test", host="localhost")
            ),
            execution=ExecutionConfig(
                max_workers=16, warehouse_limits={"postgres": 8}  # Limit postgres to 8
            ),
        )

        engine = ProfileEngine(config)

        # Should use warehouse-specific limit
        assert engine.worker_pool is not None
        assert engine.worker_pool.max_workers == 8


class TestConnectionPooling:
    """Test connection pool configuration."""

    def test_sequential_execution_default_pool(self):
        """Sequential execution should use default pool size."""
        from baselinr.config.schema import ConnectionConfig, ExecutionConfig
        from baselinr.connectors.base import BaseConnector

        class TestConnector(BaseConnector):
            def _create_engine(self):
                return None

            def get_connection_string(self):
                return "test://"

        connector = TestConnector(
            ConnectionConfig(type="postgres", database="test"),
            execution_config=ExecutionConfig(max_workers=1),
        )

        pool_config = connector._get_pool_config()

        assert pool_config["pool_size"] == 5
        assert pool_config["max_overflow"] == 10

    def test_parallel_execution_larger_pool(self):
        """Parallel execution should use larger pool size."""
        from baselinr.config.schema import ConnectionConfig, ExecutionConfig
        from baselinr.connectors.base import BaseConnector

        class TestConnector(BaseConnector):
            def _create_engine(self):
                return None

            def get_connection_string(self):
                return "test://"

        connector = TestConnector(
            ConnectionConfig(type="postgres", database="test"),
            execution_config=ExecutionConfig(max_workers=8),
        )

        pool_config = connector._get_pool_config()

        # pool_size = min(max_workers + 2, 20)
        assert pool_config["pool_size"] == 10  # 8 + 2
        assert pool_config["max_overflow"] == 8

    def test_pool_size_capped_at_20(self):
        """Pool size should be capped at 20."""
        from baselinr.config.schema import ConnectionConfig, ExecutionConfig
        from baselinr.connectors.base import BaseConnector

        class TestConnector(BaseConnector):
            def _create_engine(self):
                return None

            def get_connection_string(self):
                return "test://"

        with patch("baselinr.config.schema.os.cpu_count", return_value=32):
            connector = TestConnector(
                ConnectionConfig(type="postgres", database="test"),
                execution_config=ExecutionConfig(max_workers=30),
            )

        pool_config = connector._get_pool_config()

        # Pool size capped at 20
        assert pool_config["pool_size"] == 20
        assert pool_config["max_overflow"] == 30


@pytest.mark.integration
class TestIntegration:
    """Integration tests for worker pool with ProfileEngine."""

    @pytest.mark.skip(reason="Requires database setup")
    def test_parallel_profiling_multiple_tables(self):
        """End-to-end test of parallel profiling."""
        # This would require actual database setup
        # Left as placeholder for manual testing
        pass
