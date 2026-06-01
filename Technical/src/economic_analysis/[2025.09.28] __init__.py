"""
HMDA Economic Analysis Framework
=================================

Comprehensive framework for CRA analysis, Bhutta replication, and modern economic research.

This module provides:
- Perfect Bhutta (2011) replication capabilities
- Anderson methodology implementation
- Comparative analysis tools
- Temporal extension to modern data
- Robustness testing framework

Author: Nicholas Anderson & Claude Code
Created: 2025-09-28
Version: 1.0.0
"""

from .core import HMDAEconomicAnalysis
from .bhutta_replication import BhuttaReplicator
from .anderson_methodology import AndersonMethodology
from .comparative_analysis import ComparativeAnalyzer
from .temporal_extension import TemporalExtender
from .robustness_testing import RobustnessFramework

__version__ = "1.0.0"
__author__ = "Nicholas Anderson & Claude Code"

__all__ = [
    'HMDAEconomicAnalysis',
    'BhuttaReplicator',
    'AndersonMethodology',
    'ComparativeAnalyzer',
    'TemporalExtender',
    'RobustnessFramework'
]