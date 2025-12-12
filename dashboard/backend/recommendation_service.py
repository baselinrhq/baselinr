"""
Service layer for recommendation operations.
"""

import os
import sys
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.engine import Engine

# Add parent directory to path to import baselinr
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

try:
    from baselinr.config.schema import ConnectionConfig, TablePattern, BaselinrConfig
    from baselinr.connectors.factory import create_connector
    from baselinr.smart_selection import RecommendationEngine, SmartSelectionConfig
    from baselinr.smart_selection.recommender import (
        RecommendationReport,
        TableRecommendation,
        ColumnCheckRecommendation,
        ExcludedTable,
        ColumnRecommendationEngine,
    )
    BASELINR_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Baselinr modules not available: {e}")
    BASELINR_AVAILABLE = False

from connection_service import ConnectionService
from config_service import ConfigService

logger = logging.getLogger(__name__)


class RecommendationService:
    """Service for recommendation operations."""
    
    def __init__(self, db_engine: Optional[Engine] = None):
        """
        Initialize recommendation service.
        
        Args:
            db_engine: Database engine for accessing connections and config
        """
        self.db_engine = db_engine
        self.connection_service = ConnectionService(db_engine)
        self.config_service = ConfigService(db_engine)
    
    def _get_connection_config(self, connection_id: str) -> ConnectionConfig:
        """
        Get connection config from saved connections.
        
        Args:
            connection_id: ID of the saved connection
            
        Returns:
            ConnectionConfig object
            
        Raises:
            ValueError: If connection not found
        """
        try:
            connection = self.connection_service.get_connection(connection_id)
            if not connection:
                raise ValueError(f"Connection {connection_id} not found")
            
            # Connection is already decrypted by get_connection
            conn_dict = connection.get('connection')
            if not conn_dict:
                raise ValueError(f"Connection {connection_id} has no connection data")
            
            # Convert to ConnectionConfig
            try:
                return ConnectionConfig(**conn_dict)
            except Exception as e:
                logger.error(f"Failed to create ConnectionConfig: {e}, conn_dict keys: {list(conn_dict.keys()) if isinstance(conn_dict, dict) else 'not a dict'}")
                raise ValueError(f"Invalid connection configuration: {e}")
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error getting connection config: {e}", exc_info=True)
            raise ValueError(f"Failed to get connection config: {e}")
    
    def _get_smart_selection_config(self) -> SmartSelectionConfig:
        """
        Get smart selection configuration from current config.
        
        Returns:
            SmartSelectionConfig object (with defaults if not found)
        """
        try:
            config = self.config_service.load_config()
            if config and 'smart_selection' in config:
                smart_config_dict = config['smart_selection']
                if isinstance(smart_config_dict, dict):
                    return SmartSelectionConfig(**smart_config_dict)
        except Exception as e:
            logger.warning(f"Could not load smart_selection config, using defaults: {e}")
        
        # Return defaults
        return SmartSelectionConfig(
            enabled=True,
            mode="recommend",
        )
    
    def _get_existing_tables(self) -> List[TablePattern]:
        """
        Get existing table patterns from current configuration.
        
        Returns:
            List of TablePattern objects
        """
        try:
            config = self.config_service.load_config()
            if config and 'tables' in config:
                tables_config = config['tables']
                if isinstance(tables_config, list):
                    return [TablePattern(**t) for t in tables_config if isinstance(t, dict)]
        except Exception as e:
            logger.warning(f"Could not load existing tables from config: {e}")
        
        return []
    
    def generate_recommendations(
        self,
        connection_id: str,
        schema: Optional[str] = None,
        include_columns: bool = False,
    ) -> RecommendationReport:
        """
        Generate recommendations for a connection.
        
        Args:
            connection_id: ID of the saved connection
            schema: Optional schema to limit recommendations to
            include_columns: Whether to include column-level recommendations
            
        Returns:
            RecommendationReport with recommendations
        """
        if not BASELINR_AVAILABLE:
            raise RuntimeError("Baselinr modules not available")
        
        try:
            # Get connection config
            logger.info(f"Getting connection config for {connection_id}")
            connection_config = self._get_connection_config(connection_id)
            
            # Get smart selection config
            logger.info("Getting smart selection config")
            smart_config = self._get_smart_selection_config()
            
            # Get existing tables
            logger.info("Getting existing tables")
            existing_tables = self._get_existing_tables()
            
            # Create connector and get engine
            logger.info(f"Creating connector for {connection_config.type}")
            connector = create_connector(connection_config)
            engine = connector.engine
            
            # Get storage engine if available (for column recommendations with profiling data)
            storage_engine = None
            try:
                config = self.config_service.load_config()
                if config and 'storage' in config:
                    storage_config = config['storage']
                    if isinstance(storage_config, dict) and 'connection' in storage_config:
                        storage_conn_config = ConnectionConfig(**storage_config['connection'])
                        storage_connector = create_connector(storage_conn_config)
                        storage_engine = storage_connector.engine
            except Exception as e:
                logger.warning(f"Could not create storage engine for profiling data: {e}")
            
            # Create recommendation engine
            logger.info("Creating recommendation engine")
            recommendation_engine = RecommendationEngine(
                connection_config=connection_config,
                smart_config=smart_config,
                storage_engine=storage_engine,
            )
            
            # Generate recommendations
            logger.info(f"Generating recommendations (schema={schema}, include_columns={include_columns})")
            report = recommendation_engine.generate_recommendations(
                engine=engine,
                schema=schema,
                existing_tables=existing_tables if smart_config.auto_apply.skip_existing else None,
                include_columns=include_columns,
            )
            
            logger.info(f"Generated {len(report.recommended_tables)} recommendations")
            return report
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}", exc_info=True)
            raise
    
    def get_column_recommendations(
        self,
        connection_id: str,
        table: str,
        schema: Optional[str] = None,
        use_profiling_data: bool = True,
    ) -> List[ColumnCheckRecommendation]:
        """
        Get column-level recommendations for a specific table.
        
        Args:
            connection_id: ID of the saved connection
            table: Table name
            schema: Optional schema name
            use_profiling_data: Whether to use profiling data if available
            
        Returns:
            List of column recommendations
        """
        if not BASELINR_AVAILABLE:
            raise RuntimeError("Baselinr modules not available")
        
        # Get connection config
        connection_config = self._get_connection_config(connection_id)
        
        # Get smart selection config
        smart_config = self._get_smart_selection_config()
        
        # Create connector and get engine
        connector = create_connector(connection_config)
        engine = connector.engine
        
        # Get storage engine if available
        storage_engine = None
        if use_profiling_data:
            try:
                config = self.config_service.load_config()
                if config and 'storage' in config:
                    storage_config = config['storage']
                    if isinstance(storage_config, dict) and 'connection' in storage_config:
                        storage_conn_config = ConnectionConfig(**storage_config['connection'])
                        storage_connector = create_connector(storage_conn_config)
                        storage_engine = storage_connector.engine
            except Exception as e:
                logger.warning(f"Could not create storage engine: {e}")
        
        # Create column recommendation engine
        column_engine = ColumnRecommendationEngine(
            source_engine=engine,
            storage_engine=storage_engine,
            smart_config=smart_config,
            database_type=connection_config.type,
        )
        
        # Generate column recommendations
        recommendations = column_engine.generate_column_recommendations(
            table_name=table,
            schema=schema,
            use_profiling_data=use_profiling_data,
        )
        
        return recommendations
    
    def apply_recommendations(
        self,
        connection_id: str,
        selected_tables: List[Dict[str, str]],
        column_checks: Optional[Dict[str, List[str]]] = None,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Apply recommendations to configuration.
        
        Args:
            connection_id: ID of the saved connection
            selected_tables: List of selected tables with schema/table
            column_checks: Optional map of table.column to selected check types
            comment: Optional comment for the configuration change
            
        Returns:
            Dictionary with applied tables and counts
        """
        if not BASELINR_AVAILABLE:
            raise RuntimeError("Baselinr modules not available")
        
        # Load current config
        config = self.config_service.load_config()
        if not config:
            raise ValueError("No configuration found")
        
        # Get existing tables
        existing_tables = config.get('tables', [])
        if not isinstance(existing_tables, list):
            existing_tables = []
        
        # Convert selected tables to TablePattern format
        applied_tables = []
        total_column_checks = 0
        
        for table_info in selected_tables:
            schema = table_info.get('schema', '')
            table = table_info.get('table')
            database = table_info.get('database')
            
            if not table:
                continue
            
            # Create table pattern
            table_pattern: Dict[str, Any] = {
                'table': table,
            }
            if schema:
                table_pattern['schema'] = schema
            if database:
                table_pattern['database'] = database
            
            # Add column checks if provided
            table_key = f"{schema}.{table}" if schema else table
            if column_checks and table_key in column_checks:
                checks = column_checks[table_key]
                if checks:
                    table_pattern['columns'] = {}
                    for check_info in checks:
                        # Parse check info (format: "column:check_type")
                        if ':' in check_info:
                            col_name, check_type = check_info.split(':', 1)
                            if col_name not in table_pattern['columns']:
                                table_pattern['columns'][col_name] = []
                            table_pattern['columns'][col_name].append(check_type)
                            total_column_checks += 1
            
            # Check if table already exists
            table_exists = False
            for existing in existing_tables:
                if isinstance(existing, dict):
                    if (existing.get('table') == table and 
                        existing.get('schema') == schema and
                        existing.get('database') == database):
                        table_exists = True
                        # Merge column checks if provided
                        if column_checks and table_key in column_checks:
                            if 'columns' not in existing:
                                existing['columns'] = {}
                            for check_info in column_checks[table_key]:
                                if ':' in check_info:
                                    col_name, check_type = check_info.split(':', 1)
                                    if col_name not in existing['columns']:
                                        existing['columns'][col_name] = []
                                    if check_type not in existing['columns'][col_name]:
                                        existing['columns'][col_name].append(check_type)
                                        total_column_checks += 1
                        break
            
            if not table_exists:
                existing_tables.append(table_pattern)
            
            applied_tables.append({
                'schema': schema,
                'table': table,
                'database': database,
                'column_checks_applied': len(column_checks.get(table_key, [])) if column_checks else 0,
            })
        
        # Update config
        config['tables'] = existing_tables
        
        # Save config
        self.config_service.save_config(config, comment=comment or "Applied recommendations from UI")
        
        return {
            'success': True,
            'applied_tables': applied_tables,
            'total_tables_applied': len(applied_tables),
            'total_column_checks_applied': total_column_checks,
            'message': f"Successfully applied {len(applied_tables)} table(s) and {total_column_checks} column check(s)",
        }

