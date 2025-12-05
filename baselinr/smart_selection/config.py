"""
Configuration schema for smart table and column selection.

Defines Pydantic models for smart selection configuration
including table-level and column-level recommendations.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class SmartSelectionCriteria(BaseModel):
    """Criteria for table selection."""

    min_query_count: int = Field(10, ge=0, description="Minimum query count in lookback period")
    min_queries_per_day: float = Field(1.0, ge=0.0, description="Minimum average queries per day")
    lookback_days: int = Field(30, ge=1, le=365, description="Number of days to look back")
    exclude_patterns: List[str] = Field(
        default_factory=list, description="Patterns to exclude (wildcards supported)"
    )

    # Size thresholds
    min_rows: Optional[int] = Field(100, ge=0, description="Minimum row count")
    max_rows: Optional[int] = Field(None, description="Maximum row count (None = no limit)")

    # Recency thresholds
    max_days_since_query: Optional[int] = Field(
        None, ge=1, description="Only include tables queried in last N days"
    )
    max_days_since_modified: Optional[int] = Field(
        None, ge=1, description="Only include tables modified in last N days"
    )

    # Weight configuration (for scoring)
    weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "query_frequency": 0.4,
            "query_recency": 0.25,
            "write_activity": 0.2,
            "table_size": 0.15,
        },
        description="Scoring weights for different factors (should sum to 1.0)",
    )

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate that weights are positive and sum to approximately 1.0."""
        total = sum(v.values())
        if not (0.95 <= total <= 1.05):  # Allow small floating point variance
            raise ValueError(f"Weights should sum to 1.0, got {total:.3f}")

        for key, value in v.items():
            if value < 0:
                raise ValueError(f"Weight '{key}' must be non-negative, got {value}")

        return v


class SmartSelectionRecommendations(BaseModel):
    """Configuration for recommendation generation mode."""

    output_file: str = Field("recommendations.yaml", description="Output file for recommendations")
    auto_refresh_days: int = Field(
        7, ge=1, description="Number of days before recommendations should be refreshed"
    )
    include_explanations: bool = Field(
        True, description="Include detailed explanations in recommendations"
    )
    include_suggested_checks: bool = Field(True, description="Include suggested profiling checks")


class SmartSelectionAutoApply(BaseModel):
    """Configuration for auto-apply mode."""

    confidence_threshold: float = Field(
        0.8,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score to auto-apply a recommendation",
    )
    max_tables: int = Field(100, ge=1, description="Maximum number of tables to auto-select")
    skip_existing: bool = Field(True, description="Skip tables already in explicit configuration")


class ColumnInferenceConfig(BaseModel):
    """Configuration for column check inference."""

    use_profiling_data: bool = Field(
        True, description="Use existing profile stats for inference if available"
    )
    confidence_threshold: float = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score to recommend a check",
    )
    max_checks_per_column: int = Field(
        5, ge=1, le=20, description="Maximum number of checks to recommend per column"
    )

    # Column prioritization settings
    prioritize_primary_keys: bool = Field(
        True, description="Give higher priority to primary key columns"
    )
    prioritize_foreign_keys: bool = Field(
        True, description="Give higher priority to foreign key columns"
    )
    prioritize_timestamp_columns: bool = Field(
        True, description="Give higher priority to timestamp columns"
    )
    deprioritize_high_cardinality_strings: bool = Field(
        False, description="Lower priority for high-cardinality string columns (can be noisy)"
    )

    # Check type preferences
    preferred_checks: List[str] = Field(
        default_factory=lambda: ["completeness", "freshness", "uniqueness"],
        description="Check types to prefer in recommendations",
    )
    avoided_checks: List[str] = Field(
        default_factory=list,
        description="Check types to avoid recommending (e.g., 'custom_sql')",
    )

    @field_validator("preferred_checks", "avoided_checks")
    @classmethod
    def validate_check_types(cls, v: List[str]) -> List[str]:
        """Validate check type names."""
        valid_checks = {
            "completeness",
            "freshness",
            "uniqueness",
            "not_null",
            "format_email",
            "format_phone",
            "format_url",
            "format_uuid",
            "range",
            "non_negative",
            "allowed_values",
            "valid_date_range",
            "distribution",
            "referential_integrity",
            "valid_json",
            "custom_sql",
        }
        invalid = [c for c in v if c not in valid_checks]
        if invalid:
            # Allow custom check types, just warn
            pass
        return v


class ColumnPatternConfig(BaseModel):
    """Configuration for a custom column pattern override."""

    match: str = Field(..., description="Column name pattern (supports wildcards: *, ?)")
    pattern_type: str = Field("wildcard", description="Pattern type: 'wildcard' or 'regex'")
    checks: List[Dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "List of checks to apply. Each check has 'type' and " "optional 'confidence', 'config'."
        ),
    )

    @field_validator("pattern_type")
    @classmethod
    def validate_pattern_type(cls, v: str) -> str:
        """Validate pattern type."""
        if v not in ("wildcard", "regex"):
            raise ValueError("pattern_type must be 'wildcard' or 'regex'")
        return v


class ColumnSelectionConfig(BaseModel):
    """Configuration for column-level smart selection."""

    enabled: bool = Field(True, description="Enable column-level check recommendations")
    mode: str = Field(
        "recommend",
        description=(
            "Mode: 'recommend' (generate suggestions), "
            "'auto' (apply automatically), or 'disabled'"
        ),
    )

    inference: ColumnInferenceConfig = Field(
        default_factory=lambda: ColumnInferenceConfig(),  # type: ignore[call-arg]
        description="Check inference settings",
    )

    # Custom pattern overrides
    patterns: List[ColumnPatternConfig] = Field(
        default_factory=list,
        description="Custom pattern rules that override default inference",
    )

    # Learning settings
    learn_from_config: bool = Field(
        True, description="Learn patterns from existing column configurations"
    )
    learned_patterns_file: Optional[str] = Field(
        None, description="File to store/load learned patterns"
    )

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        """Validate mode."""
        valid_modes = ["recommend", "auto", "disabled"]
        if v not in valid_modes:
            raise ValueError(f"mode must be one of {valid_modes}")
        return v


class LineageQueryConfig(BaseModel):
    """Configuration for lineage query operations."""

    cache_ttl_hours: int = Field(
        24, ge=1, le=168, description="Cache TTL in hours for lineage data"
    )
    max_depth: int = Field(
        10, ge=1, le=50, description="Maximum depth for recursive lineage queries"
    )
    include_column_lineage: bool = Field(
        False, description="Include column-level lineage (future enhancement)"
    )


class LineageScoringWeightsConfig(BaseModel):
    """Weights for lineage impact scoring components."""

    downstream_count: float = Field(
        0.4, ge=0.0, le=1.0, description="Weight for downstream dependency count"
    )
    criticality: float = Field(
        0.3, ge=0.0, le=1.0, description="Weight for criticality of downstream assets"
    )
    depth_position: float = Field(
        0.2,
        ge=0.0,
        le=1.0,
        description="Weight for position in lineage (closer to source = higher)",
    )
    fanout: float = Field(0.1, ge=0.0, le=1.0, description="Weight for fanout factor (branching)")

    @field_validator("fanout")
    @classmethod
    def validate_weights_sum(cls, v: float, info) -> float:
        """Validate that all weights sum to approximately 1.0."""
        data = info.data
        total = (
            data.get("downstream_count", 0.4)
            + data.get("criticality", 0.3)
            + data.get("depth_position", 0.2)
            + v
        )
        if not (0.95 <= total <= 1.05):
            raise ValueError(f"Lineage scoring weights should sum to 1.0, got {total:.3f}")
        return v


class LineageBoostsConfig(BaseModel):
    """Boost factors for different table types based on lineage position."""

    root_tables: float = Field(
        1.25, ge=1.0, le=2.0, description="Score boost for root/source tables"
    )
    critical_path: float = Field(
        1.20, ge=1.0, le=2.0, description="Score boost for tables on critical paths"
    )
    high_fanout: float = Field(
        1.15, ge=1.0, le=2.0, description="Score boost for high-fanout tables"
    )


class LineagePenaltiesConfig(BaseModel):
    """Penalty factors for different table types based on lineage position."""

    leaf_tables: float = Field(
        0.60, ge=0.1, le=1.0, description="Score penalty for leaf tables with no downstream"
    )
    orphaned_tables: float = Field(
        0.50, ge=0.1, le=1.0, description="Score penalty for orphaned tables"
    )


class LineageScoringConfig(BaseModel):
    """Configuration for lineage-based impact scoring."""

    weights: LineageScoringWeightsConfig = Field(
        default_factory=lambda: LineageScoringWeightsConfig(),  # type: ignore[call-arg]
        description="Component weights for impact scoring",
    )
    boosts: LineageBoostsConfig = Field(
        default_factory=lambda: LineageBoostsConfig(),  # type: ignore[call-arg]
        description="Boost factors for prioritized table types",
    )
    penalties: LineagePenaltiesConfig = Field(
        default_factory=lambda: LineagePenaltiesConfig(),  # type: ignore[call-arg]
        description="Penalty factors for deprioritized table types",
    )


class LineageCheckAdjustmentConfig(BaseModel):
    """Check adjustments based on lineage position."""

    prioritize_checks: List[str] = Field(
        default_factory=list,
        description="Checks to prioritize for this table type",
    )
    severity: Optional[str] = Field(
        None, description="Default severity level (low, medium, high, critical)"
    )
    min_confidence_threshold: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Minimum confidence for check recommendations"
    )
    check_frequency: Optional[str] = Field(None, description="Check frequency (low, medium, high)")

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: Optional[str]) -> Optional[str]:
        """Validate severity level."""
        if v is not None:
            valid = ["low", "medium", "high", "critical"]
            if v not in valid:
                raise ValueError(f"severity must be one of {valid}")
        return v

    @field_validator("check_frequency")
    @classmethod
    def validate_frequency(cls, v: Optional[str]) -> Optional[str]:
        """Validate check frequency."""
        if v is not None:
            valid = ["low", "medium", "high"]
            if v not in valid:
                raise ValueError(f"check_frequency must be one of {valid}")
        return v


class LineageCheckAdjustmentsConfig(BaseModel):
    """Configuration for check adjustments based on lineage position."""

    root_tables: LineageCheckAdjustmentConfig = Field(
        default_factory=lambda: LineageCheckAdjustmentConfig(
            prioritize_checks=["freshness", "completeness", "schema_validation"],
            severity="critical",
            min_confidence_threshold=None,
            check_frequency=None,
        ),
        description="Check adjustments for root/source tables",
    )
    high_impact: LineageCheckAdjustmentConfig = Field(
        default_factory=lambda: LineageCheckAdjustmentConfig(
            prioritize_checks=[],
            severity=None,
            min_confidence_threshold=0.6,
            check_frequency="high",
        ),
        description="Check adjustments for high-impact tables",
    )
    leaf_tables: LineageCheckAdjustmentConfig = Field(
        default_factory=lambda: LineageCheckAdjustmentConfig(
            prioritize_checks=[],
            severity=None,
            min_confidence_threshold=0.8,
            check_frequency="medium",
        ),
        description="Check adjustments for leaf tables",
    )


class LineageReportingConfig(BaseModel):
    """Configuration for lineage visualization and reporting."""

    generate_lineage_diagram: bool = Field(True, description="Generate lineage diagram in output")
    output_path: str = Field("lineage_graph.html", description="Output path for lineage diagram")
    highlight_critical_paths: bool = Field(
        True, description="Highlight critical paths in visualization"
    )
    show_blast_radius: bool = Field(
        True, description="Show blast radius information in recommendations"
    )


class LineageConfig(BaseModel):
    """Configuration for lineage-aware prioritization (Phase 3)."""

    enabled: bool = Field(True, description="Enable lineage-aware prioritization")

    # Lineage weight in final scoring
    lineage_weight: float = Field(
        0.4,
        ge=0.0,
        le=1.0,
        description="Weight for lineage score in final table score (rest is usage-based)",
    )

    # Lineage query configuration
    query: LineageQueryConfig = Field(
        default_factory=lambda: LineageQueryConfig(),  # type: ignore[call-arg]
        description="Lineage query settings",
    )

    # Impact scoring configuration
    scoring: LineageScoringConfig = Field(
        default_factory=lambda: LineageScoringConfig(),  # type: ignore[call-arg]
        description="Impact scoring configuration",
    )

    # Check adjustments based on lineage
    check_adjustments: LineageCheckAdjustmentsConfig = Field(
        default_factory=lambda: LineageCheckAdjustmentsConfig(),  # type: ignore[call-arg]
        description="Check adjustments based on lineage position",
    )

    # Visualization and reporting
    reporting: LineageReportingConfig = Field(
        default_factory=lambda: LineageReportingConfig(),  # type: ignore[call-arg]
        description="Lineage visualization and reporting settings",
    )


class SmartSelectionConfig(BaseModel):
    """Smart table and column selection configuration."""

    enabled: bool = Field(False, description="Enable smart selection")
    mode: str = Field(
        "recommend",
        description=(
            "Selection mode: 'recommend' (generate suggestions), "
            "'auto' (apply automatically), or 'disabled'"
        ),
    )

    # Table selection (Phase 1)
    criteria: SmartSelectionCriteria = Field(
        default_factory=lambda: SmartSelectionCriteria(),  # type: ignore[call-arg]
        description="Table selection criteria",
    )

    recommendations: SmartSelectionRecommendations = Field(
        default_factory=lambda: SmartSelectionRecommendations(),  # type: ignore[call-arg]
        description="Recommendation generation settings",
    )

    auto_apply: SmartSelectionAutoApply = Field(
        default_factory=lambda: SmartSelectionAutoApply(),  # type: ignore[call-arg]
        description="Auto-apply settings",
    )

    # Column selection (Phase 2)
    columns: ColumnSelectionConfig = Field(
        default_factory=lambda: ColumnSelectionConfig(),  # type: ignore[call-arg]
        description="Column-level check recommendation settings",
    )

    # Lineage-aware prioritization (Phase 3)
    lineage: LineageConfig = Field(
        default_factory=lambda: LineageConfig(),  # type: ignore[call-arg]
        description="Lineage-aware prioritization settings",
    )

    # Cache settings
    cache_metadata: bool = Field(True, description="Cache metadata queries for performance")
    cache_ttl_seconds: int = Field(3600, ge=60, description="TTL for metadata cache in seconds")

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        """Validate selection mode."""
        valid_modes = ["recommend", "auto", "disabled"]
        if v not in valid_modes:
            raise ValueError(f"mode must be one of {valid_modes}")
        return v
