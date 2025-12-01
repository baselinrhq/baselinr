"""
Base collector interface for RCA data collection.
"""

import logging
from abc import ABC, abstractmethod
from typing import List

from sqlalchemy.engine import Engine

from ..models import PipelineRun
from ..storage import RCAStorage

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """Base class for all RCA collectors."""

    def __init__(self, engine: Engine, enabled: bool = True):
        """
        Initialize collector.

        Args:
            engine: SQLAlchemy engine for storage
            enabled: Whether this collector is enabled
        """
        self.engine = engine
        self.enabled = enabled
        self.storage = RCAStorage(engine)

    @abstractmethod
    def collect(self) -> List[PipelineRun]:
        """
        Collect pipeline run data.

        Returns:
            List of PipelineRun objects
        """
        pass

    def collect_and_store(self) -> int:
        """
        Collect and store pipeline runs.

        Returns:
            Number of runs collected
        """
        if not self.enabled:
            logger.debug(f"{self.__class__.__name__} is disabled")
            return 0

        try:
            runs = self.collect()

            for run in runs:
                self.storage.write_pipeline_run(run)

            logger.info(f"{self.__class__.__name__} collected {len(runs)} runs")
            return len(runs)

        except Exception as e:
            logger.error(f"Error in {self.__class__.__name__}: {e}")
            return 0
