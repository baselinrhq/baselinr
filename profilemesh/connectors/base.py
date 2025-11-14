"""
Base connector interface for ProfileMesh.

Defines the abstract interface that all database connectors must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, MetaData, Table, inspect
from sqlalchemy.engine import Engine
import logging

from ..config.schema import ConnectionConfig

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """Abstract base class for database connectors."""
    
    def __init__(self, config: ConnectionConfig):
        """
        Initialize connector with configuration.
        
        Args:
            config: Connection configuration
        """
        self.config = config
        self._engine: Optional[Engine] = None
        self._metadata: Optional[MetaData] = None
    
    @property
    def engine(self) -> Engine:
        """Get or create SQLAlchemy engine."""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine
    
    @property
    def metadata(self) -> MetaData:
        """Get or create SQLAlchemy metadata."""
        if self._metadata is None:
            self._metadata = MetaData()
            self._metadata.reflect(bind=self.engine)
        return self._metadata
    
    @abstractmethod
    def _create_engine(self) -> Engine:
        """
        Create SQLAlchemy engine for this connector type.
        
        Returns:
            Configured SQLAlchemy engine
        """
        pass
    
    @abstractmethod
    def get_connection_string(self) -> str:
        """
        Build database connection string.
        
        Returns:
            SQLAlchemy-compatible connection string
        """
        pass
    
    def list_schemas(self) -> List[str]:
        """
        List all available schemas in the database.
        
        Returns:
            List of schema names
        """
        inspector = inspect(self.engine)
        return inspector.get_schema_names()
    
    def list_tables(self, schema: Optional[str] = None) -> List[str]:
        """
        List all tables in a schema.
        
        Args:
            schema: Schema name (None for default)
            
        Returns:
            List of table names
        """
        inspector = inspect(self.engine)
        return inspector.get_table_names(schema=schema)
    
    def get_table(self, table_name: str, schema: Optional[str] = None) -> Table:
        """
        Get SQLAlchemy Table object with reflected metadata.
        
        Args:
            table_name: Name of the table
            schema: Schema name (None for default)
            
        Returns:
            SQLAlchemy Table object
        """
        return Table(
            table_name,
            MetaData(),
            autoload_with=self.engine,
            schema=schema
        )
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results.
        
        Args:
            query: SQL query string
            
        Returns:
            List of result rows as dictionaries
        """
        import time
        from ..logging import log_event, get_logger
        
        # Get logger - use existing logger or create one
        try:
            query_logger = get_logger(__name__)
        except:
            query_logger = logger
        
        # Truncate query for logging if too long
        query_preview = query[:200] + "..." if len(query) > 200 else query
        
        start_time = time.time()
        log_event(
            query_logger, "query_started", 
            f"Executing query: {query_preview}",
            metadata={"query_length": len(query)}
        )
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query)
                rows = [dict(row) for row in result]
                duration = time.time() - start_time
                
                # Record metrics: query completed
                try:
                    from ..metrics import is_metrics_enabled, record_query_completed, get_warehouse_type
                    if is_metrics_enabled():
                        warehouse = get_warehouse_type(self.config)
                        record_query_completed(warehouse, duration)
                except:
                    pass  # Metrics optional
                
                log_event(
                    query_logger, "query_completed",
                    f"Query completed: {len(rows)} rows in {duration:.2f}s",
                    metadata={
                        "row_count": len(rows),
                        "duration_seconds": duration,
                        "query_preview": query_preview
                    }
                )
                
                return rows
        except Exception as e:
            duration = time.time() - start_time
            
            # Record metrics: error
            try:
                from ..metrics import is_metrics_enabled, record_error, get_warehouse_type
                if is_metrics_enabled():
                    warehouse = get_warehouse_type(self.config)
                    record_error(warehouse, type(e).__name__, "connector")
            except:
                pass  # Metrics optional
            
            log_event(
                query_logger, "query_failed",
                f"Query failed after {duration:.2f}s: {e}",
                level="error",
                metadata={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_seconds": duration,
                    "query_preview": query_preview
                }
            )
            raise
    
    def close(self):
        """Close database connection."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self._metadata = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

