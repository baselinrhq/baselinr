"""
Generic pipeline run collector with factory pattern.
"""

import logging
from typing import Dict, List, Optional, Type

from sqlalchemy.engine import Engine

from .base_collector import BaseCollector

logger = logging.getLogger(__name__)


class PipelineRunCollector:
    """Factory for creating pipeline run collectors."""

    _collectors: Dict[str, Type[BaseCollector]] = {}

    @classmethod
    def register_collector(cls, pipeline_type: str, collector_class: Type[BaseCollector]):
        """
        Register a collector for a specific pipeline type.

        Args:
            pipeline_type: Type of pipeline (e.g., 'dbt', 'airflow')
            collector_class: Collector class to use
        """
        cls._collectors[pipeline_type] = collector_class
        logger.debug(f"Registered collector for pipeline type: {pipeline_type}")

    @classmethod
    def create_collector(
        cls, pipeline_type: str, engine: Engine, config: Optional[Dict] = None, **kwargs
    ) -> Optional[BaseCollector]:
        """
        Create a collector instance for the given pipeline type.

        Args:
            pipeline_type: Type of pipeline (e.g., 'dbt', 'airflow')
            engine: SQLAlchemy engine
            config: Optional configuration dict
            **kwargs: Additional arguments for collector

        Returns:
            Collector instance or None if type not registered
        """
        collector_class = cls._collectors.get(pipeline_type)

        if not collector_class:
            logger.warning(f"No collector registered for pipeline type: {pipeline_type}")
            return None

        try:
            if config:
                # Type ignore: subclasses may accept config parameter
                return collector_class(  # type: ignore[call-arg]
                    engine=engine, config=config, **kwargs
                )
            else:
                return collector_class(engine=engine, **kwargs)
        except Exception as e:
            logger.error(f"Failed to create collector for {pipeline_type}: {e}")
            return None

    @classmethod
    def get_available_collectors(cls) -> List[str]:
        """
        Get list of available collector types.

        Returns:
            List of registered pipeline types
        """
        return list(cls._collectors.keys())
