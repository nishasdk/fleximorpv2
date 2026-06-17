"""
FlexiMORPv2: Flexible Multi-Objective Renewable Platform v2

A modular system for hybrid offshore renewables analysis with real options.
Supports baseline optimization, uncertainty analysis, flexible design strategies,
multi-objective analysis, sensitivity analysis, and comprehensive visualization
for offshore renewable energy platforms.
"""

__version__ = "2.0.0"
__author__ = "FlexiMORP Team"

from .config import load_config, SiteConfig
from .baseline_optimization import BaselineOptimization
from .uncertainty_analysis import UncertaintyAnalysis
from .flexible_design import FlexibleDesign
from .multi_objective import MultiObjectiveAnalysis
from .sensitivity_analysis import SensitivityAnalysis
from .graphics import GraphicsEngine

# Import model classes
from .models.platform import PlatformModel
from .models.technologies import TechnologyModel
from .models.economics import EconomicModel

# Import utility classes
from .utils.data_loader import APIDataLoader
from .utils.financial import FinancialCalculator
from .utils.visualization import VisualizationUtils

__all__ = [
    # Configuration
    "load_config",
    "SiteConfig",
    
    # Main analysis modules (6-step workflow)
    "BaselineOptimization",          # Step 1: Baseline optimization
    "UncertaintyAnalysis",           # Step 2: Uncertainty analysis
    "FlexibleDesign",               # Step 3: Flexible design
    "MultiObjectiveAnalysis",       # Step 4: Multi-objective analysis
    "SensitivityAnalysis",          # Step 5: Sensitivity analysis
    "GraphicsEngine",               # Visualization across all steps
    
    # Core models
    "PlatformModel",
    "TechnologyModel", 
    "EconomicModel",
    
    # Utilities
    "APIDataLoader",
    "FinancialCalculator",
    "VisualizationUtils"
]

# Package metadata
__package_info__ = {
    "name": "fleximorpv2",
    "version": __version__,
    "description": "Flexible Multi-Objective Renewable Platform v2",
    "author": __author__,
    "analysis_modules": [
        "BaselineOptimization",
        "UncertaintyAnalysis", 
        "FlexibleDesign",
        "MultiObjectiveAnalysis",
        "SensitivityAnalysis"
    ],
    "supported_technologies": ["wind", "solar", "wave"],
    "supported_platforms": ["fixed", "floating", "semi_submersible"],
    "case_studies": ["alaska", "blyth", "eastport"]
}


def get_package_info():
    """Get package information."""
    return __package_info__


def create_analysis_workflow(config_path: str = None, site_name: str = None):
    """
    Create a complete analysis workflow for a site.
    
    Args:
        config_path: Path to configuration file
        site_name: Name of the site (if using default config location)
        
    Returns:
        Dictionary with initialized analysis modules
    """
    # Load configuration
    if config_path:
        import yaml
        with open(config_path, 'r') as f:
            raw_config = yaml.safe_load(f)
        # Would need to parse config here
        config = SiteConfig(**raw_config)  # Simplified
    elif site_name:
        config = load_config(site_name)
    else:
        raise ValueError("Must provide either config_path or site_name")
    
    # Initialize all analysis modules
    workflow = {
        'config': config,
        'baseline_optimizer': BaselineOptimization(config),
        'uncertainty_analyzer': UncertaintyAnalysis(config),
        'flexible_analyzer': FlexibleDesign(config),
        'multi_objective_analyzer': MultiObjectiveAnalysis(config),
        'sensitivity_analyzer': SensitivityAnalysis(config),
        'graphics_engine': GraphicsEngine(config)
    }
    
    return workflow


def run_complete_analysis(config_path: str = None, 
                         site_name: str = None,
                         save_results: bool = True,
                         output_dir: str = None):
    """
    Run the complete 6-step FlexiMORP analysis workflow.
    
    Args:
        config_path: Path to configuration file
        site_name: Name of the site (if using default config location)
        save_results: Whether to save results to files
        output_dir: Output directory for results
        
    Returns:
        Dictionary with all analysis results
    """
    print("Starting complete FlexiMORP v2 analysis workflow...")
    
    # Create workflow
    workflow = create_analysis_workflow(config_path, site_name)
    
    # Step 1: Baseline Optimization
    print("\n=== Step 1: Baseline Optimization ===")
    baseline_results = workflow['baseline_optimizer'].optimize(
        target_type='production',
        target_value=1000000  # 1 GWh target
    )
    
    # Step 2: Uncertainty Analysis
    print("\n=== Step 2: Uncertainty Analysis ===")
    uncertainty_results = workflow['uncertainty_analyzer'].analyze_uncertainty(
        baseline_design=baseline_results.optimal_design
    )
    
    # Step 3: Flexible Design Analysis
    print("\n=== Step 3: Flexible Design Analysis ===")
    flexible_results = workflow['flexible_analyzer'].analyze_flexibility(
        baseline_design=baseline_results.optimal_design
    )
    
    # Step 4: Multi-Objective Analysis
    print("\n=== Step 4: Multi-Objective Analysis ===")
    multi_obj_results = workflow['multi_objective_analyzer'].analyze_multi_objective(
        objectives=['minimize_lcoe', 'maximize_npv', 'minimize_environmental_impact']
    )
    
    # Step 5: Sensitivity Analysis
    print("\n=== Step 5: Sensitivity Analysis ===")
    sensitivity_results = workflow['sensitivity_analyzer'].analyze_sensitivity(
        baseline_design=baseline_results.optimal_design
    )
    
    # Step 6: Comprehensive Visualization
    print("\n=== Step 6: Results Visualization ===")
    graphics = workflow['graphics_engine']
    
    # Create visualizations
    baseline_plot = graphics.plot_optimization_results(baseline_results)
    uncertainty_plot = graphics.plot_uncertainty_results(uncertainty_results)
    flexible_plot = graphics.plot_flexibility_results(flexible_results)
    pareto_plot = graphics.plot_pareto_frontier(
        multi_obj_results, 
        ['minimize_lcoe', 'maximize_npv', 'minimize_environmental_impact']
    )
    sensitivity_plot = graphics.plot_sensitivity_results(sensitivity_results)
    comparison_plot = graphics.plot_comparison_analysis(
        baseline_results, uncertainty_results, flexible_results
    )
    
    # Compile results
    complete_results = {
        'baseline': baseline_results,
        'uncertainty': uncertainty_results,
        'flexible': flexible_results,
        'multi_objective': multi_obj_results,
        'sensitivity': sensitivity_results,
        'visualizations': {
            'baseline_plot': baseline_plot,
            'uncertainty_plot': uncertainty_plot,
            'flexible_plot': flexible_plot,
            'pareto_plot': pareto_plot,
            'sensitivity_plot': sensitivity_plot,
            'comparison_plot': comparison_plot
        }
    }
    
    # Save results if requested
    if save_results:
        print("\n=== Saving Results ===")
        
        if output_dir is None:
            from pathlib import Path
            package_root = Path(__file__).parent.parent
            output_dir = package_root / "data" / workflow['config'].name.lower() / "results"
        
        # Save each analysis result
        baseline_results.save_results(str(output_dir / "baseline"))
        uncertainty_results.save_results(str(output_dir / "uncertainty"))
        flexible_results.save_results(str(output_dir / "flexible"))
        multi_obj_results.save_results(str(output_dir / "multi_objective"))
        sensitivity_results.save_results(str(output_dir / "sensitivity"))
        
        # Save visualizations
        viz_dir = Path(output_dir) / "visualizations"
        viz_dir.mkdir(parents=True, exist_ok=True)
        
        graphics.save_figure(baseline_plot, str(viz_dir / "baseline_results.png"))
        graphics.save_figure(uncertainty_plot, str(viz_dir / "uncertainty_results.png"))
        graphics.save_figure(flexible_plot, str(viz_dir / "flexible_results.png"))
        graphics.save_figure(pareto_plot, str(viz_dir / "pareto_frontier.png"))
        graphics.save_figure(sensitivity_plot, str(viz_dir / "sensitivity_results.png"))
        graphics.save_figure(comparison_plot, str(viz_dir / "comparison_analysis.png"))
        
        print(f"All results saved to: {output_dir}")
    
    print("\n=== Analysis Complete ===")
    print("FlexiMORP v2 analysis workflow completed successfully!")
    
    return complete_results


def get_analysis_summary(results: dict) -> dict:
    """
    Get a comprehensive summary of all analysis results.
    
    Args:
        results: Dictionary containing all analysis results
        
    Returns:
        Summary dictionary with key findings
    """
    summary = {
        'baseline_summary': results['baseline'].get_summary(),
        'uncertainty_summary': results['uncertainty'].get_summary(),
        'flexible_summary': results['flexible'].get_summary(),
        'multi_objective_summary': results['multi_objective'].get_summary(),
        'sensitivity_summary': results['sensitivity'].get_summary()
    }
    
    # Overall recommendations
    summary['recommendations'] = {
        'optimal_design': results['baseline'].optimal_design,
        'flexibility_value': results['flexible'].flexibility_premium,
        'key_risks': results['uncertainty'].risk_metrics,
        'critical_parameters': results['sensitivity'].sensitivity_rankings,
        'pareto_solutions': len(results['multi_objective'].pareto_frontier)
    }
    
    return summary
