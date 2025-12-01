"""
Configuration schema for smart table selection.

Defines Pydantic models for smart selection configuration.
"""

from typing import Dict, List, Optional

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


class SmartSelectionConfig(BaseModel):
    """Smart table selection configuration."""

    enabled: bool = Field(False, description="Enable smart table selection")
    mode: str = Field(
        "recommend",
        description=(
            "Selection mode: 'recommend' (generate suggestions), "
            "'auto' (apply automatically), or 'disabled'"
        ),
    )

    criteria: SmartSelectionCriteria = Field(
        default_factory=lambda: SmartSelectionCriteria(),  # type: ignore[call-arg]
        description="Selection criteria",
    )

    recommendations: SmartSelectionRecommendations = Field(
        default_factory=lambda: SmartSelectionRecommendations(),  # type: ignore[call-arg]
        description="Recommendation generation settings",
    )

    auto_apply: SmartSelectionAutoApply = Field(
        default_factory=lambda: SmartSelectionAutoApply(),  # type: ignore[call-arg]
        description="Auto-apply settings",
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
