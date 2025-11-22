"""
Baselinr - Modern data profiling and drift detection framework.

Baselinr automatically profiles datasets, stores metadata and statistics,
and prepares for drift detection across SQL-based data warehouses.
"""

try:
    from ._version import version as __version__
except ImportError:
    # Fallback for development installs without setuptools-scm or before first build
    __version__ = "0.1.0.dev0"

__author__ = "Baselinr Contributors"

# Main SDK client
from .client import BaselinrClient

# Key data classes for programmatic use
from .drift.detector import ColumnDrift, DriftReport
from .planner import ProfilingPlan, TablePlan
from .profiling.core import ProfilingResult

__all__ = [
    "__version__",
    "__author__",
    # SDK client
    "BaselinrClient",
    # Data classes
    "ProfilingPlan",
    "TablePlan",
    "ProfilingResult",
    "DriftReport",
    "ColumnDrift",
]
