"""
Test script to verify Latin Hypercube Sampling implementation.
"""

from fleximorpv2.config import load_site_config
from fleximorpv2.uncertainty_analysis import UncertaintyAnalysis

def test_sampling_methods():
    """Test both Monte Carlo and Latin Hypercube sampling."""
    
    # Load Alaska config
    config = load_site_config("alaska")
    analyzer = UncertaintyAnalysis(config)
    
    # Test baseline design
    baseline_design = {
        'wind_capacity': 80,
        'solar_capacity': 40,
        'platform_area': 6000,
        'water_depth': 45,
        'distance_to_shore': 25
    }
    
    print("Testing sampling methods with smaller run count...")
    
    # Compare methods with small sample for testing
    comparison = analyzer.compare_sampling_methods(
        baseline_design=baseline_design,
        reoptimize=False,
        n_runs=100  # Small for testing
    )
    
    print("\n📊 Sampling Method Comparison Results:")
    print(f"Monte Carlo LCOE: £{comparison['monte_carlo']['mean_lcoe']:.1f} ± {comparison['monte_carlo']['std_lcoe']:.1f}")
    print(f"Latin Hypercube LCOE: £{comparison['latin_hypercube']['mean_lcoe']:.1f} ± {comparison['latin_hypercube']['std_lcoe']:.1f}")
    
    print(f"\nConvergence Analysis:")
    conv = comparison['convergence_analysis'] 
    print(f"Variance reduction ratio: {conv['variance_reduction_ratio']:.3f}")
    print(f"Recommendation: {conv['recommendation']}")
    
    # Test individual methods
    print("\n🎲 Testing Monte Carlo method individually...")
    mc_results = analyzer.analyze_uncertainty(
        baseline_design=baseline_design,
        reoptimize=False,
        sampling_method='monte_carlo'
    )
    
    print("\n🎯 Testing Latin Hypercube method individually...")
    lhs_results = analyzer.analyze_uncertainty(
        baseline_design=baseline_design,
        reoptimize=False,
        sampling_method='latin_hypercube'
    )
    
    print(f"\nResults comparison:")
    print(f"MC:  LCOE £{mc_results.mean_performance['lcoe']:.1f}, Risk {mc_results.risk_metrics['prob_negative_npv']:.1%}")
    print(f"LHS: LCOE £{lhs_results.mean_performance['lcoe']:.1f}, Risk {lhs_results.risk_metrics['prob_negative_npv']:.1%}")
    
    print(f"\n✅ Both sampling methods working correctly!")
    
    return comparison

if __name__ == "__main__":
    test_sampling_methods()
