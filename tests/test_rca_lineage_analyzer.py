"""
Tests for lineage-based analyzer.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

from baselinr.rca.analysis.lineage_analyzer import LineageAnalyzer


@pytest.fixture
def sqlite_engine_with_lineage():
    """Create SQLite database with lineage data."""
    engine = create_engine("sqlite:///:memory:")
    
    with engine.connect() as conn:
        # Create lineage table
        conn.execute(text("""
            CREATE TABLE baselinr_lineage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                downstream_database VARCHAR(255),
                downstream_schema VARCHAR(255) NOT NULL,
                downstream_table VARCHAR(255) NOT NULL,
                upstream_database VARCHAR(255),
                upstream_schema VARCHAR(255) NOT NULL,
                upstream_table VARCHAR(255) NOT NULL,
                lineage_type VARCHAR(50) NOT NULL,
                provider VARCHAR(50) NOT NULL,
                confidence_score FLOAT DEFAULT 1.0,
                first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """))
        
        # Create events table for anomaly tracking
        conn.execute(text("""
            CREATE TABLE baselinr_events (
                event_id VARCHAR(36) PRIMARY KEY,
                event_type VARCHAR(100) NOT NULL,
                run_id VARCHAR(36),
                table_name VARCHAR(255),
                column_name VARCHAR(255),
                metric_name VARCHAR(100),
                baseline_value FLOAT,
                current_value FLOAT,
                change_percent FLOAT,
                drift_severity VARCHAR(20),
                timestamp TIMESTAMP NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Add sample lineage:
        # raw_data -> staging_data -> sales_aggregate
        conn.execute(text("""
            INSERT INTO baselinr_lineage 
            (downstream_schema, downstream_table, upstream_schema, upstream_table, 
             lineage_type, provider)
            VALUES 
            ('public', 'staging_data', 'public', 'raw_data', 'table', 'dbt'),
            ('public', 'sales_aggregate', 'public', 'staging_data', 'table', 'dbt')
        """))
        
        conn.commit()
    
    return engine


def test_get_upstream_tables(sqlite_engine_with_lineage):
    """Test getting upstream tables from lineage."""
    analyzer = LineageAnalyzer(sqlite_engine_with_lineage, max_depth=5)
    
    # Get upstream tables for sales_aggregate
    upstream = analyzer._get_upstream_tables("sales_aggregate", None, "public")
    
    # Should find staging_data (distance=1) and raw_data (distance=2)
    upstream_names = [table for table, _ in upstream]
    assert "public.staging_data" in upstream_names
    assert "public.raw_data" in upstream_names
    
    # Check distances
    staging_distance = next(d for t, d in upstream if t == "public.staging_data")
    raw_distance = next(d for t, d in upstream if t == "public.raw_data")
    assert staging_distance == 1
    assert raw_distance == 2


def test_get_downstream_tables(sqlite_engine_with_lineage):
    """Test getting downstream tables from lineage."""
    analyzer = LineageAnalyzer(sqlite_engine_with_lineage, max_depth=5)
    
    # Get downstream tables for raw_data
    downstream = analyzer._get_downstream_tables("raw_data", None, "public")
    
    # Should find staging_data (distance=1) and sales_aggregate (distance=2)
    downstream_names = [table for table, _ in downstream]
    assert "public.staging_data" in downstream_names
    assert "public.sales_aggregate" in downstream_names


def test_calculate_impact_analysis(sqlite_engine_with_lineage):
    """Test impact analysis calculation."""
    analyzer = LineageAnalyzer(sqlite_engine_with_lineage, max_depth=5)
    
    # Calculate impact for staging_data
    impact = analyzer.calculate_impact_analysis("staging_data", None, "public")
    
    # Should have raw_data upstream and sales_aggregate downstream
    assert len(impact.upstream_affected) > 0
    assert len(impact.downstream_affected) > 0
    assert "public.raw_data" in impact.upstream_affected
    assert "public.sales_aggregate" in impact.downstream_affected
    
    # Blast radius should be > 0 since there are downstream tables
    assert impact.blast_radius_score > 0


def test_distance_score_calculation(sqlite_engine_with_lineage):
    """Test distance score calculation."""
    analyzer = LineageAnalyzer(sqlite_engine_with_lineage)
    
    # Direct parent (distance=1)
    score_1 = analyzer._calculate_distance_score(1)
    assert score_1 > 0.5
    
    # 2 hops away
    score_2 = analyzer._calculate_distance_score(2)
    assert 0.3 < score_2 < score_1
    
    # 5 hops away
    score_5 = analyzer._calculate_distance_score(5)
    assert 0 < score_5 < score_2
    
    # Same table (distance=0)
    score_0 = analyzer._calculate_distance_score(0)
    assert score_0 == 1.0


def test_temporal_score_for_upstream_anomaly(sqlite_engine_with_lineage):
    """Test temporal scoring for upstream anomalies."""
    analyzer = LineageAnalyzer(sqlite_engine_with_lineage, lookback_window_hours=24)
    
    downstream_time = datetime.utcnow()
    
    # Upstream anomaly 1 hour before
    upstream_time_1h = downstream_time - timedelta(hours=1)
    score_1h = analyzer._calculate_temporal_score(upstream_time_1h, downstream_time)
    assert score_1h > 0.9
    
    # Upstream anomaly 6 hours before
    upstream_time_6h = downstream_time - timedelta(hours=6)
    score_6h = analyzer._calculate_temporal_score(upstream_time_6h, downstream_time)
    assert 0.3 < score_6h < score_1h
    
    # Upstream anomaly after downstream (shouldn't happen)
    upstream_time_after = downstream_time + timedelta(hours=1)
    score_after = analyzer._calculate_temporal_score(upstream_time_after, downstream_time)
    assert score_after == 0.0
    
    # Upstream anomaly too long ago
    upstream_time_old = downstream_time - timedelta(hours=30)
    score_old = analyzer._calculate_temporal_score(upstream_time_old, downstream_time)
    assert score_old == 0.0


def test_find_common_ancestors(sqlite_engine_with_lineage):
    """Test finding common ancestors for multiple tables."""
    analyzer = LineageAnalyzer(sqlite_engine_with_lineage, max_depth=5)
    
    # Both staging_data and sales_aggregate have raw_data as common ancestor
    common = analyzer.find_common_ancestors(
        ["staging_data", "sales_aggregate"],
        "public"
    )
    
    # Should find raw_data
    common_names = [table for table, _ in common]
    assert "public.raw_data" in common_names


def test_parse_table_identifier(sqlite_engine_with_lineage):
    """Test parsing table identifiers."""
    # With schema
    schema, table = LineageAnalyzer._parse_table_identifier("public.users")
    assert schema == "public"
    assert table == "users"
    
    # Without schema
    schema, table = LineageAnalyzer._parse_table_identifier("users")
    assert schema is None
    assert table == "users"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
