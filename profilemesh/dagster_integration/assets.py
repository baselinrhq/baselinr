"""
Dagster asset factory for ProfileMesh.

Dynamically creates Dagster assets from ProfileMesh configuration
for orchestration and scheduling.
"""

from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

try:
    from dagster import (
        asset,
        AssetExecutionContext,
        ConfigurableResource,
        AssetMaterialization,
        MetadataValue,
        Output,
        Definitions,
        define_asset_job,
    )
    DAGSTER_AVAILABLE = True
except ImportError:
    DAGSTER_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Dagster not available. Install dagster to use orchestration features.")

from ..config.loader import ConfigLoader
from ..config.schema import ProfileMeshConfig, TablePattern
from ..profiling.core import ProfileEngine, ProfilingResult
from ..storage.writer import ResultWriter
from .events import emit_profiling_event

logger = logging.getLogger(__name__)


if DAGSTER_AVAILABLE:
    class ProfileMeshResource(ConfigurableResource):
        """Dagster resource for ProfileMesh configuration."""
        
        config_path: str
        
        def get_config(self) -> ProfileMeshConfig:
            """Load and return ProfileMesh configuration."""
            return ConfigLoader.load_from_file(self.config_path)
    
    
    def create_profiling_assets(
        config_path: str,
        asset_name_prefix: str = "profilemesh"
    ) -> List:
        """
        Create Dagster assets from ProfileMesh configuration.
        
        This factory function reads the ProfileMesh configuration and
        creates a Dagster asset for each table pattern defined.
        
        Args:
            config_path: Path to ProfileMesh configuration file
            asset_name_prefix: Prefix for asset names
            
        Returns:
            List of Dagster asset definitions
            
        Example:
            ```python
            from profilemesh.dagster_integration import create_profiling_assets
            
            assets = create_profiling_assets("config.yml")
            ```
        """
        # Load configuration to get table patterns
        config = ConfigLoader.load_from_file(config_path)
        
        assets = []
        
        # Create an asset for each table pattern
        for table_pattern in config.profiling.tables:
            asset_def = _create_table_asset(
                config_path=config_path,
                table_pattern=table_pattern,
                asset_name_prefix=asset_name_prefix
            )
            assets.append(asset_def)
        
        # Create summary asset that depends on all table assets
        summary_asset = _create_summary_asset(
            config_path=config_path,
            asset_name_prefix=asset_name_prefix,
            table_patterns=config.profiling.tables
        )
        assets.append(summary_asset)
        
        logger.info(f"Created {len(assets)} Dagster assets for ProfileMesh")
        return assets
    
    
    def _create_table_asset(
        config_path: str,
        table_pattern: TablePattern,
        asset_name_prefix: str
    ):
        """Create a Dagster asset for a single table."""
        
        # Create safe asset name
        table_name = table_pattern.table.replace(".", "_").replace("-", "_")
        asset_name = f"{asset_name_prefix}_{table_name}"
        
        @asset(
            name=asset_name,
            group_name="profilemesh_profiling",
            description=f"Profile table: {table_pattern.table}"
        )
        def table_profiling_asset(context: AssetExecutionContext) -> Output:
            """Profile a single table."""
            
            # Emit start event
            emit_profiling_event(
                context,
                "profiling_started",
                dataset_name=table_pattern.table
            )
            
            try:
                # Load config
                config = ConfigLoader.load_from_file(config_path)
                
                # Create profiling engine
                engine = ProfileEngine(config)
                
                # Profile just this table
                results = engine.profile(table_patterns=[table_pattern])
                
                if not results:
                    raise ValueError(f"No results generated for {table_pattern.table}")
                
                result = results[0]
                
                # Write to storage
                writer = ResultWriter(config.storage)
                writer.write_results([result], environment=config.environment)
                writer.close()
                
                # Emit completion event
                emit_profiling_event(
                    context,
                    "profiling_completed",
                    dataset_name=table_pattern.table,
                    run_id=result.run_id,
                    column_count=len(result.columns),
                    row_count=result.metadata.get('row_count')
                )
                
                # Return output with metadata
                return Output(
                    value={
                        'run_id': result.run_id,
                        'dataset_name': result.dataset_name,
                        'column_count': len(result.columns),
                        'row_count': result.metadata.get('row_count')
                    },
                    metadata={
                        'run_id': MetadataValue.text(result.run_id),
                        'dataset_name': MetadataValue.text(result.dataset_name),
                        'columns_profiled': MetadataValue.int(len(result.columns)),
                        'row_count': MetadataValue.int(result.metadata.get('row_count', 0)),
                        'profiled_at': MetadataValue.text(result.profiled_at.isoformat()),
                    }
                )
            
            except Exception as e:
                # Emit failure event
                emit_profiling_event(
                    context,
                    "profiling_failed",
                    dataset_name=table_pattern.table,
                    error=str(e)
                )
                raise
        
        return table_profiling_asset
    
    
    def _create_summary_asset(
        config_path: str,
        asset_name_prefix: str,
        table_patterns: List[TablePattern]
    ):
        """Create a summary asset that aggregates all profiling results."""
        
        @asset(
            name=f"{asset_name_prefix}_summary",
            group_name="profilemesh_profiling",
            description="Summary of all ProfileMesh profiling runs"
        )
        def profiling_summary_asset(context: AssetExecutionContext) -> Output:
            """Generate summary of profiling run."""
            
            config = ConfigLoader.load_from_file(config_path)
            
            summary = {
                'environment': config.environment,
                'tables_profiled': len(table_patterns),
                'tables': [p.table for p in table_patterns]
            }
            
            return Output(
                value=summary,
                metadata={
                    'environment': MetadataValue.text(config.environment),
                    'tables_profiled': MetadataValue.int(len(table_patterns)),
                    'table_list': MetadataValue.md(
                        "\n".join([f"- {p.table}" for p in table_patterns])
                    )
                }
            )
        
        return profiling_summary_asset
    
    
    def create_profiling_job(
        assets: List,
        job_name: str = "profilemesh_profile_all"
    ):
        """
        Create a Dagster job that runs all profiling assets.
        
        Args:
            assets: List of Dagster assets
            job_name: Name for the job
            
        Returns:
            Dagster job definition
        """
        return define_asset_job(
            name=job_name,
            selection=assets,
            description="Run all ProfileMesh profiling tasks"
        )


else:
    # Stub implementations when Dagster is not available
    class ProfileMeshResource:
        """Stub resource when Dagster not available."""
        pass
    
    def create_profiling_assets(*args, **kwargs):
        """Stub function when Dagster not available."""
        raise ImportError("Dagster is not installed. Install with: pip install dagster")
    
    def create_profiling_job(*args, **kwargs):
        """Stub function when Dagster not available."""
        raise ImportError("Dagster is not installed. Install with: pip install dagster")

