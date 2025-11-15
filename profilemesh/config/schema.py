"""
Configuration schema definitions using Pydantic.

Defines the structure for ProfileMesh configuration including
warehouse connections, profiling targets, and output settings.
"""

import os
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class DatabaseType(str, Enum):
    """Supported database types."""
    POSTGRES = "postgres"
    SNOWFLAKE = "snowflake"
    SQLITE = "sqlite"
    MYSQL = "mysql"
    BIGQUERY = "bigquery"
    REDSHIFT = "redshift"


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
    
    # BigQuery-specific (use extra_params for credentials_path)
    # Example: extra_params: {"credentials_path": "/path/to/key.json"}
    
    # Additional connection parameters
    # For BigQuery: use credentials_path in extra_params
    # For MySQL: standard host/port/database/username/password
    # For Redshift: standard host/port/database/username/password (uses port 5439 by default)
    extra_params: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = {
        "populate_by_name": True,
        "use_enum_values": True
    }


class PartitionConfig(BaseModel):
    """Partition-aware profiling configuration."""
    
    key: Optional[str] = None  # Partition column name
    strategy: str = Field("all")  # latest | recent_n | sample | all | specific_values
    recent_n: Optional[int] = Field(None, gt=0)  # For recent_n.strategy
    values: Optional[List[Any]] = None  # Explicit list of partition values (specific_values)
    metadata_fallback: bool = Field(True)  # Try to infer partition key from metadata
    
    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        """Validate partition strategy."""
        valid_strategies = ["latest", "recent_n", "sample", "all", "specific_values"]
        if v not in valid_strategies:
            raise ValueError(f"Strategy must be one of {valid_strategies}")
        return v
    
    @field_validator("recent_n")
    @classmethod
    def validate_recent_n(cls, v: Optional[int], info) -> Optional[int]:
        """Validate recent_n is provided when strategy is recent_n."""
        strategy = info.data.get('strategy')
        if strategy == 'recent_n' and v is None:
            raise ValueError("recent_n must be specified when strategy is 'recent_n'")
        return v
    
    @field_validator("values")
    @classmethod
    def validate_values(cls, v: Optional[List[Any]], info) -> Optional[List[Any]]:
        """Ensure values are provided when using specific_values strategy."""
        strategy = info.data.get('strategy')
        if strategy == 'specific_values' and (not v or len(v) == 0):
            raise ValueError("values must be provided when strategy is 'specific_values'")
        return v


class SamplingConfig(BaseModel):
    """Sampling configuration for profiling."""
    
    enabled: bool = Field(False)
    method: str = Field("random")  # random | stratified | topk
    fraction: float = Field(0.01, gt=0.0, le=1.0)  # Fraction of rows to sample
    max_rows: Optional[int] = Field(None, gt=0)  # Cap on sampled rows
    
    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate sampling method."""
        valid_methods = ["random", "stratified", "topk"]
        if v not in valid_methods:
            raise ValueError(f"Method must be one of {valid_methods}")
        return v


class TablePattern(BaseModel):
    """Table selection pattern."""
    
    schema_: Optional[str] = Field(None, alias="schema")
    table: str
    partition: Optional[PartitionConfig] = None
    sampling: Optional[SamplingConfig] = None
    
    model_config = {
        "populate_by_name": True
    }


class ProfilingConfig(BaseModel):
    """Profiling behavior configuration."""
    
    tables: List[TablePattern] = Field(default_factory=list)
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
    default_sample_ratio: float = Field(1.0, gt=0.0, le=1.0)


class StorageConfig(BaseModel):
    """Results storage configuration."""
    
    connection: ConnectionConfig
    results_table: str = Field("profilemesh_results")
    runs_table: str = Field("profilemesh_runs")
    create_tables: bool = Field(True)


class DriftDetectionConfig(BaseModel):
    """Drift detection configuration."""
    
    strategy: str = Field("absolute_threshold")
    
    # Absolute threshold strategy parameters
    absolute_threshold: Dict[str, float] = Field(
        default_factory=lambda: {
            "low_threshold": 5.0,
            "medium_threshold": 15.0,
            "high_threshold": 30.0
        }
    )
    
    # Standard deviation strategy parameters
    standard_deviation: Dict[str, float] = Field(
        default_factory=lambda: {
            "low_threshold": 1.0,
            "medium_threshold": 2.0,
            "high_threshold": 3.0
        }
    )
    
    # ML-based strategy parameters (placeholder)
    ml_based: Dict[str, Any] = Field(default_factory=dict)


class HookConfig(BaseModel):
    """Configuration for a single alert hook."""
    
    type: str  # logging | sql | snowflake | custom
    enabled: bool = Field(True)
    
    # Logging hook parameters
    log_level: Optional[str] = Field("INFO")
    
    # SQL/Snowflake hook parameters
    connection: Optional[ConnectionConfig] = None
    table_name: Optional[str] = Field("profilemesh_events")
    
    # Custom hook parameters (module path and class name)
    module: Optional[str] = None
    class_name: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate hook type."""
        valid_types = ["logging", "sql", "snowflake", "custom"]
        if v not in valid_types:
            raise ValueError(f"Hook type must be one of {valid_types}")
        return v


class HooksConfig(BaseModel):
    """Event hooks configuration."""
    
    enabled: bool = Field(True)  # Master switch for all hooks
    hooks: List[HookConfig] = Field(default_factory=list)


class RetryConfig(BaseModel):
    """Retry and recovery configuration."""
    
    enabled: bool = Field(True)  # Enable retry logic
    retries: int = Field(3, ge=0, le=10)  # Maximum retry attempts
    backoff_strategy: str = Field("exponential")  # exponential | fixed
    min_backoff: float = Field(0.5, gt=0.0, le=60.0)  # Minimum backoff in seconds
    max_backoff: float = Field(8.0, gt=0.0, le=300.0)  # Maximum backoff in seconds
    
    @field_validator("backoff_strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        """Validate backoff strategy."""
        valid_strategies = ["exponential", "fixed"]
        if v not in valid_strategies:
            raise ValueError(f"Backoff strategy must be one of {valid_strategies}")
        return v
    
    @field_validator("max_backoff")
    @classmethod
    def validate_max_backoff(cls, v: float, info) -> float:
        """Validate max_backoff is greater than min_backoff."""
        min_backoff = info.data.get('min_backoff')
        if min_backoff and v < min_backoff:
            raise ValueError("max_backoff must be greater than or equal to min_backoff")
        return v


class MonitoringConfig(BaseModel):
    """Monitoring and metrics configuration."""
    
    enable_metrics: bool = Field(False)  # Enable Prometheus metrics
    port: int = Field(9753, gt=0, le=65535)  # Metrics server port
    keep_alive: bool = Field(True)  # Keep server running after profiling completes
    
    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port is in valid range."""
        if not (1 <= v <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v


class ExecutionConfig(BaseModel):
    """Execution and parallelism configuration.
    
    This configuration is OPTIONAL and defaults to sequential execution
    (max_workers=1) for backward compatibility. Enable parallelism by
    setting max_workers > 1.
    
    Note: Dagster users already benefit from asset-level parallelism.
    This feature is primarily useful for CLI execution or when batching
    multiple tables within a single Dagster asset.
    """
    
    # CRITICAL: Default to 1 (sequential) for backward compatibility
    max_workers: int = Field(1, ge=1, le=64)
    batch_size: int = Field(10, ge=1, le=100)
    queue_size: int = Field(100, ge=10, le=1000)  # Bounded queue size
    
    # Warehouse-specific overrides (optional)
    warehouse_limits: Dict[str, int] = Field(default_factory=dict)
    # Example: {"snowflake": 20, "postgres": 8, "sqlite": 1}
    
    @field_validator("max_workers")
    @classmethod
    def validate_max_workers(cls, v: int) -> int:
        """Ensure max_workers is reasonable."""
        if v > 1:
            cpu_count = os.cpu_count() or 4
            max_allowed = cpu_count * 4
            if v > max_allowed:
                raise ValueError(f"max_workers ({v}) should not exceed {max_allowed} (4x CPU count)")
        return v


class ChangeDetectionConfig(BaseModel):
    """Configuration for change detection and metadata caching."""
    
    enabled: bool = Field(True)
    metadata_table: str = Field("profilemesh_table_state")
    connector_overrides: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    snapshot_ttl_minutes: int = Field(1440, ge=1)


class PartialProfilingConfig(BaseModel):
    """Configuration for partial profiling decisions."""
    
    enabled: bool = Field(True)
    allow_partition_pruning: bool = Field(True)
    max_partitions_per_run: int = Field(64, ge=1, le=10000)
    mergeable_metrics: List[str] = Field(
        default_factory=lambda: [
            "count",
            "null_count",
            "null_percent",
            "min",
            "max",
            "mean",
            "stddev"
        ]
    )


class AdaptiveSchedulingConfig(BaseModel):
    """Adaptive scheduling / staleness scoring configuration."""
    
    enabled: bool = Field(True)
    default_interval_minutes: int = Field(1440, ge=5)
    min_interval_minutes: int = Field(60, ge=5)
    max_interval_minutes: int = Field(10080, ge=60)  # 7 days
    priority_overrides: Dict[str, int] = Field(default_factory=dict)  # table_name -> minutes
    staleness_penalty_minutes: int = Field(1440, ge=5)


class CostControlConfig(BaseModel):
    """Cost guardrails for incremental profiling."""
    
    enabled: bool = Field(True)
    max_bytes_scanned: Optional[int] = Field(None, ge=1)
    max_rows_scanned: Optional[int] = Field(None, ge=1)
    fallback_strategy: str = Field("sample")  # sample | defer | full
    sample_fraction: float = Field(0.1, gt=0.0, le=1.0)

    @field_validator("fallback_strategy")
    @classmethod
    def validate_fallback(cls, v: str) -> str:
        valid = ["sample", "defer", "full"]
        if v not in valid:
            raise ValueError(f"fallback_strategy must be one of {valid}")
        return v


class IncrementalConfig(BaseModel):
    """Top-level incremental profiling configuration."""
    
    enabled: bool = Field(False)
    change_detection: ChangeDetectionConfig = Field(default_factory=ChangeDetectionConfig)
    partial_profiling: PartialProfilingConfig = Field(default_factory=PartialProfilingConfig)
    adaptive_scheduling: AdaptiveSchedulingConfig = Field(default_factory=AdaptiveSchedulingConfig)
    cost_controls: CostControlConfig = Field(default_factory=CostControlConfig)


class ProfileMeshConfig(BaseModel):
    """Main ProfileMesh configuration."""
    
    environment: str = Field("development")
    source: ConnectionConfig
    storage: StorageConfig
    profiling: ProfilingConfig = Field(default_factory=ProfilingConfig)
    drift_detection: DriftDetectionConfig = Field(default_factory=DriftDetectionConfig)
    hooks: HooksConfig = Field(default_factory=HooksConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    incremental: IncrementalConfig = Field(default_factory=IncrementalConfig)
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment name."""
        valid_envs = ["development", "test", "production"]
        if v not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        return v

