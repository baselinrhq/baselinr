"""
Configuration schema definitions using Pydantic.

Defines the structure for ProfileMesh configuration including
warehouse connections, profiling targets, and output settings.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class DatabaseType(str, Enum):
    """Supported database types."""
    POSTGRES = "postgres"
    SNOWFLAKE = "snowflake"
    SQLITE = "sqlite"


class ConnectionConfig(BaseModel):
    """Database connection configuration."""
    
    type: DatabaseType
    host: Optional[str] = None
    port: Optional[int] = None
    database: str
    username: Optional[str] = None
    password: Optional[str] = None
    schema_: Optional[str] = Field(None, alias="schema")
    
    # Snowflake-specific
    account: Optional[str] = None
    warehouse: Optional[str] = None
    role: Optional[str] = None
    
    # SQLite-specific
    filepath: Optional[str] = None
    
    # Additional connection parameters
    extra_params: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = {
        "populate_by_name": True,
        "use_enum_values": True
    }


class TablePattern(BaseModel):
    """Table selection pattern."""
    
    schema_: Optional[str] = Field(None, alias="schema")
    table: str
    sample_size: Optional[int] = None
    sample_ratio: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    model_config = {
        "populate_by_name": True
    }


class ProfilingConfig(BaseModel):
    """Profiling behavior configuration."""
    
    tables: List[TablePattern] = Field(default_factory=list)
    default_sample_ratio: float = Field(1.0, ge=0.0, le=1.0)
    max_distinct_values: int = Field(1000)
    compute_histograms: bool = Field(True)
    histogram_bins: int = Field(10)
    metrics: List[str] = Field(
        default_factory=lambda: [
            "count",
            "null_count",
            "null_percent",
            "distinct_count",
            "distinct_percent",
            "min",
            "max",
            "mean",
            "stddev",
            "histogram"
        ]
    )


class StorageConfig(BaseModel):
    """Results storage configuration."""
    
    connection: ConnectionConfig
    results_table: str = Field("profilemesh_results")
    runs_table: str = Field("profilemesh_runs")
    create_tables: bool = Field(True)


class ProfileMeshConfig(BaseModel):
    """Main ProfileMesh configuration."""
    
    environment: str = Field("development")
    source: ConnectionConfig
    storage: StorageConfig
    profiling: ProfilingConfig = Field(default_factory=ProfilingConfig)
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment name."""
        valid_envs = ["development", "test", "production"]
        if v not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        return v

