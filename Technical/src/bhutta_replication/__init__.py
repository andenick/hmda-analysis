# Bhutta (2011) CRA Replication Module
"""
Implementation of Bhutta (2011) "The Community Reinvestment Act and Mortgage
Lending to Lower Income Borrowers and Neighborhoods" for replication and extension.

Key components:
- Sample construction with exact Bhutta filters
- RD estimation with multiple bandwidth specifications
- Comparison with alternative specifications
"""

from .sample_construction import BhuttaSampleConstructor
from .rd_estimation import BhuttaRDEstimator
from .diagnostics import run_specification_comparison

__all__ = [
    "BhuttaSampleConstructor",
    "BhuttaRDEstimator",
    "run_specification_comparison",
]
