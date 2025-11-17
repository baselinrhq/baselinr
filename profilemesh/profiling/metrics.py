"""
Column-level metrics calculator for ProfileMesh.

Computes various statistical metrics for database columns
including counts, distributions, and histograms.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import Float, Integer, Table, cast, column, distinct, func, select
from sqlalchemy.engine import Engine

from ..config.schema import PartitionConfig, SamplingConfig

logger = logging.getLogger(__name__)


class MetricCalculator:
    """Calculates column-level profiling metrics."""

    def __init__(
        self,
        engine: Engine,
        max_distinct_values: int = 1000,
        compute_histograms: bool = True,
        histogram_bins: int = 10,
        enabled_metrics: Optional[List[str]] = None,
        query_builder=None,
    ):
        """
        Initialize metric calculator.

        Args:
            engine: SQLAlchemy engine
            max_distinct_values: Maximum distinct values to compute
            compute_histograms: Whether to compute histograms
            histogram_bins: Number of histogram bins
            enabled_metrics: List of metrics to compute (None = all metrics)
            query_builder: QueryBuilder for partition/sampling support
        """
        self.engine = engine
        self.max_distinct_values = max_distinct_values
        self.compute_histograms = compute_histograms
        self.histogram_bins = histogram_bins
        self.enabled_metrics = enabled_metrics
        self.query_builder = query_builder

    def calculate_all_metrics(
        self,
        table: Table,
        column_name: str,
        partition_config: Optional[PartitionConfig] = None,
        sampling_config: Optional[SamplingConfig] = None,
    ) -> Dict[str, Any]:
        """
        Calculate all metrics for a column.

        Args:
            table: SQLAlchemy Table object
            column_name: Name of the column to profile
            partition_config: Partition configuration (optional)
            sampling_config: Sampling configuration (optional)

        Returns:
            Dictionary of metric_name -> metric_value
        """
        col = table.c[column_name]
        metrics = {}

        # Determine which metrics to compute
        compute_counts = self._should_compute_metric_group(
            ["count", "null_count", "null_percent", "distinct_count", "distinct_percent"]
        )
        compute_numeric = self._should_compute_metric_group(["min", "max", "mean", "stddev"])
        compute_histogram = self._should_compute_metric("histogram") and self.compute_histograms
        compute_string = self._should_compute_metric_group(
            ["min_length", "max_length", "avg_length"]
        )

        # Basic counts (if any count metric is requested)
        if compute_counts:
            all_counts = self._calculate_counts(table, col, partition_config, sampling_config)
            # Filter to only requested metrics
            if self.enabled_metrics:
                all_counts = {k: v for k, v in all_counts.items() if k in self.enabled_metrics}
            metrics.update(all_counts)

        # Type-specific metrics
        col_type = str(col.type)

        if self._is_numeric_type(col_type) and compute_numeric:
            all_numeric = self._calculate_numeric_metrics(
                table, col, partition_config, sampling_config
            )
            # Filter to only requested metrics
            if self.enabled_metrics:
                all_numeric = {k: v for k, v in all_numeric.items() if k in self.enabled_metrics}
            metrics.update(all_numeric)

            if compute_histogram:
                metrics.update(
                    self._calculate_histogram(table, col, partition_config, sampling_config)
                )

        if self._is_string_type(col_type) and compute_string:
            all_string = self._calculate_string_metrics(
                table, col, partition_config, sampling_config
            )
            # Filter to only requested metrics
            if self.enabled_metrics:
                all_string = {k: v for k, v in all_string.items() if k in self.enabled_metrics}
            metrics.update(all_string)

        return metrics

    def _should_compute_metric(self, metric_name: str) -> bool:
        """Check if a specific metric should be computed."""
        if self.enabled_metrics is None:
            return True  # Compute all if not specified
        return metric_name in self.enabled_metrics

    def _should_compute_metric_group(self, metric_names: List[str]) -> bool:
        """Check if any metric in a group should be computed."""
        if self.enabled_metrics is None:
            return True  # Compute all if not specified
        return any(m in self.enabled_metrics for m in metric_names)

    def _calculate_counts(
        self,
        table: Table,
        col,
        partition_config: Optional[PartitionConfig],
        sampling_config: Optional[SamplingConfig],
    ) -> Dict[str, Any]:
        """Calculate basic count metrics."""
        with self.engine.connect() as conn:
            # Build base query with partition filtering
            if self.query_builder:
                base_query, _ = self.query_builder.build_profiling_query(
                    table=table, partition_config=partition_config, sampling_config=sampling_config
                )
                # Use subquery for counts
                subquery = base_query.alias("filtered")
                query = select(
                    func.count().label("count"),
                    func.count(subquery.c[col.name]).label("non_null_count"),
                    func.count(distinct(subquery.c[col.name])).label("distinct_count"),
                ).select_from(subquery)
            else:
                # Fallback to direct query
                query = select(
                    func.count().label("count"),
                    func.count(col).label("non_null_count"),
                    func.count(distinct(col)).label("distinct_count"),
                ).select_from(table)

            result = conn.execute(query).fetchone()

            total_count = result.count
            non_null_count = result.non_null_count
            null_count = total_count - non_null_count
            distinct_count = result.distinct_count

            return {
                "count": total_count,
                "null_count": null_count,
                "null_percent": (null_count / total_count * 100) if total_count > 0 else 0,
                "distinct_count": distinct_count,
                "distinct_percent": (distinct_count / total_count * 100) if total_count > 0 else 0,
            }

    def _calculate_numeric_metrics(
        self,
        table: Table,
        col,
        partition_config: Optional[PartitionConfig],
        sampling_config: Optional[SamplingConfig],
    ) -> Dict[str, Any]:
        """Calculate numeric metrics (min, max, mean, stddev)."""
        with self.engine.connect() as conn:
            # Build base query with partition filtering
            if self.query_builder:
                base_query, _ = self.query_builder.build_profiling_query(
                    table=table, partition_config=partition_config, sampling_config=sampling_config
                )
                subquery = base_query.alias("filtered")
                col_ref = subquery.c[col.name]
            else:
                col_ref = col

            # Cast to float for calculations
            col_float = cast(col_ref, Float)

            if self.query_builder:
                query = select(
                    func.min(col_ref).label("min"),
                    func.max(col_ref).label("max"),
                    func.avg(col_float).label("mean"),
                    func.stddev(col_float).label("stddev"),
                ).select_from(subquery)
            else:
                query = select(
                    func.min(col).label("min"),
                    func.max(col).label("max"),
                    func.avg(col_float).label("mean"),
                    func.stddev(col_float).label("stddev"),
                ).select_from(table)

            result = conn.execute(query).fetchone()

            return {
                "min": result.min,
                "max": result.max,
                "mean": float(result.mean) if result.mean is not None else None,
                "stddev": float(result.stddev) if result.stddev is not None else None,
            }

    def _calculate_histogram(
        self,
        table: Table,
        col,
        partition_config: Optional[PartitionConfig],
        sampling_config: Optional[SamplingConfig],
    ) -> Dict[str, Any]:
        """Calculate histogram for numeric columns."""
        try:
            with self.engine.connect() as conn:
                # Build base query
                if self.query_builder:
                    base_query, _ = self.query_builder.build_profiling_query(
                        table=table,
                        partition_config=partition_config,
                        sampling_config=sampling_config,
                    )
                    subquery = base_query.alias("filtered")
                    col_ref = subquery.c[col.name]

                    # Get min and max
                    query = select(func.min(col_ref), func.max(col_ref)).select_from(subquery)
                else:
                    col_ref = col
                    # Get min and max
                    query = select(func.min(col), func.max(col)).select_from(table)
                result = conn.execute(query).fetchone()
                min_val, max_val = result[0], result[1]

                if min_val is None or max_val is None:
                    return {"histogram": None}

                # Calculate bin width
                bin_width = (max_val - min_val) / self.histogram_bins

                if bin_width == 0:
                    return {"histogram": None}

                # Build histogram
                histogram = []
                for i in range(self.histogram_bins):
                    bin_start = min_val + (i * bin_width)
                    bin_end = min_val + ((i + 1) * bin_width)

                    # Count values in this bin
                    if self.query_builder:
                        if i == self.histogram_bins - 1:
                            # Last bin includes upper bound
                            count_query = (
                                select(func.count())
                                .select_from(subquery)
                                .where((col_ref >= bin_start) & (col_ref <= bin_end))
                            )
                        else:
                            count_query = (
                                select(func.count())
                                .select_from(subquery)
                                .where((col_ref >= bin_start) & (col_ref < bin_end))
                            )
                    else:
                        if i == self.histogram_bins - 1:
                            count_query = (
                                select(func.count())
                                .select_from(table)
                                .where((col >= bin_start) & (col <= bin_end))
                            )
                        else:
                            count_query = (
                                select(func.count())
                                .select_from(table)
                                .where((col >= bin_start) & (col < bin_end))
                            )

                    count = conn.execute(count_query).scalar()

                    histogram.append(
                        {"bin_start": float(bin_start), "bin_end": float(bin_end), "count": count}
                    )

                return {"histogram": json.dumps(histogram)}

        except Exception as e:
            logger.warning(f"Failed to calculate histogram: {e}")
            return {"histogram": None}

    def _calculate_string_metrics(
        self,
        table: Table,
        col,
        partition_config: Optional[PartitionConfig],
        sampling_config: Optional[SamplingConfig],
    ) -> Dict[str, Any]:
        """Calculate string-specific metrics."""
        try:
            with self.engine.connect() as conn:
                # Build base query
                if self.query_builder:
                    base_query, _ = self.query_builder.build_profiling_query(
                        table=table,
                        partition_config=partition_config,
                        sampling_config=sampling_config,
                    )
                    subquery = base_query.alias("filtered")
                    col_ref = subquery.c[col.name]

                    query = select(
                        func.min(func.length(col_ref)).label("min_length"),
                        func.max(func.length(col_ref)).label("max_length"),
                        func.avg(func.length(col_ref)).label("avg_length"),
                    ).select_from(subquery)
                else:
                    query = select(
                        func.min(func.length(col)).label("min_length"),
                        func.max(func.length(col)).label("max_length"),
                        func.avg(func.length(col)).label("avg_length"),
                    ).select_from(table)

                result = conn.execute(query).fetchone()

                return {
                    "min_length": result.min_length,
                    "max_length": result.max_length,
                    "avg_length": (
                        float(result.avg_length) if result.avg_length is not None else None
                    ),
                }
        except Exception as e:
            logger.warning(f"Failed to calculate string metrics: {e}")
            return {}

    @staticmethod
    def _is_numeric_type(col_type: str) -> bool:
        """Check if column type is numeric."""
        numeric_keywords = [
            "int",
            "integer",
            "smallint",
            "bigint",
            "float",
            "double",
            "real",
            "numeric",
            "decimal",
            "number",
        ]
        col_type_lower = col_type.lower()
        return any(keyword in col_type_lower for keyword in numeric_keywords)

    @staticmethod
    def _is_string_type(col_type: str) -> bool:
        """Check if column type is string."""
        string_keywords = ["char", "varchar", "text", "string"]
        col_type_lower = col_type.lower()
        return any(keyword in col_type_lower for keyword in string_keywords)
