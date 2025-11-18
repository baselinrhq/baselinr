"""
Column-level metrics calculator for Baselinr.

Computes various statistical metrics for database columns
including counts, distributions, and histograms.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from sqlalchemy import Float, Table, cast, distinct, func, select, text
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
        enable_enrichment: bool = True,
        enable_approx_distinct: bool = True,
        enable_type_inference: bool = True,
        type_inference_sample_size: int = 1000,
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
            enable_enrichment: Enable profiling enrichment features
            enable_approx_distinct: Enable approximate distinct count
            enable_type_inference: Enable data type inference
            type_inference_sample_size: Sample size for type inference
        """
        self.engine = engine
        self.max_distinct_values = max_distinct_values
        self.compute_histograms = compute_histograms
        self.histogram_bins = histogram_bins
        self.enabled_metrics = enabled_metrics
        self.query_builder = query_builder
        self.enable_enrichment = enable_enrichment
        self.enable_approx_distinct = enable_approx_distinct
        self.enable_type_inference = enable_type_inference
        self.type_inference_sample_size = type_inference_sample_size

        # Detect database type from engine URL
        self.database_type = self._detect_database_type()

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
            [
                "count",
                "null_count",
                "null_ratio",
                "distinct_count",
                "unique_ratio",
                "approx_distinct_count",
            ]
        )
        compute_numeric = self._should_compute_metric_group(["min", "max", "mean", "stddev"])
        compute_histogram = self._should_compute_metric("histogram") and self.compute_histograms
        compute_string = self._should_compute_metric_group(
            ["min_length", "max_length", "avg_length"]
        )
        compute_generic_minmax = self._should_compute_metric_group(["min", "max"])

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

        # Generic min/max for all types (if not already computed for numeric)
        if not self._is_numeric_type(col_type) and compute_generic_minmax:
            generic_minmax = self._calculate_generic_minmax(
                table, col, partition_config, sampling_config
            )
            if self.enabled_metrics:
                generic_minmax = {
                    k: v for k, v in generic_minmax.items() if k in self.enabled_metrics
                }
            metrics.update(generic_minmax)

        # Data type inference (if enabled)
        if self.enable_enrichment and self.enable_type_inference:
            if self._should_compute_metric("data_type_inferred"):
                inferred_type = self._infer_data_type(table, col, partition_config, sampling_config)
                if inferred_type:
                    metrics["data_type_inferred"] = inferred_type

        # Approximate distinct count (if enabled)
        if self.enable_enrichment and self.enable_approx_distinct:
            if self._should_compute_metric("approx_distinct_count"):
                approx_distinct = self._calculate_approx_distinct(
                    table, col, partition_config, sampling_config
                )
                if approx_distinct is not None:
                    metrics["approx_distinct_count"] = approx_distinct

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

            if result is None:
                return {
                    "count": 0,
                    "null_count": 0,
                    "null_ratio": 0.0,
                    "distinct_count": 0,
                    "unique_ratio": 0.0,
                }

            total_count = int(result[0]) if result[0] is not None else 0
            non_null_count = int(result[1]) if result[1] is not None else 0
            null_count = total_count - non_null_count
            distinct_count_val = int(result[2]) if result[2] is not None else 0

            return {
                "count": total_count,
                "null_count": null_count,
                "null_ratio": (null_count / total_count) if total_count > 0 else 0.0,
                "distinct_count": distinct_count_val,
                "unique_ratio": (distinct_count_val / total_count) if total_count > 0 else 0.0,
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

            if result is None:
                return {
                    "min": None,
                    "max": None,
                    "mean": None,
                    "stddev": None,
                }

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
                if result is None:
                    min_val, max_val = None, None
                else:
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

                if result is None:
                    return {
                        "min_length": None,
                        "max_length": None,
                        "avg_length": None,
                    }

                return {
                    "min_length": result.min_length if result.min_length is not None else None,
                    "max_length": result.max_length if result.max_length is not None else None,
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

    def _detect_database_type(self) -> str:
        """Detect database type from engine URL."""
        url_str = str(self.engine.url)
        if "postgresql" in url_str or "postgres" in url_str:
            return "postgres"
        elif "snowflake" in url_str:
            return "snowflake"
        elif "mysql" in url_str:
            return "mysql"
        elif "bigquery" in url_str or "bigquery+" in url_str:
            return "bigquery"
        elif "redshift" in url_str:
            return "redshift"
        elif "sqlite" in url_str:
            return "sqlite"
        else:
            return "unknown"

    def _calculate_approx_distinct(
        self,
        table: Table,
        col,
        partition_config: Optional[PartitionConfig],
        sampling_config: Optional[SamplingConfig],
    ) -> Optional[int]:
        """Calculate approximate distinct count using database-specific functions."""
        try:
            with self.engine.connect() as conn:
                # Build base query with partition filtering
                if self.query_builder:
                    base_query, _ = self.query_builder.build_profiling_query(
                        table=table,
                        partition_config=partition_config,
                        sampling_config=sampling_config,
                    )
                    subquery = base_query.alias("filtered")
                    col_ref = subquery.c[col.name]
                else:
                    col_ref = col

                # Use database-specific approximate functions
                if self.database_type == "snowflake":
                    # Snowflake: APPROX_COUNT_DISTINCT
                    if self.query_builder:
                        query = select(
                            func.count(distinct(col_ref)).label("approx_distinct")
                        ).select_from(subquery)
                    else:
                        query = select(
                            func.count(distinct(col)).label("approx_distinct")
                        ).select_from(table)
                    # Try to use APPROX_COUNT_DISTINCT if available (requires raw SQL)
                    try:
                        if self.query_builder:
                            compiled_query = str(
                                base_query.compile(compile_kwargs={"literal_binds": True})
                            )
                            sql_query = text(
                                f"SELECT APPROX_COUNT_DISTINCT({col.name}) "
                                f"as approx_distinct FROM ({compiled_query})"
                            )
                        else:
                            sql_query = text(
                                f"SELECT APPROX_COUNT_DISTINCT({col.name}) "
                                f"as approx_distinct FROM {table.fullname}"
                            )
                        result = conn.execute(sql_query).fetchone()
                        if result and result[0] is not None:
                            return int(result[0])
                    except Exception:
                        # Fall back to exact count
                        pass
                    # Use exact count as fallback
                    result = conn.execute(query).fetchone()
                    return int(result[0]) if result and result[0] is not None else None

                elif self.database_type == "bigquery":
                    # BigQuery: APPROX_COUNT_DISTINCT
                    try:
                        if self.query_builder:
                            compiled_query = str(
                                base_query.compile(compile_kwargs={"literal_binds": True})
                            )
                            sql_query = text(
                                f"SELECT APPROX_COUNT_DISTINCT({col.name}) "
                                f"as approx_distinct FROM ({compiled_query})"
                            )
                        else:
                            table_ref = (
                                f"`{table.schema}.{table.name}`"
                                if table.schema
                                else f"`{table.name}`"
                            )
                            sql_query = text(
                                f"SELECT APPROX_COUNT_DISTINCT({col.name}) "
                                f"as approx_distinct FROM {table_ref}"
                            )
                        result = conn.execute(sql_query).fetchone()
                        if result and result[0] is not None:
                            return int(result[0])
                    except Exception:
                        pass
                    # Fall back to exact count
                    if self.query_builder:
                        query = select(
                            func.count(distinct(col_ref)).label("approx_distinct")
                        ).select_from(subquery)
                    else:
                        query = select(
                            func.count(distinct(col)).label("approx_distinct")
                        ).select_from(table)
                    result = conn.execute(query).fetchone()
                    return int(result[0]) if result and result[0] is not None else None

                elif self.database_type == "redshift":
                    # Redshift: APPROXIMATE COUNT(DISTINCT)
                    try:
                        if self.query_builder:
                            compiled_query = str(
                                base_query.compile(compile_kwargs={"literal_binds": True})
                            )
                            sql_query = text(
                                f"SELECT APPROXIMATE COUNT(DISTINCT {col.name}) "
                                f"as approx_distinct FROM ({compiled_query})"
                            )
                        else:
                            sql_query = text(
                                f"SELECT APPROXIMATE COUNT(DISTINCT {col.name}) "
                                f"as approx_distinct FROM {table.fullname}"
                            )
                        result = conn.execute(sql_query).fetchone()
                        if result and result[0] is not None:
                            return int(result[0])
                    except Exception:
                        pass
                    # Fall back to exact count
                    if self.query_builder:
                        query = select(
                            func.count(distinct(col_ref)).label("approx_distinct")
                        ).select_from(subquery)
                    else:
                        query = select(
                            func.count(distinct(col)).label("approx_distinct")
                        ).select_from(table)
                    result = conn.execute(query).fetchone()
                    return int(result[0]) if result and result[0] is not None else None

                elif self.database_type == "postgres":
                    # PostgreSQL: Try to use COUNT(DISTINCT) with estimate, or exact count
                    # For now, use exact count
                    # (PostgreSQL doesn't have built-in approx count distinct)
                    if self.query_builder:
                        query = select(
                            func.count(distinct(col_ref)).label("approx_distinct")
                        ).select_from(subquery)
                    else:
                        query = select(
                            func.count(distinct(col)).label("approx_distinct")
                        ).select_from(table)
                    result = conn.execute(query).fetchone()
                    return int(result[0]) if result and result[0] is not None else None

                else:
                    # For other databases (MySQL, SQLite), use exact count
                    if self.query_builder:
                        query = select(
                            func.count(distinct(col_ref)).label("approx_distinct")
                        ).select_from(subquery)
                    else:
                        query = select(
                            func.count(distinct(col)).label("approx_distinct")
                        ).select_from(table)
                    result = conn.execute(query).fetchone()
                    return int(result[0]) if result and result[0] is not None else None

        except Exception as e:
            logger.warning(f"Failed to calculate approximate distinct count: {e}")
            return None

    def _calculate_generic_minmax(
        self,
        table: Table,
        col,
        partition_config: Optional[PartitionConfig],
        sampling_config: Optional[SamplingConfig],
    ) -> Dict[str, Any]:
        """Calculate min/max for any comparable type (strings, dates, booleans, etc.)."""
        # Check if column is boolean - PostgreSQL doesn't support min/max on booleans
        col_type = str(col.type).lower()
        boolean_keywords = ["boolean", "bool", "bit"]
        if any(keyword in col_type for keyword in boolean_keywords):
            # Booleans don't have meaningful min/max values
            return {"min": None, "max": None}

        try:
            with self.engine.connect() as conn:
                # Build base query with partition filtering
                if self.query_builder:
                    base_query, _ = self.query_builder.build_profiling_query(
                        table=table,
                        partition_config=partition_config,
                        sampling_config=sampling_config,
                    )
                    subquery = base_query.alias("filtered")
                    col_ref = subquery.c[col.name]

                    query = select(
                        func.min(col_ref).label("min"),
                        func.max(col_ref).label("max"),
                    ).select_from(subquery)
                else:
                    col_ref = col
                    query = select(
                        func.min(col).label("min"),
                        func.max(col).label("max"),
                    ).select_from(table)

                result = conn.execute(query).fetchone()

                if result is None:
                    return {
                        "min": None,
                        "max": None,
                    }

                min_val = result.min
                max_val = result.max

                # Convert to string for non-numeric types to ensure consistency
                # Numeric types are already handled in _calculate_numeric_metrics
                if not self._is_numeric_type(col_type):
                    min_val = str(min_val) if min_val is not None else None
                    max_val = str(max_val) if max_val is not None else None

                return {
                    "min": min_val,
                    "max": max_val,
                }

        except Exception as e:
            logger.warning(f"Failed to calculate generic min/max: {e}")
            return {"min": None, "max": None}

    def _infer_data_type(
        self,
        table: Table,
        col,
        partition_config: Optional[PartitionConfig],
        sampling_config: Optional[SamplingConfig],
    ) -> Optional[str]:
        """Infer data type from sample values."""
        try:
            with self.engine.connect() as conn:
                # Build base query with partition filtering
                if self.query_builder:
                    base_query, _ = self.query_builder.build_profiling_query(
                        table=table,
                        partition_config=partition_config,
                        sampling_config=sampling_config,
                    )
                    subquery = base_query.alias("filtered")
                    col_ref = subquery.c[col.name]

                    # Sample non-null values for inference
                    sample_query = (
                        select(col_ref)
                        .select_from(subquery)
                        .where(col_ref.isnot(None))
                        .limit(self.type_inference_sample_size)
                    )
                else:
                    col_ref = col
                    sample_query = (
                        select(col)
                        .select_from(table)
                        .where(col.isnot(None))
                        .limit(self.type_inference_sample_size)
                    )

                result = conn.execute(sample_query)
                sample_values = [row[0] for row in result if row[0] is not None]

                if not sample_values:
                    return None

                # Analyze patterns
                inferred_type = self._analyze_type_patterns(sample_values)
                return inferred_type

        except Exception as e:
            logger.warning(f"Failed to infer data type: {e}")
            return None

    @staticmethod
    def _analyze_type_patterns(sample_values: List[Any]) -> str:
        """Analyze sample values to infer data type."""
        if not sample_values:
            return "unknown"

        # Take a reasonable sample for analysis
        analysis_sample = sample_values[: min(100, len(sample_values))]

        # Boolean patterns
        bool_true = {"true", "false", "yes", "no", "1", "0", "t", "f", "y", "n"}
        if all(str(v).lower().strip() in bool_true for v in analysis_sample):
            return "boolean"

        # Numeric patterns
        numeric_count = 0
        for v in analysis_sample:
            try:
                float(str(v))
                numeric_count += 1
            except (ValueError, TypeError):
                pass
        if numeric_count / len(analysis_sample) > 0.8:
            # Check if integers
            int_count = 0
            for v in analysis_sample:
                try:
                    float_val = float(str(v))
                    if float_val == int(float_val):
                        int_count += 1
                except (ValueError, TypeError):
                    pass
            if int_count / len(analysis_sample) > 0.8:
                return "integer"
            return "numeric"

        # Date/timestamp patterns
        date_patterns = [
            r"^\d{4}-\d{2}-\d{2}",  # YYYY-MM-DD
            r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",  # YYYY-MM-DD HH:MM:SS
            r"^\d{2}/\d{2}/\d{4}",  # MM/DD/YYYY
            r"^\d{4}/\d{2}/\d{2}",  # YYYY/MM/DD
        ]
        date_count = 0
        for v in analysis_sample:
            v_str = str(v)
            for pattern in date_patterns:
                if re.match(pattern, v_str):
                    date_count += 1
                    break
        if date_count / len(analysis_sample) > 0.7:
            return "date"

        # Email pattern
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        email_count = sum(1 for v in analysis_sample if re.match(email_pattern, str(v)))
        if email_count / len(analysis_sample) > 0.8:
            return "email"

        # URL pattern
        url_pattern = r"^https?://"
        url_count = sum(1 for v in analysis_sample if re.match(url_pattern, str(v)))
        if url_count / len(analysis_sample) > 0.8:
            return "url"

        # UUID pattern
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        uuid_count = sum(1 for v in analysis_sample if re.match(uuid_pattern, str(v).lower()))
        if uuid_count / len(analysis_sample) > 0.8:
            return "uuid"

        # JSON pattern (basic check)
        json_count = 0
        for v in analysis_sample:
            v_str = str(v).strip()
            if (v_str.startswith("{") and v_str.endswith("}")) or (
                v_str.startswith("[") and v_str.endswith("]")
            ):
                try:
                    json.loads(v_str)
                    json_count += 1
                except (ValueError, TypeError):
                    pass
        if json_count / len(analysis_sample) > 0.7:
            return "json"

        # Default to string
        return "string"
