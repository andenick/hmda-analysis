"""
Banks Analysis Module
====================

This module provides comprehensive tools for analyzing systemically important
US banks using HMDA data, including identification, ranking, and detailed
analysis of lending patterns and market concentration.

Modules:
    systemic_banks: Main analyzer for identifying systemic banks
    bank_metrics: Comprehensive metrics calculator for banks
"""

from .systemic_banks import SystemicBanksAnalyzer
from .bank_metrics import BankMetricsCalculator

__version__ = "1.0.0"
__author__ = "HMDA Analysis Team"

__all__ = [
    "SystemicBanksAnalyzer",
    "BankMetricsCalculator"
]
