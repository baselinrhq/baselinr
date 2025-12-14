"""
Data models for quality scoring.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class ScoreStatus(str, Enum):
    """Status classification for quality scores."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


class ScoreComponent(str, Enum):
    """Components of the quality score."""

    COMPLETENESS = "completeness"
    VALIDITY = "validity"
    CONSISTENCY = "consistency"
    FRESHNESS = "freshness"
    UNIQUENESS = "uniqueness"
    ACCURACY = "accuracy"


@dataclass
class DataQualityScore:
    """Comprehensive data quality score."""

    overall_score: float  # 0-100
    completeness_score: float
    validity_score: float
    consistency_score: float
    freshness_score: float
    uniqueness_score: float
    accuracy_score: float
    status: str  # "healthy", "warning", "critical"
    total_issues: int
    critical_issues: int
    warnings: int
    table_name: str
    schema_name: Optional[str]
    run_id: Optional[str]
    calculated_at: datetime
    period_start: datetime
    period_end: datetime

    def to_dict(self) -> dict:
        """Convert score to dictionary."""
        return {
            "overall_score": self.overall_score,
            "completeness_score": self.completeness_score,
            "validity_score": self.validity_score,
            "consistency_score": self.consistency_score,
            "freshness_score": self.freshness_score,
            "uniqueness_score": self.uniqueness_score,
            "accuracy_score": self.accuracy_score,
            "status": self.status,
            "total_issues": self.total_issues,
            "critical_issues": self.critical_issues,
            "warnings": self.warnings,
            "table_name": self.table_name,
            "schema_name": self.schema_name,
            "run_id": self.run_id,
            "calculated_at": self.calculated_at.isoformat(),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
        }


@dataclass
class ColumnQualityScore:
    """Data quality score for a specific column."""

    overall_score: float  # 0-100
    completeness_score: float
    validity_score: float
    consistency_score: float
    freshness_score: float
    uniqueness_score: float
    accuracy_score: float
    status: str  # "healthy", "warning", "critical"
    table_name: str
    schema_name: Optional[str]
    column_name: str
    run_id: Optional[str]
    calculated_at: datetime
    period_start: datetime
    period_end: datetime

    def to_dict(self) -> dict:
        """Convert score to dictionary."""
        return {
            "overall_score": self.overall_score,
            "completeness_score": self.completeness_score,
            "validity_score": self.validity_score,
            "consistency_score": self.consistency_score,
            "freshness_score": self.freshness_score,
            "uniqueness_score": self.uniqueness_score,
            "accuracy_score": self.accuracy_score,
            "status": self.status,
            "table_name": self.table_name,
            "schema_name": self.schema_name,
            "column_name": self.column_name,
            "run_id": self.run_id,
            "calculated_at": self.calculated_at.isoformat(),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
        }
