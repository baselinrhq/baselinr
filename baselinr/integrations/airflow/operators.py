"""
Airflow operators for Baselinr profiling and drift detection.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from airflow.operators.python import PythonOperator as _PythonOperator
else:
    _PythonOperator = None

try:
    from airflow.operators.python import PythonOperator

    AIRFLOW_AVAILABLE = True
except ImportError:
    AIRFLOW_AVAILABLE = False
    # Create a dummy base class when Airflow is not available

    class PythonOperator:  # type: ignore[no-redef]
        """Dummy base class when Airflow is not available."""

        def __init__(self, *args, **kwargs):
            # Check if AIRFLOW_AVAILABLE was patched to True (for testing)
            import baselinr.integrations.airflow.operators as ops_module

            if not getattr(ops_module, "AIRFLOW_AVAILABLE", False):
                raise ImportError(
                    "Airflow is not installed. Install with: pip install apache-airflow"
                )
            # If AIRFLOW_AVAILABLE is True (patched), allow initialization
            # Store kwargs for potential use
            self.task_id = kwargs.get("task_id")
            self.python_callable = kwargs.get("python_callable")


class BaselinrProfileOperator(PythonOperator):
    """
    Airflow operator for running Baselinr profiling.

    This operator wraps the BaselinrClient.profile() method and can be used
    in Airflow DAGs to profile tables. Results are returned via XCom.

    Example:
        >>> from baselinr.integrations.airflow import BaselinrProfileOperator
        >>>
        >>> profile_task = BaselinrProfileOperator(
        ...     task_id="profile_tables",
        ...     config_path="/path/to/config.yml",
        ...     table_patterns=[{"pattern": "customers_*"}],
        ...     dry_run=False,
        ... )
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        table_patterns: Optional[List[Dict[str, Any]]] = None,
        dry_run: bool = False,
        **kwargs,
    ):
        """
        Initialize Baselinr profile operator.

        Args:
            config_path: Path to Baselinr configuration file (YAML or JSON)
            config: Baselinr configuration dictionary (alternative to config_path)
            table_patterns: Optional list of table patterns to profile.
                          If not provided, uses patterns from config.
            dry_run: If True, profile but don't write to storage
            **kwargs: Additional arguments passed to PythonOperator
        """
        if not AIRFLOW_AVAILABLE:
            raise ImportError("Airflow is not installed. Install with: pip install apache-airflow")

        if config_path and config:
            raise ValueError("Provide either config_path or config, not both")
        if not config_path and not config:
            raise ValueError("Provide either config_path or config")

        self.config_path = config_path
        self.config = config
        self.table_patterns = table_patterns
        self.dry_run = dry_run

        # Create the Python callable
        python_callable = self._create_profile_callable()

        # Initialize parent with the callable
        super().__init__(python_callable=python_callable, **kwargs)

    def _create_profile_callable(self):
        """Create the Python callable for profiling."""

        def profile_tables(**context: Any) -> Dict[str, Any]:
            """
            Execute profiling and return results via XCom.

            Args:
                **context: Airflow context dictionary

            Returns:
                Dictionary with run_id and profiling summary
            """
            from baselinr import BaselinrClient
            from baselinr.config.schema import TablePattern

            # Initialize client
            if self.config_path:
                client = BaselinrClient(config_path=self.config_path)
            else:
                client = BaselinrClient(config=self.config)

            # Convert table_patterns to TablePattern objects if provided
            table_pattern_objs = None
            if self.table_patterns:
                table_pattern_objs = [
                    TablePattern(**pattern) if isinstance(pattern, dict) else pattern
                    for pattern in self.table_patterns
                ]

            # Run profiling
            try:
                results = client.profile(table_patterns=table_pattern_objs, dry_run=self.dry_run)

                # Extract summary information
                run_ids = []
                tables_profiled = set()
                for result in results:
                    if hasattr(result, "run_id") and result.run_id:
                        run_ids.append(result.run_id)
                    if hasattr(result, "dataset_name") and result.dataset_name:
                        tables_profiled.add(result.dataset_name)

                summary = {
                    "run_ids": run_ids,
                    "tables_profiled": list(tables_profiled),
                    "tables_count": len(tables_profiled),
                    "results_count": len(results),
                }

                logger.info(
                    f"Baselinr profiling completed: {len(tables_profiled)} tables, "
                    f"{len(run_ids)} run IDs"
                )

                return summary

            except Exception as e:
                logger.error(f"Baselinr profiling failed: {e}", exc_info=True)
                raise

        return profile_tables


class BaselinrDriftOperator(PythonOperator):
    """
    Airflow operator for detecting drift with Baselinr.

    This operator wraps the BaselinrClient.detect_drift() method and can be used
    in Airflow DAGs to detect drift. Results are returned via XCom.

    Example:
        >>> from baselinr.integrations.airflow import BaselinrDriftOperator
        >>>
        >>> drift_task = BaselinrDriftOperator(
        ...     task_id="detect_drift",
        ...     config_path="/path/to/config.yml",
        ...     dataset_name="customers",
        ...     fail_on_drift=True,
        ... )
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        dataset_name: str = "",
        schema_name: Optional[str] = None,
        baseline_run_id: Optional[str] = None,
        current_run_id: Optional[str] = None,
        fail_on_drift: bool = False,
        fail_on_severity: Optional[str] = None,  # low, medium, high
        **kwargs,
    ):
        """
        Initialize Baselinr drift operator.

        Args:
            config_path: Path to Baselinr configuration file (YAML or JSON)
            config: Baselinr configuration dictionary (alternative to config_path)
            dataset_name: Name of the dataset/table to check for drift
            schema_name: Optional schema name
            baseline_run_id: Optional run ID to use as baseline
                           (default: auto-selected based on strategy)
            current_run_id: Optional run ID to compare against baseline
                          (default: latest run)
            fail_on_drift: If True, raise exception if any drift is detected
            fail_on_severity: If set, only fail on drift of this severity or higher
                            (low, medium, high). If None, uses fail_on_drift flag.
            **kwargs: Additional arguments passed to PythonOperator
        """
        if not AIRFLOW_AVAILABLE:
            raise ImportError("Airflow is not installed. Install with: pip install apache-airflow")

        if config_path and config:
            raise ValueError("Provide either config_path or config, not both")
        if not config_path and not config:
            raise ValueError("Provide either config_path or config")
        if not dataset_name:
            raise ValueError("dataset_name is required")

        self.config_path = config_path
        self.config = config
        self.dataset_name = dataset_name
        self.schema_name = schema_name
        self.baseline_run_id = baseline_run_id
        self.current_run_id = current_run_id
        self.fail_on_drift = fail_on_drift
        self.fail_on_severity = fail_on_severity

        # Create the Python callable
        python_callable = self._create_drift_callable()

        # Initialize parent with the callable
        super().__init__(python_callable=python_callable, **kwargs)

    def _create_drift_callable(self):
        """Create the Python callable for drift detection."""

        def detect_drift(**context: Any) -> Dict[str, Any]:
            """
            Execute drift detection and return results via XCom.

            Args:
                **context: Airflow context dictionary

            Returns:
                Dictionary with drift report summary

            Raises:
                ValueError: If fail_on_drift is True and drift is detected
            """
            from baselinr import BaselinrClient

            # Initialize client
            if self.config_path:
                client = BaselinrClient(config_path=self.config_path)
            else:
                client = BaselinrClient(config=self.config)

            # Detect drift
            try:
                report = client.detect_drift(
                    dataset_name=self.dataset_name,
                    baseline_run_id=self.baseline_run_id,
                    current_run_id=self.current_run_id,
                    schema_name=self.schema_name,
                )

                # Extract summary information
                column_drifts = getattr(report, "column_drifts", [])
                schema_changes = getattr(report, "schema_changes", [])
                has_drift = len(column_drifts) > 0 or len(schema_changes) > 0

                # Count drifts by severity
                severity_counts = {"low": 0, "medium": 0, "high": 0}
                for drift in column_drifts:
                    severity = getattr(drift, "severity", "low")
                    if severity in severity_counts:
                        severity_counts[severity] += 1

                summary = {
                    "has_drift": has_drift,
                    "column_drifts_count": len(column_drifts),
                    "schema_changes_count": len(schema_changes),
                    "severity_counts": severity_counts,
                    "drift_report": report.to_dict() if hasattr(report, "to_dict") else {},
                }

                logger.info(
                    f"Baselinr drift detection completed for {self.dataset_name}: "
                    f"{len(column_drifts)} column drifts, {len(schema_changes)} schema changes"
                )

                # Check if we should fail
                should_fail = False
                if self.fail_on_drift and has_drift:
                    should_fail = True
                elif self.fail_on_severity:
                    # Check if any drift matches the severity threshold
                    severity_order = {"low": 1, "medium": 2, "high": 3}
                    threshold = severity_order.get(self.fail_on_severity, 0)
                    for severity, count in severity_counts.items():
                        if count > 0 and severity_order.get(severity, 0) >= threshold:
                            should_fail = True
                            break

                if should_fail:
                    error_msg = (
                        f"Drift detected in {self.dataset_name}: "
                        f"{len(column_drifts)} column drifts, "
                        f"{len(schema_changes)} schema changes. "
                        f"Severity breakdown: {severity_counts}"
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                return summary

            except Exception as e:
                logger.error(f"Baselinr drift detection failed: {e}", exc_info=True)
                raise

        return detect_drift


class BaselinrQueryOperator(PythonOperator):
    """
    Airflow operator for querying Baselinr metadata.

    This operator wraps various BaselinrClient query methods and can be used
    to query runs, drift events, table history, etc.

    Example:
        >>> from baselinr.integrations.airflow import BaselinrQueryOperator
        >>>
        >>> query_task = BaselinrQueryOperator(
        ...     task_id="query_runs",
        ...     config_path="/path/to/config.yml",
        ...     query_type="runs",
        ...     days=7,
        ... )
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        query_type: str = "runs",  # runs, drift, table_history, run_details
        **kwargs,
    ):
        """
        Initialize Baselinr query operator.

        Args:
            config_path: Path to Baselinr configuration file (YAML or JSON)
            config: Baselinr configuration dictionary (alternative to config_path)
            query_type: Type of query to execute (runs, drift, table_history, run_details)
            **kwargs: Additional arguments passed to PythonOperator and query method.
                     Query-specific args (table, run_id, schema, days, limit, offset, etc.)
                     are extracted and passed to the query method.
        """
        if not AIRFLOW_AVAILABLE:
            raise ImportError("Airflow is not installed. Install with: pip install apache-airflow")

        if config_path and config:
            raise ValueError("Provide either config_path or config, not both")
        if not config_path and not config:
            raise ValueError("Provide either config_path or config")

        valid_query_types = ["runs", "drift", "table_history", "run_details"]
        if query_type not in valid_query_types:
            raise ValueError(f"query_type must be one of {valid_query_types}, got: {query_type}")

        # Extract query-specific kwargs from kwargs
        query_kwarg_names = [
            "table",
            "run_id",
            "schema",
            "days",
            "limit",
            "offset",
            "status",
            "environment",
            "severity",
            "dataset_name",
        ]
        self.query_kwargs = {k: v for k, v in kwargs.items() if k in query_kwarg_names}
        operator_kwargs = {k: v for k, v in kwargs.items() if k not in query_kwarg_names}

        self.config_path = config_path
        self.config = config
        self.query_type = query_type

        # Create the Python callable
        python_callable = self._create_query_callable()

        # Initialize parent with the callable
        super().__init__(python_callable=python_callable, **operator_kwargs)

    def _create_query_callable(self):
        """Create the Python callable for querying."""

        def query_metadata(**context: Any) -> Any:
            """
            Execute query and return results via XCom.

            Args:
                **context: Airflow context dictionary

            Returns:
                Query results (format depends on query_type)
            """
            from baselinr import BaselinrClient

            # Initialize client
            if self.config_path:
                client = BaselinrClient(config_path=self.config_path)
            else:
                client = BaselinrClient(config=self.config)

            try:
                # Execute query based on type
                if self.query_type == "runs":
                    runs = client.query_runs(**self.query_kwargs)
                    # Convert RunSummary objects to dicts for XCom
                    return [r.to_dict() if hasattr(r, "to_dict") else r for r in runs]

                elif self.query_type == "drift":
                    return client.query_drift(**self.query_kwargs)

                elif self.query_type == "table_history":
                    if "table" not in self.query_kwargs:
                        raise ValueError("table parameter required for table_history query")
                    return client.query_table_history(**self.query_kwargs)

                elif self.query_type == "run_details":
                    if "run_id" not in self.query_kwargs:
                        raise ValueError("run_id parameter required for run_details query")
                    return client.query_run_details(**self.query_kwargs)

                else:
                    raise ValueError(f"Unknown query_type: {self.query_type}")

            except Exception as e:
                logger.error(f"Baselinr query failed: {e}", exc_info=True)
                raise

        return query_metadata
