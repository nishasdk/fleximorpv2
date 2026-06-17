"""
Test suite for uncertainty analysis module.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from fleximorpv2.uncertainty_analysis import UncertaintyAnalysis, UncertaintyParameters, UncertaintyResults
from fleximorpv2.config import SiteConfig, load_config


class TestUncertaintyAnalysis:
    """Test uncertainty analysis functionality."""

    def setup_method(self):
        self.config = load_config("alaska")
        # Cap MC runs so unit tests stay fast
        self.config.uncertainty["monte_carlo_runs"] = 20
        self.analyzer = UncertaintyAnalysis(self.config)

    def test_initialization(self):
        """Test analyzer initialization."""
        assert self.analyzer.config == self.config
        assert self.analyzer.uncertainty_params.monte_carlo_runs > 0
        assert hasattr(self.analyzer, 'distributions')

    def test_scenario_generation(self):
        """Test Monte Carlo scenario generation."""
        scenarios = self.analyzer._generate_scenarios(sampling_method='monte_carlo')

        assert len(scenarios) == self.analyzer.uncertainty_params.monte_carlo_runs
        assert all(isinstance(s, dict) for s in scenarios)
    
    def test_evaluate_scenarios_excludes_array_fields(self):
        """Per-scenario performance dicts must only contain scalar values.

        TechnologyModel.calculate_performance() includes an hourly
        'generation_profile' numpy array; this must be stripped before
        results are fed into a pandas DataFrame for mean()/std() reduction.
        """
        design = {f'{tech}_capacity': 20 for tech in self.config.get_enabled_technologies()}
        scenarios = self.analyzer._generate_scenarios(sampling_method='monte_carlo')[:3]

        performance_results = self.analyzer._evaluate_scenarios(design, scenarios)

        assert performance_results
        for performance in performance_results:
            for key, value in performance.items():
                assert not isinstance(value, np.ndarray), f"{key} is an array"

    def test_analyze_uncertainty_runs_end_to_end(self):
        """analyze_uncertainty() must complete and return scalar statistics."""
        design = {f'{tech}_capacity': 20 for tech in self.config.get_enabled_technologies()}

        results = self.analyzer.analyze_uncertainty(design, reoptimize=False)

        assert isinstance(results.mean_performance['capacity_factor'], float)
        assert isinstance(results.std_performance['capacity_factor'], float)

    def test_risk_metrics_calculation(self):
        """Test risk metrics calculation."""
        import pandas as pd
        
        # Mock performance data
        data = {
            'lcoe': np.random.normal(85, 15, 1000),
            'npv': np.random.normal(10e6, 5e6, 1000),
            'capacity_factor': np.random.normal(0.35, 0.05, 1000)
        }
        df = pd.DataFrame(data)
        
        risk_metrics = self.analyzer._calculate_risk_metrics(df)
        
        assert 'lcoe_var_95' in risk_metrics
        assert 'prob_negative_npv' in risk_metrics
        assert 0 <= risk_metrics['prob_negative_npv'] <= 1


class TestUncertaintyParameters:
    """Test uncertainty parameter handling."""
    
    def test_parameter_creation(self):
        """Test uncertainty parameter creation."""
        params = UncertaintyParameters(
            monte_carlo_runs=1000,
            uncertain_variables={'weather': 'stochastic'},
            random_seed=42
        )
        
        assert params.monte_carlo_runs == 1000
        assert params.uncertain_variables['weather'] == 'stochastic'
        assert params.random_seed == 42
