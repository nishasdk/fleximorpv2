"""
Integration smoke tests for the full FlexiMORP v2 workflow.

These tests run the real pipeline end-to-end with small sample sizes
to verify that all modules connect correctly without API keys.
"""

import pytest
import numpy as np

from fleximorpv2.config import load_config
from fleximorpv2.baseline_optimization import BaselineOptimization
from fleximorpv2.uncertainty_analysis import UncertaintyAnalysis
from fleximorpv2.sensitivity_analysis import SensitivityAnalysis


@pytest.fixture(scope="module")
def alaska_config():
    config = load_config("alaska")
    config.uncertainty["monte_carlo_runs"] = 10  # tiny for CI speed
    return config


@pytest.fixture(scope="module")
def baseline_results(alaska_config):
    opt = BaselineOptimization(alaska_config)
    return opt.optimize("production", 200_000, method="scipy")


class TestBaselineIntegration:
    def test_optimization_completes(self, baseline_results):
        assert baseline_results is not None

    def test_financial_metrics_present(self, baseline_results):
        fm = baseline_results.financial_metrics
        assert "lcoe" in fm
        assert "npv" in fm
        assert "capex" in fm

    def test_lcoe_is_positive(self, baseline_results):
        assert baseline_results.financial_metrics["lcoe"] > 0

    def test_total_capacity_within_config_limit(self, baseline_results, alaska_config):
        total = baseline_results.technical_metrics["total_capacity"]
        max_cap = alaska_config.optimization.get("constraints", {}).get("max_total_capacity", 2.0)
        assert total <= max_cap * 1.01  # 1% tolerance for float rounding

    def test_technology_capacities_non_negative(self, baseline_results):
        for tech, cap in baseline_results.technology_capacities.items():
            assert cap >= 0, f"{tech} capacity is negative"


class TestUncertaintyIntegration:
    def test_uncertainty_analysis_completes(self, alaska_config, baseline_results):
        analyzer = UncertaintyAnalysis(alaska_config)
        results = analyzer.analyze_uncertainty(
            baseline_design=baseline_results.optimal_design,
            reoptimize=False,
        )
        assert results is not None

    def test_mean_performance_has_lcoe(self, alaska_config, baseline_results):
        analyzer = UncertaintyAnalysis(alaska_config)
        results = analyzer.analyze_uncertainty(
            baseline_design=baseline_results.optimal_design,
            reoptimize=False,
        )
        assert "lcoe" in results.mean_performance
        assert results.mean_performance["lcoe"] > 0

    def test_risk_metrics_present(self, alaska_config, baseline_results):
        analyzer = UncertaintyAnalysis(alaska_config)
        results = analyzer.analyze_uncertainty(
            baseline_design=baseline_results.optimal_design,
            reoptimize=False,
        )
        assert "prob_negative_npv" in results.risk_metrics
        assert 0 <= results.risk_metrics["prob_negative_npv"] <= 1

    def test_latin_hypercube_sampling(self, alaska_config, baseline_results):
        analyzer = UncertaintyAnalysis(alaska_config)
        results = analyzer.analyze_uncertainty(
            baseline_design=baseline_results.optimal_design,
            reoptimize=False,
            sampling_method="latin_hypercube",
        )
        assert results is not None
        assert "lcoe" in results.mean_performance


class TestSensitivityIntegration:
    def test_local_sensitivity_is_deterministic(self, alaska_config, baseline_results):
        sa = SensitivityAnalysis(alaska_config)
        results1 = sa._evaluate_design(baseline_results.optimal_design)
        results2 = sa._evaluate_design(baseline_results.optimal_design)
        assert results1["lcoe"] == pytest.approx(results2["lcoe"])

    def test_sensitivity_lcoe_is_positive(self, alaska_config, baseline_results):
        sa = SensitivityAnalysis(alaska_config)
        perf = sa._evaluate_design(baseline_results.optimal_design)
        assert perf["lcoe"] > 0

    def test_full_sensitivity_analysis(self, alaska_config, baseline_results):
        sa = SensitivityAnalysis(alaska_config)
        results = sa.analyze_sensitivity(
            baseline_results.optimal_design,
            methods=["local", "scenarios"],  # skip global (slow) in CI
        )
        assert results is not None
        assert len(results.local_sensitivity) > 0
        assert len(results.parameter_rankings) > 0
