"""
Storage layer for learned expectations.

Handles persistence and retrieval of learned expectations from the database.
"""

import json
import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from ..config.schema import StorageConfig
from .expectation_learner import LearnedExpectation

logger = logging.getLogger(__name__)


class ExpectationStorage:
    """
    Stores and retrieves learned expectations.

    Provides CRUD operations for learned expectations in the database.

    Example:
        >>> storage = ExpectationStorage(storage_config, engine)
        >>> expectation = learner.learn_expectations(...)
        >>> if expectation:
        ...     storage.save_expectation(expectation)
        >>>
        >>> # Retrieve later
        >>> retrieved = storage.get_expectation(
        ...     table_name="users",
        ...     column_name="age",
        ...     metric_name="mean"
        ... )
    """

    def __init__(self, storage_config: StorageConfig, engine: Engine):
        """
        Initialize expectation storage.

        Args:
            storage_config: Storage configuration
            engine: Database engine
        """
        self.storage_config = storage_config
        self.engine = engine
        self.expectations_table = "baselinr_expectations"

    def save_expectation(self, expectation: LearnedExpectation):
        """
        Save or update a learned expectation.

        Args:
            expectation: LearnedExpectation to save
        """
        # Check if expectation exists
        existing = self.get_expectation(
            expectation.table_name,
            expectation.column_name,
            expectation.metric_name,
            expectation.schema_name,
        )

        if existing:
            # Update
            self._update_expectation(expectation)
        else:
            # Insert
            self._insert_expectation(expectation)

    def get_expectation(
        self,
        table_name: str,
        column_name: str,
        metric_name: str,
        schema_name: Optional[str] = None,
    ) -> Optional[LearnedExpectation]:
        """
        Retrieve a learned expectation.

        Args:
            table_name: Name of the table
            column_name: Name of the column
            metric_name: Name of the metric
            schema_name: Optional schema name

        Returns:
            LearnedExpectation or None if not found
        """
        schema_filter = ""
        if schema_name:
            schema_filter = "AND schema_name = :schema_name"
        else:
            schema_filter = "AND (schema_name IS NULL OR schema_name = :schema_name)"

        query = text(
            f"""
            SELECT * FROM {self.expectations_table}
            WHERE table_name = :table_name
            AND column_name = :column_name
            AND metric_name = :metric_name
            {schema_filter}
            LIMIT 1
        """
        )

        params = {
            "table_name": table_name,
            "column_name": column_name,
            "metric_name": metric_name,
            "schema_name": schema_name,
        }

        with self.engine.connect() as conn:
            result = conn.execute(query, params).fetchone()
            if not result:
                return None

            return self._row_to_expectation(result)

    def _insert_expectation(self, expectation: LearnedExpectation):
        """Insert a new expectation."""
        query = text(
            f"""
            INSERT INTO {self.expectations_table}
            (table_name, schema_name, column_name, metric_name, column_type,
             expected_mean, expected_variance, expected_stddev, expected_min, expected_max,
             lower_control_limit, upper_control_limit, lcl_method, ucl_method,
             ewma_value, ewma_lambda,
             distribution_type, distribution_params,
             category_distribution,
             sample_size, learning_window_days, last_updated, expectation_version)
            VALUES
            (:table_name, :schema_name, :column_name, :metric_name, :column_type,
             :expected_mean, :expected_variance, :expected_stddev, :expected_min, :expected_max,
             :lower_control_limit, :upper_control_limit, :lcl_method, :ucl_method,
             :ewma_value, :ewma_lambda,
             :distribution_type, :distribution_params,
             :category_distribution,
             :sample_size, :learning_window_days, :last_updated, :expectation_version)
        """
        )

        params = self._expectation_to_params(expectation)

        with self.engine.connect() as conn:
            conn.execute(query, params)
            conn.commit()

    def _update_expectation(self, expectation: LearnedExpectation):
        """Update an existing expectation."""
        schema_filter = ""
        if expectation.schema_name:
            schema_filter = "AND schema_name = :schema_name"
        else:
            schema_filter = "AND (schema_name IS NULL OR schema_name = :schema_name)"

        query = text(
            f"""
            UPDATE {self.expectations_table}
            SET column_type = :column_type,
                expected_mean = :expected_mean,
                expected_variance = :expected_variance,
                expected_stddev = :expected_stddev,
                expected_min = :expected_min,
                expected_max = :expected_max,
                lower_control_limit = :lower_control_limit,
                upper_control_limit = :upper_control_limit,
                lcl_method = :lcl_method,
                ucl_method = :ucl_method,
                ewma_value = :ewma_value,
                ewma_lambda = :ewma_lambda,
                distribution_type = :distribution_type,
                distribution_params = :distribution_params,
                category_distribution = :category_distribution,
                sample_size = :sample_size,
                learning_window_days = :learning_window_days,
                last_updated = :last_updated,
                expectation_version = expectation_version + 1
            WHERE table_name = :table_name
            AND column_name = :column_name
            AND metric_name = :metric_name
            {schema_filter}
        """
        )

        params = self._expectation_to_params(expectation)

        with self.engine.connect() as conn:
            conn.execute(query, params)
            conn.commit()

    def _expectation_to_params(self, expectation: LearnedExpectation) -> dict:
        """Convert expectation to database parameters."""
        return {
            "table_name": expectation.table_name,
            "schema_name": expectation.schema_name,
            "column_name": expectation.column_name,
            "metric_name": expectation.metric_name,
            "column_type": expectation.column_type,
            "expected_mean": expectation.expected_mean,
            "expected_variance": expectation.expected_variance,
            "expected_stddev": expectation.expected_stddev,
            "expected_min": expectation.expected_min,
            "expected_max": expectation.expected_max,
            "lower_control_limit": expectation.lower_control_limit,
            "upper_control_limit": expectation.upper_control_limit,
            "lcl_method": expectation.lcl_method,
            "ucl_method": expectation.ucl_method,
            "ewma_value": expectation.ewma_value,
            "ewma_lambda": expectation.ewma_lambda,
            "distribution_type": expectation.distribution_type,
            "distribution_params": (
                json.dumps(expectation.distribution_params)
                if expectation.distribution_params
                else None
            ),
            "category_distribution": (
                json.dumps(expectation.category_distribution)
                if expectation.category_distribution
                else None
            ),
            "sample_size": expectation.sample_size,
            "learning_window_days": expectation.learning_window_days,
            "last_updated": expectation.last_updated,
            "expectation_version": expectation.expectation_version,
        }

    def _row_to_expectation(self, row) -> LearnedExpectation:
        """Convert database row to LearnedExpectation."""
        expectation = LearnedExpectation(
            table_name=row.table_name,
            schema_name=row.schema_name,
            column_name=row.column_name,
            metric_name=row.metric_name,
            column_type=row.column_type,
            expected_mean=row.expected_mean,
            expected_variance=row.expected_variance,
            expected_stddev=row.expected_stddev,
            expected_min=row.expected_min,
            expected_max=row.expected_max,
            lower_control_limit=row.lower_control_limit,
            upper_control_limit=row.upper_control_limit,
            lcl_method=row.lcl_method,
            ucl_method=row.ucl_method,
            ewma_value=row.ewma_value,
            ewma_lambda=row.ewma_lambda or 0.2,
            distribution_type=row.distribution_type,
            distribution_params=(
                json.loads(row.distribution_params) if row.distribution_params else None
            ),
            category_distribution=(
                json.loads(row.category_distribution) if row.category_distribution else None
            ),
            sample_size=row.sample_size,
            learning_window_days=row.learning_window_days,
            last_updated=row.last_updated,
            expectation_version=row.expectation_version,
        )
        return expectation
