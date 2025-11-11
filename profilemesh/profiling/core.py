"""
Core profiling engine for ProfileMesh.

Orchestrates the profiling of database tables and columns,
collecting schema information and computing metrics.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import uuid
import time

from ..connectors.base import BaseConnector
from ..config.schema import ProfileMeshConfig, TablePattern
from .metrics import MetricCalculator
from .query_builder import QueryBuilder
from ..events import EventBus, ProfilingStarted, ProfilingCompleted, ProfilingFailed

logger = logging.getLogger(__name__)


class ProfilingResult:
    """Container for profiling results."""
    
    def __init__(
        self,
        run_id: str,
        dataset_name: str,
        schema_name: Optional[str],
        profiled_at: datetime
    ):
        """
        Initialize profiling result container.
        
        Args:
            run_id: Unique identifier for this profiling run
            dataset_name: Name of the dataset/table profiled
            schema_name: Schema name (if applicable)
            profiled_at: Timestamp of profiling
        """
        self.run_id = run_id
        self.dataset_name = dataset_name
        self.schema_name = schema_name
        self.profiled_at = profiled_at
        self.columns: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}
    
    def add_column_metrics(
        self,
        column_name: str,
        column_type: str,
        metrics: Dict[str, Any]
    ):
        """
        Add metrics for a column.
        
        Args:
            column_name: Name of the column
            column_type: Data type of the column
            metrics: Dictionary of metric_name -> metric_value
        """
        self.columns.append({
            'column_name': column_name,
            'column_type': column_type,
            'metrics': metrics
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'run_id': self.run_id,
            'dataset_name': self.dataset_name,
            'schema_name': self.schema_name,
            'profiled_at': self.profiled_at.isoformat(),
            'columns': self.columns,
            'metadata': self.metadata
        }


class ProfileEngine:
    """Main profiling engine for ProfileMesh."""
    
    def __init__(self, config: ProfileMeshConfig, event_bus: Optional[EventBus] = None):
        """
        Initialize profiling engine.
        
        Args:
            config: ProfileMesh configuration
            event_bus: Optional event bus for emitting profiling events
        """
        self.config = config
        self.connector: Optional[BaseConnector] = None
        self.metric_calculator: Optional[MetricCalculator] = None
        self.event_bus = event_bus
    
    def profile(self, table_patterns: Optional[List[TablePattern]] = None) -> List[ProfilingResult]:
        """
        Profile tables according to configuration.
        
        Args:
            table_patterns: Optional list of table patterns to profile
                          (uses config if not provided)
        
        Returns:
            List of profiling results
        """
        patterns = table_patterns or self.config.profiling.tables
        
        if not patterns:
            logger.warning("No table patterns specified for profiling")
            return []
        
        # Create connector
        from ..connectors import PostgresConnector, SnowflakeConnector, SQLiteConnector
        
        if self.config.source.type == "postgres":
            self.connector = PostgresConnector(self.config.source)
        elif self.config.source.type == "snowflake":
            self.connector = SnowflakeConnector(self.config.source)
        elif self.config.source.type == "sqlite":
            self.connector = SQLiteConnector(self.config.source)
        else:
            raise ValueError(f"Unsupported database type: {self.config.source.type}")
        
        # Create query builder for partition/sampling support
        self.query_builder = QueryBuilder(database_type=self.config.source.type)
        
        # Create metric calculator
        self.metric_calculator = MetricCalculator(
            engine=self.connector.engine,
            max_distinct_values=self.config.profiling.max_distinct_values,
            compute_histograms=self.config.profiling.compute_histograms,
            histogram_bins=self.config.profiling.histogram_bins,
            enabled_metrics=self.config.profiling.metrics,
            query_builder=self.query_builder
        )
        
        # Profile each table pattern
        results = []
        for pattern in patterns:
            try:
                result = self._profile_table(pattern)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to profile {pattern.table}: {e}", exc_info=True)
        
        # Cleanup
        if self.connector:
            self.connector.close()
        
        return results
    
    def _profile_table(self, pattern: TablePattern) -> ProfilingResult:
        """
        Profile a single table.
        
        Args:
            pattern: Table pattern configuration
            
        Returns:
            ProfilingResult for this table
        """
        logger.info(f"Profiling table: {pattern.table}")
        
        # Generate run ID
        run_id = str(uuid.uuid4())
        profiled_at = datetime.utcnow()
        start_time = time.time()
        
        # Emit profiling started event
        if self.event_bus:
            self.event_bus.emit(ProfilingStarted(
                event_type="ProfilingStarted",
                timestamp=profiled_at,
                table=pattern.table,
                run_id=run_id,
                metadata={}
            ))
        
        try:
            # Get table metadata
            table = self.connector.get_table(pattern.table, schema=pattern.schema_)
            
            # Create result container
            result = ProfilingResult(
                run_id=run_id,
                dataset_name=pattern.table,
                schema_name=pattern.schema_,
                profiled_at=profiled_at
            )
            
            # Infer partition key if metadata_fallback is enabled
            partition_config = pattern.partition
            if partition_config and partition_config.metadata_fallback and not partition_config.key:
                inferred_key = self.query_builder.infer_partition_key(table)
                if inferred_key:
                    partition_config.key = inferred_key
                    logger.info(f"Using inferred partition key: {inferred_key}")
            
            # Add table metadata
            result.metadata['row_count'] = self._get_row_count(table, partition_config, pattern.sampling)
            result.metadata['column_count'] = len(table.columns)
            result.metadata['partition_config'] = partition_config.model_dump() if partition_config else None
            result.metadata['sampling_config'] = pattern.sampling.model_dump() if pattern.sampling else None
            
            # Profile each column
            for column in table.columns:
                logger.debug(f"Profiling column: {column.name}")
                
                try:
                    metrics = self.metric_calculator.calculate_all_metrics(
                        table=table,
                        column_name=column.name,
                        partition_config=partition_config,
                        sampling_config=pattern.sampling
                    )
                    
                    result.add_column_metrics(
                        column_name=column.name,
                        column_type=str(column.type),
                        metrics=metrics
                    )
                except Exception as e:
                    logger.error(f"Failed to profile column {column.name}: {e}")
                    # Add error marker
                    result.add_column_metrics(
                        column_name=column.name,
                        column_type=str(column.type),
                        metrics={'error': str(e)}
                    )
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Emit profiling completed event
            if self.event_bus:
                self.event_bus.emit(ProfilingCompleted(
                    event_type="ProfilingCompleted",
                    timestamp=datetime.utcnow(),
                    table=pattern.table,
                    run_id=run_id,
                    row_count=result.metadata.get('row_count', 0),
                    column_count=result.metadata.get('column_count', 0),
                    duration_seconds=duration,
                    metadata={}
                ))
            
            logger.info(f"Successfully profiled {pattern.table} with {len(result.columns)} columns in {duration:.2f}s")
            return result
            
        except Exception as e:
            # Emit profiling failed event
            if self.event_bus:
                self.event_bus.emit(ProfilingFailed(
                    event_type="ProfilingFailed",
                    timestamp=datetime.utcnow(),
                    table=pattern.table,
                    run_id=run_id,
                    error=str(e),
                    metadata={}
                ))
            raise
    
    def _get_row_count(
        self,
        table,
        partition_config=None,
        sampling_config=None
    ) -> int:
        """
        Get row count for a table (with optional partition/sampling).
        
        Args:
            table: SQLAlchemy Table object
            partition_config: Partition configuration
            sampling_config: Sampling configuration
            
        Returns:
            Row count
        """
        from sqlalchemy import select, func
        
        with self.connector.engine.connect() as conn:
            # Build query with partition filtering
            query, _ = self.query_builder.build_profiling_query(
                table=table,
                partition_config=partition_config,
                sampling_config=None  # Don't apply sampling for count
            )
            
            # Count rows
            count_query = select(func.count()).select_from(query.alias())
            return conn.execute(count_query).scalar()

