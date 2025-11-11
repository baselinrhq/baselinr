"""
Core profiling engine for ProfileMesh.

Orchestrates the profiling of database tables and columns,
collecting schema information and computing metrics.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import uuid

from ..connectors.base import BaseConnector
from ..config.schema import ProfileMeshConfig, TablePattern
from .metrics import MetricCalculator

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
    
    def __init__(self, config: ProfileMeshConfig):
        """
        Initialize profiling engine.
        
        Args:
            config: ProfileMesh configuration
        """
        self.config = config
        self.connector: Optional[BaseConnector] = None
        self.metric_calculator: Optional[MetricCalculator] = None
    
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
        
        # Create metric calculator
        self.metric_calculator = MetricCalculator(
            engine=self.connector.engine,
            max_distinct_values=self.config.profiling.max_distinct_values,
            compute_histograms=self.config.profiling.compute_histograms,
            histogram_bins=self.config.profiling.histogram_bins
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
        
        # Get table metadata
        table = self.connector.get_table(pattern.table, schema=pattern.schema_)
        
        # Create result container
        result = ProfilingResult(
            run_id=run_id,
            dataset_name=pattern.table,
            schema_name=pattern.schema_,
            profiled_at=profiled_at
        )
        
        # Add table metadata
        result.metadata['row_count'] = self._get_row_count(table)
        result.metadata['column_count'] = len(table.columns)
        
        # Determine sample ratio
        sample_ratio = pattern.sample_ratio or self.config.profiling.default_sample_ratio
        
        # Profile each column
        for column in table.columns:
            logger.debug(f"Profiling column: {column.name}")
            
            try:
                metrics = self.metric_calculator.calculate_all_metrics(
                    table=table,
                    column_name=column.name,
                    sample_ratio=sample_ratio
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
        
        logger.info(f"Successfully profiled {pattern.table} with {len(result.columns)} columns")
        return result
    
    def _get_row_count(self, table) -> int:
        """Get total row count for a table."""
        from sqlalchemy import select, func
        
        with self.connector.engine.connect() as conn:
            query = select(func.count()).select_from(table)
            return conn.execute(query).scalar()

