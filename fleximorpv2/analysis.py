"""
Analysis module for FlexiMORPv2.

This module provides a unified interface for importing all analysis components
used by the integration example and other external scripts.
"""

# Import the core analysis classes
from .baseline_optimization import BaselineOptimization
from .uncertainty_analysis import UncertaintyAnalysis, UncertaintyResults, MonteCarloResults
from .flexible_design import FlexibleDesign, FlexibleResults
from .sensitivity_analysis import SensitivityAnalysis
from .multi_objective import MultiObjectiveAnalysis

# Create aliases for compatibility
FlexibilityAnalysis = FlexibleDesign  # Alias for backward compatibility

# Make them available at the module level
__all__ = [
    'BaselineOptimization',
    'UncertaintyAnalysis', 
    'UncertaintyResults',
    'MonteCarloResults',
    'FlexibleDesign',
    'FlexibilityAnalysis',  # Alias
    'FlexibleResults',
    'SensitivityAnalysis',
    'MultiObjectiveAnalysis'
]
