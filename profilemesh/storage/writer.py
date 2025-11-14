"""
Results writer for ProfileMesh.

Writes profiling results to storage backend with support
for historical tracking and drift detection.
"""

from typing import List, Optional
from datetime import datetime
import logging
from sqlalchemy import text, MetaData, Table, Column, String, Float, DateTime, Integer, Text
from sqlalchemy.engine import Engine

from ..profiling.core import ProfilingResult
from ..config.schema import StorageConfig

logger = logging.getLogger(__name__)


class ResultWriter:
    """Writes profiling results to storage backend."""
    
    def __init__(self, config: StorageConfig):
        """
        Initialize result writer.
        
        Args:
            config: Storage configuration
        """
        self.config = config
        self.engine: Optional[Engine] = None
        self._setup_connection()
        
        if self.config.create_tables:
            self._create_tables()
    
    def _setup_connection(self):
        """Setup database connection for storage."""
        from ..connectors import (
            PostgresConnector, SnowflakeConnector, SQLiteConnector,
            MySQLConnector, BigQueryConnector, RedshiftConnector
        )
        
        if self.config.connection.type == "postgres":
            connector = PostgresConnector(self.config.connection)
        elif self.config.connection.type == "snowflake":
            connector = SnowflakeConnector(self.config.connection)
        elif self.config.connection.type == "sqlite":
            connector = SQLiteConnector(self.config.connection)
        elif self.config.connection.type == "mysql":
            connector = MySQLConnector(self.config.connection)
        elif self.config.connection.type == "bigquery":
            connector = BigQueryConnector(self.config.connection)
        elif self.config.connection.type == "redshift":
            connector = RedshiftConnector(self.config.connection)
        else:
            raise ValueError(f"Unsupported storage type: {self.config.connection.type}")
        
        self.engine = connector.engine
    
    def _create_tables(self):
        """Create storage tables if they don't exist."""
        metadata = MetaData()
        
        # Runs table - tracks profiling runs
        runs_table = Table(
            self.config.runs_table,
            metadata,
            Column('run_id', String(36), primary_key=True),
            Column('dataset_name', String(255), nullable=False),
            Column('schema_name', String(255)),
            Column('profiled_at', DateTime, nullable=False),
            Column('environment', String(50)),
            Column('status', String(20)),
            Column('row_count', Integer),
            Column('column_count', Integer)
        )
        
        # Results table - stores individual metrics
        results_table = Table(
            self.config.results_table,
            metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('run_id', String(36), nullable=False),
            Column('dataset_name', String(255), nullable=False),
            Column('schema_name', String(255)),
            Column('column_name', String(255), nullable=False),
            Column('column_type', String(100)),
            Column('metric_name', String(100), nullable=False),
            Column('metric_value', Text),
            Column('profiled_at', DateTime, nullable=False)
        )
        
        # Create tables
        with self.engine.connect() as conn:
            metadata.create_all(self.engine)
            conn.commit()
        
        logger.info("Storage tables created successfully")
    
    def write_results(self, results: List[ProfilingResult], environment: str = "development"):
        """
        Write profiling results to storage.
        
        Args:
            results: List of profiling results to write
            environment: Environment name (dev/test/prod)
        """
        with self.engine.connect() as conn:
            for result in results:
                # Write run metadata
                self._write_run(conn, result, environment)
                
                # Write column metrics
                self._write_metrics(conn, result)
            
            conn.commit()
        
        logger.info(f"Wrote {len(results)} profiling results to storage")
    
    def _write_run(self, conn, result: ProfilingResult, environment: str):
        """Write run metadata."""
        insert_query = text(f"""
            INSERT INTO {self.config.runs_table}
            (run_id, dataset_name, schema_name, profiled_at, environment, status, row_count, column_count)
            VALUES (:run_id, :dataset_name, :schema_name, :profiled_at, :environment, :status, :row_count, :column_count)
        """)
        
        conn.execute(insert_query, {
            'run_id': result.run_id,
            'dataset_name': result.dataset_name,
            'schema_name': result.schema_name,
            'profiled_at': result.profiled_at,
            'environment': environment,
            'status': 'completed',
            'row_count': result.metadata.get('row_count'),
            'column_count': result.metadata.get('column_count')
        })
    
    def _write_metrics(self, conn, result: ProfilingResult):
        """Write column metrics."""
        insert_query = text(f"""
            INSERT INTO {self.config.results_table}
            (run_id, dataset_name, schema_name, column_name, column_type, metric_name, metric_value, profiled_at)
            VALUES (:run_id, :dataset_name, :schema_name, :column_name, :column_type, :metric_name, :metric_value, :profiled_at)
        """)
        
        for column_data in result.columns:
            column_name = column_data['column_name']
            column_type = column_data['column_type']
            
            for metric_name, metric_value in column_data['metrics'].items():
                # Convert metric value to string for storage
                if metric_value is not None:
                    metric_value_str = str(metric_value)
                else:
                    metric_value_str = None
                
                conn.execute(insert_query, {
                    'run_id': result.run_id,
                    'dataset_name': result.dataset_name,
                    'schema_name': result.schema_name,
                    'column_name': column_name,
                    'column_type': column_type,
                    'metric_name': metric_name,
                    'metric_value': metric_value_str,
                    'profiled_at': result.profiled_at
                })
    
    def get_latest_run(self, dataset_name: str, schema_name: Optional[str] = None) -> Optional[str]:
        """
        Get the latest run_id for a dataset.
        
        Args:
            dataset_name: Name of the dataset
            schema_name: Optional schema name
            
        Returns:
            Run ID or None if not found
        """
        query = text(f"""
            SELECT run_id FROM {self.config.runs_table}
            WHERE dataset_name = :dataset_name
            {"AND schema_name = :schema_name" if schema_name else ""}
            ORDER BY profiled_at DESC
            LIMIT 1
        """)
        
        params = {'dataset_name': dataset_name}
        if schema_name:
            params['schema_name'] = schema_name
        
        with self.engine.connect() as conn:
            result = conn.execute(query, params).fetchone()
            return result[0] if result else None
    
    def close(self):
        """Close database connection."""
        if self.engine:
            self.engine.dispose()

