"""
Tests for Latin Hypercube vs Monte Carlo sampling in uncertainty analysis.
"""

import pytest
from fleximorpv2.config import load_config
from fleximorpv2.uncertainty_analysis import UncertaintyAnalysis

BASELINE_DESIGN = {
    'wind_capacity': 0.5,
    'solar_capacity': 0.3,
    'hydro_capacity': 0.1,
    'platform_area': 6000,
    'water_depth': 15,
    'distance_to_shore': 0.5,
}


@pytest.fixture(scope="module")
def analyzer():
    config = load_config("alaska")
    config.uncertainty["monte_carlo_runs"] = 20  # small for CI speed
    return UncertaintyAnalysis(config)


def test_monte_carlo_sampling(analyzer):
    results = analyzer.analyze_uncertainty(
        baseline_design=BASELINE_DESIGN,
        reoptimize=False,
        sampling_method='monte_carlo',
    )
    assert results is not None
    assert results.mean_performance.get('lcoe', 0) > 0
    assert 0 <= results.risk_metrics.get('prob_negative_npv', 0) <= 1


def test_latin_hypercube_sampling(analyzer):
    results = analyzer.analyze_uncertainty(
        baseline_design=BASELINE_DESIGN,
        reoptimize=False,
        sampling_method='latin_hypercube',
    )
    assert results is not None
    assert results.mean_performance.get('lcoe', 0) > 0


def test_sampling_comparison(analyzer):
    comparison = analyzer.compare_sampling_methods(
        baseline_design=BASELINE_DESIGN,
        reoptimize=False,
        n_runs=20,
    )
    assert 'monte_carlo' in comparison
    assert 'latin_hypercube' in comparison
    assert 'convergence_analysis' in comparison
    assert 'recommendation' in comparison['convergence_analysis']


if __name__ == "__main__":
    cfg = load_config("alaska")
    cfg.uncertainty["monte_carlo_runs"] = 50
    an = UncertaintyAnalysis(cfg)
    mc = an.analyze_uncertainty(BASELINE_DESIGN, reoptimize=False, sampling_method='monte_carlo')
    lhs = an.analyze_uncertainty(BASELINE_DESIGN, reoptimize=False, sampling_method='latin_hypercube')
    print(f"MC  LCOE: {mc.mean_performance['lcoe']:.2f}, risk: {mc.risk_metrics['prob_negative_npv']:.1%}")
    print(f"LHS LCOE: {lhs.mean_performance['lcoe']:.2f}, risk: {lhs.risk_metrics['prob_negative_npv']:.1%}")

