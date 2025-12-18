"""
Demo quality storage for serving pre-generated quality scores.

This module provides a QualityScoreStorage-compatible interface for demo mode,
loading quality scores from JSON files instead of a database.
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

# Add parent directory to path to import baselinr
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from baselinr.quality.models import DataQualityScore, ColumnQualityScore


class DemoQualityStorage:
    """Demo quality score storage that loads from JSON files."""
    
    def __init__(self, data_dir: str = "demo_data"):
        """
        Initialize demo quality storage.
        
        Args:
            data_dir: Directory containing quality score JSON files
        """
        self.data_dir = data_dir
        self.table_scores_raw = []
        self.column_scores_raw = []
        self._load_data()
    
    def _load_data(self):
        """Load quality score JSON files."""
        try:
            # Load table quality scores
            table_scores_file = os.path.join(self.data_dir, "table_quality_scores.json")
            if os.path.exists(table_scores_file):
                with open(table_scores_file, 'r') as f:
                    self.table_scores_raw = json.load(f)
                logger.info(f"Loaded {len(self.table_scores_raw)} table quality scores")
            
            # Load column quality scores
            column_scores_file = os.path.join(self.data_dir, "column_quality_scores.json")
            if os.path.exists(column_scores_file):
                with open(column_scores_file, 'r') as f:
                    self.column_scores_raw = json.load(f)
                logger.info(f"Loaded {len(self.column_scores_raw)} column quality scores")
        
        except Exception as e:
            logger.error(f"Error loading demo quality scores: {e}")
            raise
    
    def _parse_datetime(self, date_str: str) -> datetime:
        """Parse ISO datetime string to datetime object."""
        if isinstance(date_str, datetime):
            return date_str
        dt = datetime.fromisoformat(date_str)
        # Make timezone-naive for consistent comparison
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    
    def _to_data_quality_score(self, raw: Dict[str, Any]) -> DataQualityScore:
        """Convert raw dict to DataQualityScore object."""
        return DataQualityScore(
            overall_score=raw["overall_score"],
            completeness_score=raw["completeness_score"],
            validity_score=raw["validity_score"],
            consistency_score=raw["consistency_score"],
            freshness_score=raw["freshness_score"],
            uniqueness_score=raw["uniqueness_score"],
            accuracy_score=raw["accuracy_score"],
            status=raw["status"],
            total_issues=raw["total_issues"],
            critical_issues=raw["critical_issues"],
            warnings=raw["warnings"],
            table_name=raw["table_name"],
            schema_name=raw.get("schema_name"),
            run_id=raw.get("run_id"),
            calculated_at=self._parse_datetime(raw["calculated_at"]),
            period_start=self._parse_datetime(raw["period_start"]),
            period_end=self._parse_datetime(raw["period_end"])
        )
    
    def _to_column_quality_score(self, raw: Dict[str, Any]) -> ColumnQualityScore:
        """Convert raw dict to ColumnQualityScore object."""
        return ColumnQualityScore(
            overall_score=raw["overall_score"],
            completeness_score=raw["completeness_score"],
            validity_score=raw["validity_score"],
            consistency_score=raw["consistency_score"],
            freshness_score=raw["freshness_score"],
            uniqueness_score=raw["uniqueness_score"],
            accuracy_score=raw["accuracy_score"],
            status=raw["status"],
            table_name=raw["table_name"],
            schema_name=raw.get("schema_name"),
            column_name=raw["column_name"],
            run_id=raw.get("run_id"),
            calculated_at=self._parse_datetime(raw["calculated_at"]),
            period_start=self._parse_datetime(raw["period_start"]),
            period_end=self._parse_datetime(raw["period_end"])
        )
    
    def get_latest_score(
        self, table_name: str, schema_name: Optional[str] = None
    ) -> Optional[DataQualityScore]:
        """Get the latest quality score for a table."""
        # Filter by table and schema
        filtered = [
            s for s in self.table_scores_raw
            if s["table_name"] == table_name
            and (schema_name is None or s.get("schema_name") == schema_name)
        ]
        
        if not filtered:
            return None
        
        # Sort by calculated_at and get the latest
        filtered.sort(key=lambda s: s["calculated_at"], reverse=True)
        return self._to_data_quality_score(filtered[0])
    
    def get_score_history(
        self, table_name: str, schema_name: Optional[str] = None, days: int = 30
    ) -> List[DataQualityScore]:
        """Get quality score history for a table."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Filter by table, schema, and date
        filtered = [
            s for s in self.table_scores_raw
            if s["table_name"] == table_name
            and (schema_name is None or s.get("schema_name") == schema_name)
            and self._parse_datetime(s["calculated_at"]) >= cutoff_date
        ]
        
        # Sort by calculated_at (newest first)
        filtered.sort(key=lambda s: s["calculated_at"], reverse=True)
        
        return [self._to_data_quality_score(s) for s in filtered]
    
    def query_all_latest_scores(
        self, schema_name: Optional[str] = None
    ) -> List[DataQualityScore]:
        """Get the latest score for all tables."""
        # Group by table and schema
        by_table = defaultdict(list)
        for score in self.table_scores_raw:
            if schema_name is None or score.get("schema_name") == schema_name:
                key = (score["table_name"], score.get("schema_name"))
                by_table[key].append(score)
        
        # Get latest for each table
        latest_scores = []
        for scores in by_table.values():
            scores.sort(key=lambda s: s["calculated_at"], reverse=True)
            latest_scores.append(self._to_data_quality_score(scores[0]))
        
        return latest_scores
    
    def query_scores_by_schema(self, schema_name: str) -> List[DataQualityScore]:
        """Get all scores for a schema."""
        filtered = [
            s for s in self.table_scores_raw
            if s.get("schema_name") == schema_name
        ]
        
        return [self._to_data_quality_score(s) for s in filtered]
    
    def query_system_scores(self) -> List[DataQualityScore]:
        """Get all scores across the system."""
        return [self._to_data_quality_score(s) for s in self.table_scores_raw]
    
    def get_column_scores_for_table(
        self, table_name: str, schema_name: Optional[str] = None, days: int = 30
    ) -> List[ColumnQualityScore]:
        """Get column-level scores for a table."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Group by column to get latest for each
        by_column = defaultdict(list)
        for score in self.column_scores_raw:
            if (score["table_name"] == table_name and
                (schema_name is None or score.get("schema_name") == schema_name) and
                self._parse_datetime(score["calculated_at"]) >= cutoff_date):
                
                column_key = score["column_name"]
                by_column[column_key].append(score)
        
        # Get latest score for each column
        column_scores = []
        for scores in by_column.values():
            scores.sort(key=lambda s: s["calculated_at"], reverse=True)
            column_scores.append(self._to_column_quality_score(scores[0]))
        
        return column_scores

