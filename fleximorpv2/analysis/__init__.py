"""
Analysis Modules Package

Contains the 6-step analysis workflow for offshore renewable energy optimization:
1. Baseline optimization (deterministic)
2. Uncertainty analysis (Monte Carlo)
3. Flexibility analysis (real options)
4. Multi-objective optimization
5. Sensitivity analysis
6. Risk assessment and mitigation
"""

from .step1_baseline import BaselineOptimization
from .step2_uncertainty import UncertaintyAnalysis
from .step3_flexibility import FlexibilityAnalysis
from .step4_multiobjective import MultiObjectiveOptimization
from .step5_sensitivity import SensitivityAnalysis
from .step6_risk_assessment import RiskAssessment

__all__ = [
    'BaselineOptimization',
    'UncertaintyAnalysis', 
    'FlexibilityAnalysis',
    'MultiObjectiveOptimization',
    'SensitivityAnalysis',
    'RiskAssessment'
]
