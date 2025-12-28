"""
Tests for quality score export functionality.
"""

import pytest
import csv
import json
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

from baselinr.quality.models import DataQualityScore
from baselinr.quality.storage import QualityScoreStorage
from sqlalchemy import create_engine


@pytest.fixture
def sample_score():
    """Create a sample quality score."""
    return DataQualityScore(
        overall_score=85.5,
        completeness_score=90.0,
        validity_score=88.0,
        consistency_score=82.0,
        freshness_score=95.0,
        uniqueness_score=85.0,
        accuracy_score=78.0,
        status="healthy",
        total_issues=3,
        critical_issues=1,
        warnings=2,
        table_name="customers",
        schema_name="public",
        run_id="test_run_123",
        calculated_at=datetime(2024, 1, 15, 10, 30, 0),
        period_start=datetime(2024, 1, 8, 10, 30, 0),
        period_end=datetime(2024, 1, 15, 10, 30, 0),
    )


@pytest.fixture
def sample_scores():
    """Create multiple sample scores for history."""
    base_time = datetime(2024, 1, 15, 10, 30, 0)
    scores = []
    for i in range(5):
        score = DataQualityScore(
            overall_score=85.5 - (i * 2),
            completeness_score=90.0,
            validity_score=88.0,
            consistency_score=82.0,
            freshness_score=95.0,
            uniqueness_score=85.0,
            accuracy_score=78.0,
            status="healthy" if (85.5 - (i * 2)) >= 80 else "warning",
            total_issues=3 + i,
            critical_issues=1,
            warnings=2 + i,
            table_name="customers",
            schema_name="public",
            run_id=f"test_run_{i}",
            calculated_at=base_time - timedelta(days=i),
            period_start=base_time - timedelta(days=i + 7),
            period_end=base_time - timedelta(days=i),
        )
        scores.append(score)
    return scores


class TestCSVExport:
    """Test CSV export functionality."""

    def test_export_single_score_to_csv(self, sample_score):
        """Test exporting a single score to CSV."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            temp_path = f.name
        
        try:
            # Write CSV
            fieldnames = [
                "table_name", "schema_name", "overall_score",
                "completeness_score", "validity_score", "consistency_score",
                "freshness_score", "uniqueness_score", "accuracy_score",
                "status", "total_issues", "critical_issues", "warnings",
                "calculated_at", "period_start", "period_end"
            ]
            
            with open(temp_path, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow({
                    "table_name": sample_score.table_name,
                    "schema_name": sample_score.schema_name or "",
                    "overall_score": sample_score.overall_score,
                    "completeness_score": sample_score.completeness_score,
                    "validity_score": sample_score.validity_score,
                    "consistency_score": sample_score.consistency_score,
                    "freshness_score": sample_score.freshness_score,
                    "uniqueness_score": sample_score.uniqueness_score,
                    "accuracy_score": sample_score.accuracy_score,
                    "status": sample_score.status,
                    "total_issues": sample_score.total_issues,
                    "critical_issues": sample_score.critical_issues,
                    "warnings": sample_score.warnings,
                    "calculated_at": sample_score.calculated_at.isoformat(),
                    "period_start": sample_score.period_start.isoformat(),
                    "period_end": sample_score.period_end.isoformat(),
                })
            
            # Verify CSV content
            with open(temp_path, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                row = next(reader)
                assert row["table_name"] == "customers"
                assert row["schema_name"] == "public"
                assert float(row["overall_score"]) == 85.5
                assert float(row["completeness_score"]) == 90.0
                assert row["status"] == "healthy"
                assert int(row["total_issues"]) == 3
        finally:
            os.unlink(temp_path)

    def test_export_history_to_csv(self, sample_scores):
        """Test exporting score history to CSV."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            temp_path = f.name
        
        try:
            fieldnames = [
                "table_name", "schema_name", "overall_score",
                "completeness_score", "validity_score", "consistency_score",
                "freshness_score", "uniqueness_score", "accuracy_score",
                "status", "total_issues", "critical_issues", "warnings",
                "calculated_at", "period_start", "period_end"
            ]
            
            with open(temp_path, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for score in sample_scores:
                    writer.writerow({
                        "table_name": score.table_name,
                        "schema_name": score.schema_name or "",
                        "overall_score": score.overall_score,
                        "completeness_score": score.completeness_score,
                        "validity_score": score.validity_score,
                        "consistency_score": score.consistency_score,
                        "freshness_score": score.freshness_score,
                        "uniqueness_score": score.uniqueness_score,
                        "accuracy_score": score.accuracy_score,
                        "status": score.status,
                        "total_issues": score.total_issues,
                        "critical_issues": score.critical_issues,
                        "warnings": score.warnings,
                        "calculated_at": score.calculated_at.isoformat(),
                        "period_start": score.period_start.isoformat(),
                        "period_end": score.period_end.isoformat(),
                    })
            
            # Verify CSV content
            with open(temp_path, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)
                assert len(rows) == 5
                assert float(rows[0]["overall_score"]) == 85.5
                assert float(rows[-1]["overall_score"]) == 77.5
        finally:
            os.unlink(temp_path)


class TestJSONExport:
    """Test JSON export functionality."""

    def test_export_single_score_to_json(self, sample_score):
        """Test exporting a single score to JSON."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            # Write JSON
            with open(temp_path, 'w') as jsonfile:
                json.dump(sample_score.to_dict(), jsonfile, indent=2, default=str)
            
            # Verify JSON content
            with open(temp_path, 'r') as jsonfile:
                data = json.load(jsonfile)
                assert data["table_name"] == "customers"
                assert data["schema_name"] == "public"
                assert data["overall_score"] == 85.5
                assert data["completeness_score"] == 90.0
                assert data["status"] == "healthy"
                assert data["total_issues"] == 3
        finally:
            os.unlink(temp_path)

    def test_export_history_to_json(self, sample_scores):
        """Test exporting score history to JSON."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            # Write JSON
            with open(temp_path, 'w') as jsonfile:
                json.dump([s.to_dict() for s in sample_scores], jsonfile, indent=2, default=str)
            
            # Verify JSON content
            with open(temp_path, 'r') as jsonfile:
                data = json.load(jsonfile)
                assert isinstance(data, list)
                assert len(data) == 5
                assert data[0]["overall_score"] == 85.5
                assert data[-1]["overall_score"] == 77.5
                assert all("table_name" in item for item in data)
                assert all("calculated_at" in item for item in data)
        finally:
            os.unlink(temp_path)


class TestExportFormat:
    """Test export format correctness."""

    def test_csv_has_all_required_columns(self, sample_score):
        """Test CSV export includes all required columns."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            temp_path = f.name
        
        try:
            fieldnames = [
                "table_name", "schema_name", "overall_score",
                "completeness_score", "validity_score", "consistency_score",
                "freshness_score", "uniqueness_score", "accuracy_score",
                "status", "total_issues", "critical_issues", "warnings",
                "calculated_at", "period_start", "period_end"
            ]
            
            with open(temp_path, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                score_dict = sample_score.to_dict()
                # Remove run_id as it's not in the CSV export format
                score_dict.pop('run_id', None)
                writer.writerow(score_dict)
            
            with open(temp_path, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                row = next(reader)
                for field in fieldnames:
                    assert field in row
        finally:
            os.unlink(temp_path)

    def test_json_has_all_required_fields(self, sample_score):
        """Test JSON export includes all required fields."""
        score_dict = sample_score.to_dict()
        
        required_fields = [
            "overall_score", "completeness_score", "validity_score",
            "consistency_score", "freshness_score", "uniqueness_score",
            "accuracy_score", "status", "total_issues", "critical_issues",
            "warnings", "table_name", "schema_name", "calculated_at",
            "period_start", "period_end"
        ]
        
        for field in required_fields:
            assert field in score_dict









