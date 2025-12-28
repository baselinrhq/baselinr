"""
Configuration schema definitions using Pydantic.

Defines the structure for Baselinr configuration including
warehouse connections, profiling targets, and output settings.
"""

import os
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


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

    model_config = {"populate_by_name": True, "use_enum_values": True}


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
        strategy = info.data.get("strategy")
        if strategy == "recent_n" and v is None:
            raise ValueError("recent_n must be specified when strategy is 'recent_n'")
        return v

    @field_validator("values")
    @classmethod
    def validate_values(cls, v: Optional[List[Any]], info) -> Optional[List[Any]]:
        """Ensure values are provided when using specific_values strategy."""
        strategy = info.data.get("strategy")
        if strategy == "specific_values" and (not v or len(v) == 0):
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


class ColumnDriftConfig(BaseModel):
    """Column-level drift detection configuration."""

    enabled: Optional[bool] = Field(
        None, description="Enable/disable drift detection for this column"
    )
    strategy: Optional[str] = Field(
        None,
        description=(
            "Override drift strategy " "(absolute_threshold, standard_deviation, statistical)"
        ),
    )
    thresholds: Optional[Dict[str, float]] = Field(
        None, description="Per-column thresholds (low, medium, high)"
    )
    baselines: Optional[Dict[str, Any]] = Field(
        None, description="Override baseline selection strategy and windows"
    )

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: Optional[str]) -> Optional[str]:
        """Validate drift strategy."""
        if v is not None:
            valid_strategies = ["absolute_threshold", "standard_deviation", "statistical"]
            if v not in valid_strategies:
                raise ValueError(f"Strategy must be one of {valid_strategies}")
        return v


class ColumnAnomalyConfig(BaseModel):
    """Column-level anomaly detection configuration."""

    enabled: Optional[bool] = Field(
        None, description="Enable/disable anomaly detection for this column"
    )
    methods: Optional[List[str]] = Field(
        None,
        description=(
            "List of enabled detection methods "
            "(control_limits, iqr, mad, ewma, seasonality, regime_shift)"
        ),
    )
    thresholds: Optional[Dict[str, float]] = Field(
        None,
        description=(
            "Per-column thresholds "
            "(iqr_threshold, mad_threshold, ewma_deviation_threshold, etc.)"
        ),
    )

    @field_validator("methods")
    @classmethod
    def validate_methods(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate anomaly detection methods."""
        if v is not None:
            valid_methods = [
                "control_limits",
                "iqr",
                "mad",
                "ewma",
                "seasonality",
                "regime_shift",
            ]
            invalid = [m for m in v if m not in valid_methods]
            if invalid:
                raise ValueError(f"Invalid methods: {invalid}. Must be one of {valid_methods}")
        return v


class ColumnProfilingConfig(BaseModel):
    """Column-level profiling configuration."""

    enabled: Optional[bool] = Field(
        None, description="Enable/disable profiling for this column (default: true)"
    )


class ColumnValidationConfig(BaseModel):
    """Column-level validation configuration."""

    rules: Optional[List["ValidationRuleConfig"]] = Field(
        None, description="Validation rules specific to this column"
    )


class ColumnConfig(BaseModel):
    """Column-level configuration for profiling, drift, validation, and anomaly detection.

    Supports both explicit column names and patterns (wildcards/regex).
    When patterns are used, multiple columns may match a single configuration.

    Column-level configurations are defined in ODCS contracts.
    """

    name: str = Field(..., description="Column name or pattern (supports wildcards: *, ?)")
    pattern_type: Optional[str] = Field(
        None, description="Pattern type: 'wildcard' (default) or 'regex'"
    )
    metrics: Optional[List[str]] = Field(
        None, description="List of metrics to compute (overrides table-level metrics)"
    )
    profiling: Optional[ColumnProfilingConfig] = Field(
        None, description="Profiling configuration for this column"
    )
    drift: Optional[ColumnDriftConfig] = Field(
        None, description="Drift detection configuration for this column"
    )
    validation: Optional[ColumnValidationConfig] = Field(
        None, description="Validation configuration for this column"
    )
    anomaly: Optional[ColumnAnomalyConfig] = Field(
        None, description="Anomaly detection configuration for this column"
    )

    @field_validator("pattern_type")
    @classmethod
    def validate_pattern_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate pattern type."""
        if v is not None and v not in ["wildcard", "regex"]:
            raise ValueError("pattern_type must be 'wildcard' or 'regex'")
        return v

    @field_validator("metrics")
    @classmethod
    def validate_metrics(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate metric names."""
        if v is not None:
            valid_metrics = [
                "count",
                "null_count",
                "null_ratio",
                "distinct_count",
                "unique_ratio",
                "approx_distinct_count",
                "min",
                "max",
                "mean",
                "stddev",
                "histogram",
                "data_type_inferred",
                "min_length",
                "max_length",
                "avg_length",
            ]
            invalid = [m for m in v if m not in valid_metrics]
            if invalid:
                raise ValueError(f"Invalid metrics: {invalid}. Must be one of {valid_metrics}")
        return v

    @model_validator(mode="after")
    def validate_dependencies(self):
        """Validate dependencies between profiling, drift, and anomaly detection.

        Drift and anomaly detection require profiling to be enabled.
        """
        # Default to enabled if profiling config not specified
        profiling_enabled = True
        if self.profiling and self.profiling.enabled is not None:
            profiling_enabled = self.profiling.enabled

        # If profiling is disabled, drift and anomaly should not be configured
        if not profiling_enabled:
            if self.drift and self.drift.enabled is not False:
                import warnings

                warnings.warn(
                    f"Column '{self.name}': Drift detection configured but "
                    "profiling is disabled. Drift detection requires profiling. "
                    "Consider removing drift config or enabling profiling.",
                    UserWarning,
                )
            if self.anomaly and self.anomaly.enabled is not False:
                import warnings

                warnings.warn(
                    f"Column '{self.name}': Anomaly detection configured but "
                    "profiling is disabled. Anomaly detection requires profiling. "
                    "Consider removing anomaly config or enabling profiling.",
                    UserWarning,
                )

        return self


class TablePattern(BaseModel):
    """Table selection pattern.

    Supports multiple selection methods:
    - Explicit table name (table field)
    - Pattern-based (wildcard/regex via pattern field)
    - Schema-based (select_schema field)
    - Database-level (select_all_schemas field)
    - Tag-based (tags/tags_any fields)

    All methods can be combined with additional filters.

    When database is specified, the pattern operates on that database.
    When omitted, uses config.source.database (backward compatible).
    """

    database: Optional[str] = Field(
        None, description="Database name (optional, defaults to source.database)"
    )
    schema_: Optional[str] = Field(None, alias="schema")
    table: Optional[str] = Field(
        None, description="Explicit table name (required if pattern not used)"
    )

    # Pattern-based selection
    pattern: Optional[str] = Field(
        None, description="Wildcard (*, ?) or regex pattern for table name matching"
    )
    pattern_type: Optional[str] = Field(
        None, description="Pattern type: 'wildcard' or 'regex' (default: wildcard)"
    )
    schema_pattern: Optional[str] = Field(
        None, description="Wildcard/regex pattern for schema names"
    )

    # Schema/database-level selection
    select_all_schemas: Optional[bool] = Field(
        None, description="If True, profile all schemas in database"
    )
    select_schema: Optional[bool] = Field(
        None, description="If True, profile all tables in specified schema(s)"
    )

    # Tag-based selection
    tags: Optional[List[str]] = Field(None, description="Tags that tables must have (AND logic)")
    tags_any: Optional[List[str]] = Field(None, description="Tags where any match (OR logic)")

    # dbt-based selection
    dbt_ref: Optional[str] = Field(
        None, description="dbt model reference (e.g., 'customers' or 'package.model')"
    )
    dbt_selector: Optional[str] = Field(
        None,
        description=(
            "dbt selector expression (e.g., 'tag:critical', " "'config.materialized:table')"
        ),
    )
    dbt_project_path: Optional[str] = Field(None, description="Path to dbt project root directory")
    dbt_manifest_path: Optional[str] = Field(
        None,
        description="Path to dbt manifest.json (auto-detected from project_path if not provided)",
    )

    # Filters
    exclude_patterns: Optional[List[str]] = Field(
        None, description="Patterns to exclude from matches"
    )
    table_types: Optional[List[str]] = Field(
        None, description="Filter by table type: 'table', 'view', 'materialized_view', etc."
    )
    min_rows: Optional[int] = Field(
        None, gt=0, description="Only profile tables with at least N rows"
    )
    max_rows: Optional[int] = Field(
        None, gt=0, description="Only profile tables with at most N rows"
    )
    required_columns: Optional[List[str]] = Field(
        None, description="Tables must have these columns"
    )
    modified_since_days: Optional[int] = Field(
        None, gt=0, description="Only profile tables modified in last N days"
    )

    # Precedence override
    override_priority: Optional[int] = Field(
        None,
        description=(
            "Higher priority overrides lower priority matches "
            "(default: explicit=100, patterns=10, schema=5, database=1)"
        ),
    )

    model_config = {"populate_by_name": True}

    @field_validator("pattern_type")
    @classmethod
    def validate_pattern_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate pattern type."""
        if v is not None and v not in ["wildcard", "regex"]:
            raise ValueError("pattern_type must be 'wildcard' or 'regex'")
        return v

    @model_validator(mode="before")
    @classmethod
    def reject_old_profiling_fields(cls, data: Any) -> Any:
        """Reject old profiling fields that should be in ODCS contracts."""
        if isinstance(data, dict):
            if "partition" in data or "sampling" in data or "columns" in data:
                raise ValueError(
                    "TablePattern no longer supports 'partition', 'sampling', or 'columns' fields. "
                    "These must be defined in ODCS contracts. "
                    "Use ODCS contracts instead your configuration."
                )
        return data

    @model_validator(mode="after")
    def validate_table_or_pattern(self):
        """Ensure either table or pattern/select fields are provided."""
        has_table = self.table is not None
        has_pattern = self.pattern is not None
        has_select_schema = self.select_schema is True
        has_select_all_schemas = self.select_all_schemas is True
        has_dbt_ref = self.dbt_ref is not None
        has_dbt_selector = self.dbt_selector is not None

        if not (
            has_table
            or has_pattern
            or has_select_schema
            or has_select_all_schemas
            or has_dbt_ref
            or has_dbt_selector
        ):
            raise ValueError(
                "TablePattern must specify either 'table', 'pattern', "
                "'select_schema', 'select_all_schemas', 'dbt_ref', or 'dbt_selector'"
            )

        # Ensure only one primary selection method is used
        selection_methods = [
            has_table,
            has_pattern,
            has_select_schema,
            has_select_all_schemas,
            has_dbt_ref,
            has_dbt_selector,
        ]
        if sum(selection_methods) > 1:
            raise ValueError(
                "TablePattern can only specify one primary selection method: "
                "'table', 'pattern', 'select_schema', 'select_all_schemas', "
                "'dbt_ref', or 'dbt_selector'"
            )

        return self


class DiscoveryOptionsConfig(BaseModel):
    """Configuration options for table discovery."""

    include_schemas: Optional[List[str]] = Field(None, description="Only discover in these schemas")
    exclude_schemas: Optional[List[str]] = Field(
        None, description="Exclude these schemas from discovery"
    )
    include_table_types: Optional[List[str]] = Field(
        None, description="Default table types to include"
    )
    exclude_table_types: Optional[List[str]] = Field(
        None, description="Default table types to exclude"
    )
    cache_discovery: bool = Field(True, description="Cache discovered tables for performance")
    cache_ttl_seconds: int = Field(300, gt=0, description="TTL for discovery cache in seconds")
    max_tables_per_pattern: int = Field(1000, gt=0, description="Max tables to match per pattern")
    max_schemas_per_database: int = Field(100, gt=0, description="Max schemas to scan per database")
    discovery_limit_action: str = Field(
        "warn", description="What to do when limit hit: 'warn', 'error', or 'skip'"
    )
    validate_regex: bool = Field(True, description="Validate regex patterns at config load time")
    tag_provider: Optional[str] = Field(
        None,
        description=(
            "Tag metadata provider: 'auto', 'snowflake', 'bigquery', "
            "'postgres', 'mysql', 'redshift', 'sqlite', 'dbt', or None"
        ),
    )
    dbt_manifest_path: Optional[str] = Field(
        None, description="Path to dbt manifest.json for dbt tag provider"
    )

    @field_validator("discovery_limit_action")
    @classmethod
    def validate_limit_action(cls, v: str) -> str:
        """Validate discovery limit action."""
        valid_actions = ["warn", "error", "skip"]
        if v not in valid_actions:
            raise ValueError(f"discovery_limit_action must be one of {valid_actions}")
        return v

    @field_validator("tag_provider")
    @classmethod
    def validate_tag_provider(cls, v: Optional[str]) -> Optional[str]:
        """Validate tag provider."""
        if v is not None:
            valid_providers = [
                "auto",
                "snowflake",
                "bigquery",
                "postgres",
                "mysql",
                "redshift",
                "sqlite",
                "dbt",
                "external",
            ]
            if v not in valid_providers:
                raise ValueError(f"tag_provider must be one of {valid_providers} or None")
        return v


class ProfilingConfig(BaseModel):
    """Profiling behavior configuration."""

    tables: List[TablePattern] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def reject_old_schema_database_fields(cls, data: Any) -> Any:
        """Reject old schemas/databases fields that should be in ODCS contracts."""
        if isinstance(data, dict):
            if "schemas" in data or "databases" in data:
                raise ValueError(
                    "ProfilingConfig no longer supports 'schemas' or 'databases' fields. "
                    "These must be defined in ODCS contracts. "
                    "Use ODCS contracts instead your configuration."
                )
        return data

    max_distinct_values: int = Field(1000)
    compute_histograms: bool = Field(True)
    histogram_bins: int = Field(10)
    metrics: List[str] = Field(
        default_factory=lambda: [
            "count",
            "null_count",
            "null_ratio",
            "distinct_count",
            "unique_ratio",
            "approx_distinct_count",
            "min",
            "max",
            "mean",
            "stddev",
            "histogram",
            "data_type_inferred",
        ]
    )
    default_sample_ratio: float = Field(1.0, gt=0.0, le=1.0)

    # Table discovery options
    table_discovery: bool = Field(
        True, description="Enable automatic table discovery (default: True when patterns used)"
    )
    discovery_options: DiscoveryOptionsConfig = Field(
        default_factory=lambda: DiscoveryOptionsConfig(),  # type: ignore[call-arg]
        description="Options for table discovery",
    )

    # Enrichment options
    enable_enrichment: bool = Field(True, description="Enable profiling enrichment features")
    enable_approx_distinct: bool = Field(True, description="Enable approximate distinct count")
    enable_schema_tracking: bool = Field(True, description="Enable schema change tracking")
    enable_type_inference: bool = Field(True, description="Enable data type inference")
    enable_column_stability: bool = Field(True, description="Enable column stability tracking")

    # Stability calculation config
    stability_window: int = Field(7, description="Number of runs to use for stability calculations")
    type_inference_sample_size: int = Field(1000, description="Sample size for type inference")

    # Lineage extraction
    extract_lineage: bool = Field(False, description="Enable lineage extraction during profiling")


class StorageConfig(BaseModel):
    """Results storage configuration."""

    connection: ConnectionConfig
    results_table: str = Field("baselinr_results")
    runs_table: str = Field("baselinr_runs")
    create_tables: bool = Field(True)

    # Expectation learning configuration
    enable_expectation_learning: bool = Field(
        False, description="Enable automatic learning of expected metric ranges"
    )
    learning_window_days: int = Field(
        30, description="Historical window in days for learning expectations"
    )
    min_samples: int = Field(
        5, description="Minimum number of historical runs required for learning"
    )
    ewma_lambda: float = Field(
        0.2, description="EWMA smoothing parameter (0 < lambda <= 1)", gt=0.0, le=1.0
    )

    # Anomaly detection configuration
    enable_anomaly_detection: bool = Field(
        False, description="Enable automatic anomaly detection using learned expectations"
    )
    anomaly_enabled_methods: List[str] = Field(
        default_factory=lambda: [
            "control_limits",
            "iqr",
            "mad",
            "ewma",
            "seasonality",
            "regime_shift",
        ],
        description="List of enabled anomaly detection methods",
    )
    anomaly_iqr_threshold: float = Field(
        1.5, description="IQR multiplier threshold for outlier detection", gt=0.0
    )
    anomaly_mad_threshold: float = Field(
        3.0, description="MAD threshold (modified z-score) for outlier detection", gt=0.0
    )
    anomaly_ewma_deviation_threshold: float = Field(
        2.0, description="EWMA deviation threshold (number of stddevs)", gt=0.0
    )
    anomaly_seasonality_enabled: bool = Field(
        True, description="Enable trend and seasonality detection"
    )
    anomaly_regime_shift_enabled: bool = Field(True, description="Enable regime shift detection")
    anomaly_regime_shift_window: int = Field(
        3, description="Number of recent runs for regime shift comparison", ge=2
    )
    anomaly_regime_shift_sensitivity: float = Field(
        0.05, description="P-value threshold for regime shift detection", gt=0.0, le=1.0
    )


class DriftDetectionConfig(BaseModel):
    """Drift detection configuration.

    This is the global/default drift detection configuration.
    Dataset-specific drift overrides must be defined in ODCS contracts.
    """

    strategy: str = Field("absolute_threshold")

    # Absolute threshold strategy parameters
    absolute_threshold: Dict[str, float] = Field(
        default_factory=lambda: {
            "low_threshold": 5.0,
            "medium_threshold": 15.0,
            "high_threshold": 30.0,
        }
    )

    # Standard deviation strategy parameters
    standard_deviation: Dict[str, float] = Field(
        default_factory=lambda: {
            "low_threshold": 1.0,
            "medium_threshold": 2.0,
            "high_threshold": 3.0,
        }
    )

    # ML-based strategy parameters (placeholder)
    ml_based: Dict[str, Any] = Field(default_factory=dict)

    # Statistical test strategy parameters
    statistical: Dict[str, Any] = Field(
        default_factory=lambda: {
            "tests": ["ks_test", "psi", "chi_square"],
            "sensitivity": "medium",
            "test_params": {
                "ks_test": {"alpha": 0.05},
                "psi": {"buckets": 10, "threshold": 0.2},
                "z_score": {"z_threshold": 2.0},
                "chi_square": {"alpha": 0.05},
                "entropy": {"entropy_threshold": 0.1},
                "top_k": {"k": 10, "similarity_threshold": 0.7},
            },
        }
    )

    # Baseline auto-selection configuration
    baselines: Dict[str, Any] = Field(
        default_factory=lambda: {
            # auto | last_run | moving_average | prior_period | stable_window
            "strategy": "last_run",
            "windows": {
                "moving_average": 7,  # Number of runs for moving average
                "prior_period": 7,  # Days for prior period (7 = week, 30 = month)
                "min_runs": 3,  # Minimum runs required for auto-selection
            },
        }
    )

    @field_validator("baselines")
    @classmethod
    def validate_baselines(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate baseline configuration."""
        if isinstance(v, dict):
            valid_strategies = [
                "auto",
                "last_run",
                "moving_average",
                "prior_period",
                "stable_window",
            ]
            strategy = v.get("strategy", "last_run")
            if strategy not in valid_strategies:
                raise ValueError(
                    f"Baseline strategy must be one of {valid_strategies}, got: {strategy}"
                )

            # Ensure windows dict exists with defaults
            if "windows" not in v:
                v["windows"] = {}
            windows = v["windows"]

            # Set defaults for window parameters
            windows.setdefault("moving_average", 7)
            windows.setdefault("prior_period", 7)
            windows.setdefault("min_runs", 3)

            # Validate window parameters
            if windows["moving_average"] < 2:
                raise ValueError("moving_average window must be at least 2")
            if windows["prior_period"] not in [1, 7, 30]:
                raise ValueError("prior_period must be 1 (day), 7 (week), or 30 (month)")
            if windows["min_runs"] < 2:
                raise ValueError("min_runs must be at least 2")

        return v

    # Type-specific threshold configuration
    enable_type_specific_thresholds: bool = Field(True)

    type_specific_thresholds: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "numeric": {
                "mean": {"low": 10.0, "medium": 25.0, "high": 50.0},
                "stddev": {"low": 3.0, "medium": 8.0, "high": 15.0},
                "default": {"low": 5.0, "medium": 15.0, "high": 30.0},
            },
            "categorical": {
                "distinct_count": {"low": 2.0, "medium": 5.0, "high": 10.0},
                "unique_ratio": {"low": 0.02, "medium": 0.05, "high": 0.10},
                "default": {"low": 5.0, "medium": 15.0, "high": 30.0},
            },
            "timestamp": {
                "default": {"low": 5.0, "medium": 15.0, "high": 30.0},
            },
            "boolean": {
                "default": {"low": 2.0, "medium": 5.0, "high": 10.0},
            },
        }
    )


class HookConfig(BaseModel):
    """Configuration for a single alert hook."""

    type: str  # logging | sql | snowflake | slack | custom
    enabled: bool = Field(True)

    # Logging hook parameters
    log_level: Optional[str] = Field("INFO")

    # SQL/Snowflake hook parameters
    connection: Optional[ConnectionConfig] = None
    table_name: Optional[str] = Field("baselinr_events")

    # Slack hook parameters
    webhook_url: Optional[str] = None
    channel: Optional[str] = None
    username: Optional[str] = Field("Baselinr")
    min_severity: Optional[str] = Field("low")
    alert_on_drift: Optional[bool] = Field(True)
    alert_on_schema_change: Optional[bool] = Field(True)
    alert_on_profiling_failure: Optional[bool] = Field(True)
    timeout: Optional[int] = Field(10)

    # Custom hook parameters (module path and class name)
    module: Optional[str] = None
    class_name: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate hook type."""
        valid_types = ["logging", "sql", "snowflake", "slack", "custom"]
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
        min_backoff = info.data.get("min_backoff")
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
                raise ValueError(
                    f"max_workers ({v}) should not exceed {max_allowed} (4x CPU count)"
                )
        return v


class ChangeDetectionConfig(BaseModel):
    """Configuration for change detection and metadata caching."""

    enabled: bool = Field(True)
    metadata_table: str = Field("baselinr_table_state")
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
            "null_ratio",
            "min",
            "max",
            "mean",
            "stddev",
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
    change_detection: ChangeDetectionConfig = Field(
        default_factory=lambda: ChangeDetectionConfig()  # type: ignore[call-arg]
    )
    partial_profiling: PartialProfilingConfig = Field(
        default_factory=lambda: PartialProfilingConfig()  # type: ignore[call-arg]
    )
    adaptive_scheduling: AdaptiveSchedulingConfig = Field(
        default_factory=lambda: AdaptiveSchedulingConfig()  # type: ignore[call-arg]
    )
    cost_controls: CostControlConfig = Field(
        default_factory=lambda: CostControlConfig()  # type: ignore[call-arg]
    )


class SchemaChangeSuppressionRule(BaseModel):
    """Rule for suppressing schema change events."""

    table: Optional[str] = None  # Table name (None = all tables)
    schema_: Optional[str] = Field(None, alias="schema")  # Schema name (None = all schemas)
    change_type: Optional[str] = None  # Change type (None = all change types)

    model_config = {"populate_by_name": True}
    # Valid change types: column_added, column_removed, column_renamed,
    # type_changed, partition_changed

    @field_validator("change_type")
    @classmethod
    def validate_change_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate change type."""
        if v is not None:
            valid_types = [
                "column_added",
                "column_removed",
                "column_renamed",
                "type_changed",
                "partition_changed",
            ]
            if v not in valid_types:
                raise ValueError(f"change_type must be one of {valid_types}")
        return v


class SchemaChangeConfig(BaseModel):
    """Configuration for schema change detection."""

    enabled: bool = Field(True)
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0)  # For rename detection
    suppression: List[SchemaChangeSuppressionRule] = Field(default_factory=list)


class QueryHistoryConfig(BaseModel):
    """Configuration for query history lineage extraction."""

    enabled: bool = Field(True, description="Enable query history lineage")
    incremental: bool = Field(True, description="Enable incremental updates during profiling")
    lookback_days: int = Field(30, ge=1, le=365, description="Days of history for bulk sync")
    min_query_count: int = Field(1, ge=1, description="Minimum queries to establish relationship")
    exclude_patterns: Optional[List[str]] = Field(
        None, description="Regex patterns to exclude queries"
    )
    edge_expiration_days: Optional[int] = Field(
        None,
        ge=1,
        description=(
            "Days after which query history edges are considered stale and can be removed. "
            "None = never expire automatically"
        ),
    )
    warn_stale_days: int = Field(
        90,
        ge=1,
        description=(
            "Days after which to warn about stale edges when querying lineage (default: 90)"
        ),
    )
    # Warehouse-specific configs
    snowflake: Optional[Dict[str, Any]] = None
    bigquery: Optional[Dict[str, Any]] = None
    postgres: Optional[Dict[str, Any]] = None
    redshift: Optional[Dict[str, Any]] = None
    mysql: Optional[Dict[str, Any]] = None


class LineageConfig(BaseModel):
    """Configuration for data lineage extraction."""

    enabled: bool = Field(
        True, description="Enable lineage extraction (requires profiling.extract_lineage=true)"
    )
    extract_column_lineage: bool = Field(
        False, description="Enable column-level lineage extraction"
    )
    providers: Optional[List[str]] = Field(
        None,
        description=(
            "List of lineage providers to use (e.g., ['dbt', 'sql_parser']). "
            "If None, uses all available providers."
        ),
    )
    dbt: Optional[Dict[str, Any]] = Field(
        None,
        description="dbt-specific configuration (e.g., manifest_path)",
    )
    dagster: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Dagster-specific configuration " "(e.g., metadata_db_url, code_locations, graphql_url)"
        ),
    )
    query_history: Optional[QueryHistoryConfig] = Field(
        None,
        description="Query history lineage configuration",
    )


class ChatConfig(BaseModel):
    """Configuration for chat/conversational interface."""

    enabled: bool = Field(True, description="Enable chat interface")
    max_history_messages: int = Field(
        20, ge=1, le=100, description="Maximum messages to keep in context window"
    )
    max_iterations: int = Field(
        5, ge=1, le=20, description="Maximum tool-calling iterations per query"
    )
    tool_timeout: int = Field(30, gt=0, le=300, description="Tool execution timeout in seconds")
    cache_tool_results: bool = Field(True, description="Cache tool results within a session")
    enable_context_enhancement: bool = Field(
        True, description="Enhance tool results with additional context"
    )


class LLMConfig(BaseModel):
    """Configuration for LLM-powered human-readable explanations."""

    enabled: bool = Field(
        False, description="Enable LLM explanations (opt-in, disabled by default)"
    )
    provider: str = Field("openai", description="LLM provider: openai | anthropic | azure | ollama")
    api_key: Optional[str] = Field(
        None, description="API key (supports env var expansion like ${OPENAI_API_KEY})"
    )
    model: str = Field("gpt-4o-mini", description="Provider-specific model name")
    temperature: float = Field(0.3, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(500, gt=0, description="Maximum tokens to generate")
    timeout: int = Field(30, gt=0, description="API timeout in seconds")
    rate_limit: Dict[str, Any] = Field(
        default_factory=dict, description="Rate limiting configuration (for future use)"
    )
    fallback_to_template: bool = Field(
        True, description="Use template-based explanations if LLM fails"
    )
    chat: ChatConfig = Field(
        default_factory=lambda: ChatConfig(),  # type: ignore[call-arg]
        description="Chat interface configuration",
    )

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate provider name."""
        valid_providers = ["openai", "anthropic", "azure", "ollama"]
        if v not in valid_providers:
            raise ValueError(f"Provider must be one of {valid_providers}")
        return v


class VisualizationStylesConfig(BaseModel):
    """Visualization styling configuration."""

    node_colors: Dict[str, str] = Field(
        default_factory=lambda: {
            "healthy": "#4CAF50",
            "warning": "#FFC107",
            "drift": "#F44336",
        }
    )


class VisualizationConfig(BaseModel):
    """Lineage visualization configuration."""

    enabled: bool = Field(True, description="Enable lineage visualization features")
    max_depth: int = Field(
        3, ge=1, le=10, description="Default maximum depth for lineage traversal"
    )
    direction: str = Field("both", description="Default direction (upstream/downstream/both)")
    confidence_threshold: float = Field(
        0.5, ge=0.0, le=1.0, description="Default confidence threshold"
    )
    layout: str = Field("hierarchical", description="Default layout algorithm")
    web_viewer_port: int = Field(8080, description="Default port for web viewer")
    theme: str = Field("dark", description="Default theme (dark/light)")
    styles: VisualizationStylesConfig = Field(
        default_factory=lambda: VisualizationStylesConfig()  # type: ignore[call-arg]
    )

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str) -> str:
        """Validate direction."""
        valid = ["upstream", "downstream", "both"]
        if v not in valid:
            raise ValueError(f"Direction must be one of {valid}")
        return v

    @field_validator("layout")
    @classmethod
    def validate_layout(cls, v: str) -> str:
        """Validate layout algorithm."""
        valid = ["hierarchical", "circular", "force_directed", "grid"]
        if v not in valid:
            raise ValueError(f"Layout must be one of {valid}")
        return v

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, v: str) -> str:
        """Validate theme."""
        valid = ["dark", "light"]
        if v not in valid:
            raise ValueError(f"Theme must be one of {valid}")
        return v


class RCACollectorConfig(BaseModel):
    """Configuration for RCA data collectors."""

    dbt: Optional[bool] = Field(True, description="Enable dbt run collector")
    manifest_path: Optional[str] = Field(None, description="Path to dbt manifest.json")
    project_dir: Optional[str] = Field(None, description="DBT project directory")

    dagster: Optional[bool] = Field(False, description="Enable Dagster run collector")
    dagster_instance_path: Optional[str] = Field(
        None, description="Path to Dagster instance directory"
    )
    dagster_graphql_url: Optional[str] = Field(None, description="Dagster GraphQL API URL")

    airflow: Optional[bool] = Field(False, description="Enable Airflow run collector")
    airflow_api_url: Optional[str] = Field(None, description="Airflow API URL")
    airflow_api_version: Optional[str] = Field("v1", description="Airflow API version (v1 or v2)")
    airflow_username: Optional[str] = Field(None, description="Username for Airflow API auth")
    airflow_password: Optional[str] = Field(None, description="Password for Airflow API auth")
    airflow_metadata_db_connection: Optional[str] = Field(
        None, description="Connection string for direct Airflow metadata DB access"
    )
    airflow_dag_ids: Optional[List[str]] = Field(
        None, description="Optional list of DAG IDs to collect (None = all DAGs)"
    )


class RCAConfig(BaseModel):
    """Configuration for Root Cause Analysis."""

    enabled: bool = Field(True, description="Enable RCA features")
    lookback_window_hours: int = Field(
        24, ge=1, le=168, description="Time window for finding causes"
    )
    max_depth: int = Field(5, ge=1, le=10, description="Maximum depth for lineage traversal")
    max_causes_to_return: int = Field(
        5, ge=1, le=20, description="Maximum probable causes to return"
    )
    min_confidence_threshold: float = Field(
        0.3, ge=0.0, le=1.0, description="Minimum confidence to include a cause"
    )
    auto_analyze: bool = Field(True, description="Automatically analyze anomalies when detected")
    enable_pattern_learning: bool = Field(
        True, description="Use historical patterns to improve RCA"
    )
    collectors: RCACollectorConfig = Field(
        default_factory=lambda: RCACollectorConfig(),  # type: ignore[call-arg]
        description="Configuration for pipeline run collectors",
    )

    @field_validator("lookback_window_hours")
    @classmethod
    def validate_lookback_window(cls, v: int) -> int:
        """Validate lookback window is reasonable."""
        if v > 168:  # 7 days
            raise ValueError("lookback_window_hours should not exceed 168 (7 days)")
        return v


class ValidationRuleConfig(BaseModel):
    """Configuration for a single validation rule."""

    type: str = Field(
        ..., description="Rule type: format, range, enum, not_null, unique, referential"
    )
    table: Optional[str] = Field(
        None, description="Table name (optional, can be specified at provider level)"
    )
    column: Optional[str] = Field(None, description="Column name (None for table-level rules)")
    pattern: Optional[str] = Field(None, description="Regex pattern for format validation")
    min_value: Optional[float] = Field(None, description="Minimum value for range validation")
    max_value: Optional[float] = Field(None, description="Maximum value for range validation")
    allowed_values: Optional[List[Any]] = Field(
        None, description="Allowed values for enum validation"
    )
    references: Optional[Dict[str, str]] = Field(
        None, description="Reference config for referential validation: {table, column}"
    )
    severity: str = Field("medium", description="Severity level: low, medium, high")
    enabled: bool = Field(True, description="Whether this rule is enabled")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate rule type."""
        valid_types = ["format", "range", "enum", "not_null", "unique", "referential"]
        if v not in valid_types:
            raise ValueError(f"Rule type must be one of {valid_types}")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        """Validate severity level."""
        valid_severities = ["low", "medium", "high"]
        if v not in valid_severities:
            raise ValueError(f"Severity must be one of {valid_severities}")
        return v


class ValidationConfig(BaseModel):
    """Validation configuration."""

    enabled: bool = Field(True, description="Enable validation")
    providers: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of validation provider configurations"
    )
    rules: List[ValidationRuleConfig] = Field(
        default_factory=list,
        description=(
            "List of top-level validation rules. "
            "Validation rules must be defined in ODCS contracts. "
            "This field is ignored. Use ODCS contracts instead."
        ),
    )


class QualityScoringWeights(BaseModel):
    """Component weights for quality scoring."""

    completeness: float = Field(25.0, ge=0, le=100)
    validity: float = Field(25.0, ge=0, le=100)
    consistency: float = Field(20.0, ge=0, le=100)
    freshness: float = Field(15.0, ge=0, le=100)
    uniqueness: float = Field(10.0, ge=0, le=100)
    accuracy: float = Field(5.0, ge=0, le=100)

    @model_validator(mode="after")
    def validate_weights_sum(self):
        """Ensure weights sum to 100."""
        total = (
            self.completeness
            + self.validity
            + self.consistency
            + self.freshness
            + self.uniqueness
            + self.accuracy
        )
        if abs(total - 100.0) > 0.01:  # Allow small floating point differences
            raise ValueError(f"Quality scoring weights must sum to 100, got {total}")
        return self


class QualityScoringThresholds(BaseModel):
    """Score thresholds for status classification."""

    healthy: float = Field(80.0, ge=0, le=100)
    warning: float = Field(60.0, ge=0, le=100)
    critical: float = Field(0.0, ge=0, le=100)

    @model_validator(mode="after")
    def validate_thresholds(self):
        """Ensure thresholds are in descending order."""
        if not (self.critical <= self.warning <= self.healthy):
            raise ValueError(
                "Quality scoring thresholds must be in order: critical <= warning <= healthy"
            )
        return self


class QualityScoringFreshness(BaseModel):
    """Freshness thresholds in hours."""

    excellent: int = Field(24, gt=0)
    good: int = Field(48, gt=0)
    acceptable: int = Field(168, gt=0)  # 1 week

    @model_validator(mode="after")
    def validate_freshness(self):
        """Ensure freshness thresholds are in ascending order."""
        if not (self.excellent <= self.good <= self.acceptable):
            raise ValueError(
                "Freshness thresholds must be in order: excellent <= good <= acceptable"
            )
        return self


class QualityScoringConfig(BaseModel):
    """Quality scoring configuration."""

    enabled: bool = Field(True, description="Enable quality scoring")
    weights: QualityScoringWeights = Field(
        default_factory=lambda: QualityScoringWeights()  # type: ignore[call-arg]
    )
    thresholds: QualityScoringThresholds = Field(
        default_factory=lambda: QualityScoringThresholds()  # type: ignore[call-arg]
    )
    freshness: QualityScoringFreshness = Field(
        default_factory=lambda: QualityScoringFreshness()  # type: ignore[call-arg]
    )
    store_history: bool = Field(True, description="Store historical scores")
    history_retention_days: int = Field(90, gt=0, description="Days to retain score history")


class ContractsConfig(BaseModel):
    """Configuration for ODCS data contracts location.

    ODCS (Open Data Contract Standard) contracts define dataset schemas,
    quality rules, SLAs, and stakeholders in a standardized format.

    Example:
        contracts:
          directory: ./contracts
          recursive: true
          validate_on_load: true
    """

    directory: str = Field(
        "./contracts",
        description="Path to ODCS contracts directory (relative to config file or absolute)",
    )
    file_patterns: List[str] = Field(
        default_factory=lambda: ["*.odcs.yaml", "*.odcs.yml"],
        description="File patterns to match for ODCS contracts",
    )
    recursive: bool = Field(
        True,
        description="Recursively search subdirectories for contracts",
    )
    validate_on_load: bool = Field(
        True,
        description="Validate contracts against ODCS schema when loading",
    )
    exclude_patterns: Optional[List[str]] = Field(
        None,
        description="Patterns to exclude from discovery (e.g., ['**/templates/**'])",
    )
    strict_validation: bool = Field(
        False,
        description="Treat validation warnings as errors",
    )


class BaselinrConfig(BaseModel):
    """Main Baselinr configuration."""

    environment: str = Field("development")
    source: ConnectionConfig
    storage: StorageConfig
    profiling: ProfilingConfig = Field(
        default_factory=lambda: ProfilingConfig()  # type: ignore[call-arg]
    )
    drift_detection: DriftDetectionConfig = Field(
        default_factory=lambda: DriftDetectionConfig()  # type: ignore[call-arg]
    )
    hooks: HooksConfig = Field(default_factory=lambda: HooksConfig())  # type: ignore[call-arg]
    monitoring: MonitoringConfig = Field(
        default_factory=lambda: MonitoringConfig()  # type: ignore[call-arg]
    )
    retry: RetryConfig = Field(default_factory=lambda: RetryConfig())  # type: ignore[call-arg]
    execution: ExecutionConfig = Field(
        default_factory=lambda: ExecutionConfig()  # type: ignore[call-arg]
    )
    incremental: IncrementalConfig = Field(
        default_factory=lambda: IncrementalConfig()  # type: ignore[call-arg]
    )
    schema_change: SchemaChangeConfig = Field(
        default_factory=lambda: SchemaChangeConfig()  # type: ignore[call-arg]
    )
    lineage: Optional[LineageConfig] = Field(None, description="Lineage extraction configuration")
    visualization: VisualizationConfig = Field(
        default_factory=lambda: VisualizationConfig(),  # type: ignore[call-arg]
        description="Lineage visualization configuration",
    )
    llm: Optional[LLMConfig] = Field(None, description="LLM configuration for explanations")
    smart_selection: Optional[Any] = Field(
        None,
        description="Smart table selection configuration (imported lazily to avoid circular deps)",
    )
    rca: RCAConfig = Field(
        default_factory=lambda: RCAConfig(),  # type: ignore[call-arg]
        description="Root Cause Analysis configuration",
    )
    validation: Optional["ValidationConfig"] = Field(
        None, description="Data validation configuration"
    )
    quality_scoring: Optional["QualityScoringConfig"] = Field(
        None, description="Quality scoring configuration"
    )

    # ODCS Contracts configuration
    contracts: Optional[ContractsConfig] = Field(
        None,
        description=(
            "ODCS data contracts configuration. Specifies the directory containing "
            "ODCS v3.1.0 contracts that define dataset schemas, quality rules, and SLAs."
        ),
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment name."""
        valid_envs = ["development", "test", "production"]
        if v not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        return v
