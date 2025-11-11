"""
Column-level metrics calculator for ProfileMesh.

Computes various statistical metrics for database columns
including counts, distributions, and histograms.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy import select, func, column, cast, Float, Integer, distinct
from sqlalchemy.engine import Engine
from sqlalchemy import Table
import logging
import json

logger = logging.getLogger(__name__)


class MetricCalculator:
    """Calculates column-level profiling metrics."""
    
    def __init__(
        self,
        engine: Engine,
        max_distinct_values: int = 1000,
        compute_histograms: bool = True,
        histogram_bins: int = 10
    ):
        """
        Initialize metric calculator.
        
        Args:
            engine: SQLAlchemy engine
            max_distinct_values: Maximum distinct values to compute
            compute_histograms: Whether to compute histograms
            histogram_bins: Number of histogram bins
        """
        self.engine = engine
        self.max_distinct_values = max_distinct_values
        self.compute_histograms = compute_histograms
        self.histogram_bins = histogram_bins
    
    def calculate_all_metrics(
        self,
        table: Table,
        column_name: str,
        sample_ratio: float = 1.0
    ) -> Dict[str, Any]:
        """
        Calculate all metrics for a column.
        
        Args:
            table: SQLAlchemy Table object
            column_name: Name of the column to profile
            sample_ratio: Sampling ratio (0.0 to 1.0)
            
        Returns:
            Dictionary of metric_name -> metric_value
        """
        col = table.c[column_name]
        metrics = {}
        
        # Basic counts
        metrics.update(self._calculate_counts(table, col, sample_ratio))
        
        # Type-specific metrics
        col_type = str(col.type)
        
        if self._is_numeric_type(col_type):
            metrics.update(self._calculate_numeric_metrics(table, col, sample_ratio))
            if self.compute_histograms:
                metrics.update(self._calculate_histogram(table, col, sample_ratio))
        
        if self._is_string_type(col_type):
            metrics.update(self._calculate_string_metrics(table, col, sample_ratio))
        
        return metrics
    
    def _calculate_counts(
        self,
        table: Table,
        col,
        sample_ratio: float
    ) -> Dict[str, Any]:
        """Calculate basic count metrics."""
        with self.engine.connect() as conn:
            # Build query with optional sampling
            query = select(
                func.count().label('count'),
                func.count(col).label('non_null_count'),
                func.count(distinct(col)).label('distinct_count')
            ).select_from(table)
            
            if sample_ratio < 1.0:
                # Note: Sampling syntax varies by database
                # This is a simplified version
                pass
            
            result = conn.execute(query).fetchone()
            
            total_count = result.count
            non_null_count = result.non_null_count
            null_count = total_count - non_null_count
            distinct_count = result.distinct_count
            
            return {
                'count': total_count,
                'null_count': null_count,
                'null_percent': (null_count / total_count * 100) if total_count > 0 else 0,
                'distinct_count': distinct_count,
                'distinct_percent': (distinct_count / total_count * 100) if total_count > 0 else 0
            }
    
    def _calculate_numeric_metrics(
        self,
        table: Table,
        col,
        sample_ratio: float
    ) -> Dict[str, Any]:
        """Calculate numeric metrics (min, max, mean, stddev)."""
        with self.engine.connect() as conn:
            # Cast to float for calculations
            col_float = cast(col, Float)
            
            query = select(
                func.min(col).label('min'),
                func.max(col).label('max'),
                func.avg(col_float).label('mean'),
                func.stddev(col_float).label('stddev')
            ).select_from(table)
            
            result = conn.execute(query).fetchone()
            
            return {
                'min': result.min,
                'max': result.max,
                'mean': float(result.mean) if result.mean is not None else None,
                'stddev': float(result.stddev) if result.stddev is not None else None
            }
    
    def _calculate_histogram(
        self,
        table: Table,
        col,
        sample_ratio: float
    ) -> Dict[str, Any]:
        """Calculate histogram for numeric columns."""
        try:
            with self.engine.connect() as conn:
                # Get min and max
                query = select(func.min(col), func.max(col)).select_from(table)
                result = conn.execute(query).fetchone()
                min_val, max_val = result[0], result[1]
                
                if min_val is None or max_val is None:
                    return {'histogram': None}
                
                # Calculate bin width
                bin_width = (max_val - min_val) / self.histogram_bins
                
                if bin_width == 0:
                    return {'histogram': None}
                
                # Build histogram
                histogram = []
                for i in range(self.histogram_bins):
                    bin_start = min_val + (i * bin_width)
                    bin_end = min_val + ((i + 1) * bin_width)
                    
                    # Count values in this bin
                    if i == self.histogram_bins - 1:
                        # Last bin includes upper bound
                        count_query = select(func.count()).select_from(table).where(
                            (col >= bin_start) & (col <= bin_end)
                        )
                    else:
                        count_query = select(func.count()).select_from(table).where(
                            (col >= bin_start) & (col < bin_end)
                        )
                    
                    count = conn.execute(count_query).scalar()
                    
                    histogram.append({
                        'bin_start': float(bin_start),
                        'bin_end': float(bin_end),
                        'count': count
                    })
                
                return {'histogram': json.dumps(histogram)}
        
        except Exception as e:
            logger.warning(f"Failed to calculate histogram: {e}")
            return {'histogram': None}
    
    def _calculate_string_metrics(
        self,
        table: Table,
        col,
        sample_ratio: float
    ) -> Dict[str, Any]:
        """Calculate string-specific metrics."""
        try:
            with self.engine.connect() as conn:
                query = select(
                    func.min(func.length(col)).label('min_length'),
                    func.max(func.length(col)).label('max_length'),
                    func.avg(func.length(col)).label('avg_length')
                ).select_from(table)
                
                result = conn.execute(query).fetchone()
                
                return {
                    'min_length': result.min_length,
                    'max_length': result.max_length,
                    'avg_length': float(result.avg_length) if result.avg_length is not None else None
                }
        except Exception as e:
            logger.warning(f"Failed to calculate string metrics: {e}")
            return {}
    
    @staticmethod
    def _is_numeric_type(col_type: str) -> bool:
        """Check if column type is numeric."""
        numeric_keywords = [
            'int', 'integer', 'smallint', 'bigint',
            'float', 'double', 'real', 'numeric',
            'decimal', 'number'
        ]
        col_type_lower = col_type.lower()
        return any(keyword in col_type_lower for keyword in numeric_keywords)
    
    @staticmethod
    def _is_string_type(col_type: str) -> bool:
        """Check if column type is string."""
        string_keywords = ['char', 'varchar', 'text', 'string']
        col_type_lower = col_type.lower()
        return any(keyword in col_type_lower for keyword in string_keywords)

