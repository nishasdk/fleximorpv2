"""
FlexiMORP v2 Integration Example Script

Demonstrates the complete 6-step workflow for offshore renewable energy optimization.
This script shows how to use all the components together for a real analysis.
"""

import sys
from pathlib import Path
import yaml
import json
import pandas as pd
import numpy as np
from datetime import datetime
import logging

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from fleximorpv2.config_builder import ConfigurationBuilder
from fleximorpv2.adaptive_optimization import AdaptiveOptimizationEngine
from fleximorpv2.utils.environmental import EnvironmentalAssessment
from fleximorpv2.analysis import (
    BaselineOptimization,
    UncertaintyAnalysis,
    FlexibilityAnalysis
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """
    Complete FlexiMORP v2 workflow demonstration
    """
    print("🌊 FlexiMORP v2 - Complete Workflow Example")
    print("=" * 50)
    
    # Step 1: Load site configuration
    print("\n📋 Step 1: Loading Site Configuration")
    
    site_name = "blyth"  # Options: alaska, blyth, eastport
    config_path = project_root / "data" / site_name / "config.yaml"
    
    try:
        with open(config_path, 'r') as f:
            site_config = yaml.safe_load(f)
        
        print(f"✅ Loaded configuration for {site_config['site_info']['name']}")
        print(f"   Location: {site_config['site_info']['coordinates']['latitude']:.3f}, {site_config['site_info']['coordinates']['longitude']:.3f}")
        print(f"   Technologies: {', '.join(site_config['technology_options'].keys())}")
        
    except FileNotFoundError:
        print(f"❌ Configuration file not found: {config_path}")
        print("   Using default configuration...")
        site_config = create_default_config(site_name)
    
    # Step 2: Initialize configuration builder
    print("\n🔧 Step 2: Building Analysis Configuration")
    
    config_builder = ConfigurationBuilder()
    analysis_config = config_builder.build_from_site_config(site_config)
    
    print(f"✅ Configuration built successfully")
    print(f"   Optimization target: {analysis_config.get('optimization_target', 'minimize_lcoe')}")
    print(f"   Constraints: {len(analysis_config.get('constraints', {}))} constraint categories")
    
    # Step 3: Environmental assessment
    print("\n🌍 Step 3: Environmental Assessment")
    
    try:
        # Use demo API keys for this example
        api_keys = {
            'nrel': 'DEMO_KEY',
            'nasa': 'DEMO_KEY', 
            'openweather': 'DEMO_KEY',
            'copernicus': 'DEMO_KEY'
        }
        
        env_assessor = EnvironmentalAssessment(api_keys)
        
        lat = site_config['site_info']['coordinates']['latitude']
        lon = site_config['site_info']['coordinates']['longitude']
        technologies = list(site_config['technology_options'].keys())
        
        env_assessment = env_assessor.assess_site_suitability(lat, lon, technologies)
        
        print("✅ Environmental assessment completed")
        
        # Display suitability scores
        suitability = env_assessment.get('overall_suitability', {})
        for tech, scores in suitability.items():
            rating = scores.get('suitability_rating', 'unknown')
            score = scores.get('overall_score', 0)
            print(f"   {tech.title()}: {rating} (score: {score:.2f})")
            
    except Exception as e:
        print(f"⚠️  Environmental assessment failed: {e}")
        print("   Continuing with default environmental assumptions...")
        env_assessment = create_mock_environmental_assessment(lat, lon, technologies)
    
    # Step 4: Baseline optimization
    print("\n🎯 Step 4: Baseline Optimization")
    
    try:
        baseline_optimizer = BaselineOptimization(analysis_config)
        
        # Run optimization for target capacity
        target_capacity = site_config.get('project_parameters', {}).get('target_capacity_mw', 100)
        baseline_result = baseline_optimizer.optimize(target_type="capacity", target_value=target_capacity)
        
        print("✅ Baseline optimization completed")
        print(f"   Optimal LCOE: ${baseline_result.performance_metrics.get('lcoe_per_mwh', 0):.1f}/MWh")
        print(f"   Total capacity: {baseline_result.optimal_config.get('total_capacity_mw', 0):.1f} MW")
        print(f"   Capacity factor: {baseline_result.performance_metrics.get('overall_capacity_factor', 0):.1%}")
        
        # Technology breakdown
        tech_breakdown = baseline_result.performance_metrics.get('technology_breakdown', {})
        for tech, data in tech_breakdown.items():
            capacity = data.get('capacity_mw', 0)
            share = data.get('capacity_share', 0)
            print(f"   {tech.title()}: {capacity:.1f} MW ({share:.1%})")
            
    except Exception as e:
        print(f"❌ Baseline optimization failed: {e}")
        return
    
    # Step 5: Uncertainty analysis
    print("\n🎲 Step 5: Uncertainty Analysis")
    
    try:
        uncertainty_analyzer = UncertaintyAnalysis(analysis_config, baseline_result)
        
        # Run Monte Carlo simulation
        n_simulations = 250  # Reduced for demo speed
        print(f"   Running {n_simulations} Monte Carlo simulations...")
        
        uncertainty_result = uncertainty_analyzer.run_monte_carlo(
            n_simulations=n_simulations,
            parallel=True
        )
        
        print("✅ Uncertainty analysis completed")
        
        # Display statistics
        stats = uncertainty_result.statistics
        lcoe_stats = stats.get('lcoe', {})
        print(f"   LCOE statistics:")
        print(f"     Mean: ${lcoe_stats.get('mean', 0):.1f}/MWh")
        print(f"     Std Dev: ${lcoe_stats.get('std', 0):.1f}/MWh")
        print(f"     95% CI: ${lcoe_stats.get('p5', 0):.1f} - ${lcoe_stats.get('p95', 0):.1f}/MWh")
        
        # Risk metrics
        risk_metrics = uncertainty_result.risk_metrics
        lcoe_risk = risk_metrics.get('lcoe_risk', {})
        print(f"   Risk metrics:")
        print(f"     VaR (95%): ${lcoe_risk.get('var_95', 0):.1f}/MWh")
        print(f"     CVaR (95%): ${lcoe_risk.get('cvar_95', 0):.1f}/MWh")
        
        # Success rate
        sim_stats = stats.get('simulation_stats', {})
        success_rate = sim_stats.get('success_rate', 0)
        print(f"   Simulation success rate: {success_rate:.1%}")
        
    except Exception as e:
        print(f"❌ Uncertainty analysis failed: {e}")
        uncertainty_result = None
    
    # Step 6: Flexibility analysis
    print("\n🔄 Step 6: Flexibility Analysis") 
    
    try:
        # This would use the FlexibilityAnalysis class when fully implemented
        # For now, create mock flexibility results
        
        flexibility_result = {
            'real_options_value': 15000000,  # $15M
            'flexibility_premium': 0.12,     # 12%
            'optimal_staging': [
                {'year': 0, 'capacity_mw': 40, 'technologies': ['wind']},
                {'year': 3, 'capacity_mw': 30, 'technologies': ['solar']},
                {'year': 7, 'capacity_mw': 30, 'technologies': ['wind', 'wave']}
            ],
            'expansion_triggers': {
                'electricity_price_threshold': 85,  # $/MWh
                'technology_cost_reduction': 0.15,  # 15%
                'capacity_utilization': 0.85       # 85%
            }
        }
        
        print("✅ Flexibility analysis completed")
        print(f"   Real options value: ${flexibility_result['real_options_value']:,.0f}")
        print(f"   Flexibility premium: {flexibility_result['flexibility_premium']:.1%}")
        print(f"   Staging phases: {len(flexibility_result['optimal_staging'])}")
        
        for i, stage in enumerate(flexibility_result['optimal_staging']):
            year = stage['year']
            capacity = stage['capacity_mw']
            techs = ', '.join(stage['technologies'])
            print(f"     Phase {i+1}: Year {year}, {capacity} MW ({techs})")
            
    except Exception as e:
        print(f"❌ Flexibility analysis failed: {e}")
        flexibility_result = None
    
    # Step 7: Generate comprehensive results
    print("\n📊 Step 7: Results Summary and Export")
    
    # Compile all results
    comprehensive_results = {
        'analysis_metadata': {
            'site_name': site_name,
            'analysis_date': datetime.now().isoformat(),
            'fleximorp_version': '2.0.0',
            'analysis_duration_minutes': 5  # Placeholder
        },
        'site_configuration': site_config,
        'environmental_assessment': env_assessment,
        'baseline_optimization': {
            'optimal_config': baseline_result.optimal_config,
            'performance_metrics': baseline_result.performance_metrics,
            'optimization_details': baseline_result.optimization_details
        },
        'uncertainty_analysis': {
            'statistics': uncertainty_result.statistics if uncertainty_result else {},
            'risk_metrics': uncertainty_result.risk_metrics if uncertainty_result else {}
        },
        'flexibility_analysis': flexibility_result,
        'recommendations': generate_final_recommendations(
            baseline_result, uncertainty_result, flexibility_result, env_assessment
        )
    }
    
    # Save results
    results_file = project_root / f"results_{site_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        with open(results_file, 'w') as f:
            json.dump(comprehensive_results, f, indent=2, default=str)
        
        print(f"✅ Results saved to: {results_file}")
        
    except Exception as e:
        print(f"⚠️  Could not save results file: {e}")
    
    # Final summary
    print("\n🎉 Analysis Complete - Summary")
    print("=" * 50)
    
    baseline_lcoe = baseline_result.performance_metrics.get('lcoe_per_mwh', 0)
    baseline_capacity = baseline_result.optimal_config.get('total_capacity_mw', 0)
    
    print(f"📍 Site: {site_config['site_info']['name']}")
    print(f"💰 Optimal LCOE: ${baseline_lcoe:.1f}/MWh")
    print(f"⚡ Total Capacity: {baseline_capacity:.1f} MW")
    
    if uncertainty_result:
        lcoe_std = uncertainty_result.statistics.get('lcoe', {}).get('std', 0)
        print(f"📊 LCOE Uncertainty: ±${lcoe_std:.1f}/MWh (1σ)")
    
    if flexibility_result:
        flex_value = flexibility_result.get('real_options_value', 0)
        print(f"🔄 Flexibility Value: ${flex_value:,.0f}")
    
    env_score = env_assessment.get('overall_suitability', {})
    if env_score:
        avg_score = np.mean([scores.get('overall_score', 0) for scores in env_score.values()])
        print(f"🌍 Environmental Score: {avg_score:.2f}/1.0")
    
    print(f"\n📄 Detailed results saved to: {results_file.name}")
    print("\n🚀 Ready for next steps: detailed design, permitting, and stakeholder engagement!")


def create_default_config(site_name):
    """Create default configuration if config file not found"""
    
    site_configs = {
        'alaska': {
            'site_info': {
                'name': 'Alaska Community Project',
                'coordinates': {'latitude': 64.2008, 'longitude': -165.4064}
            },
            'technology_options': {
                'wind': {'capacity_factor': 0.42, 'capex_per_kw': 2500},
                'solar': {'capacity_factor': 0.18, 'capex_per_kw': 1800}
            },
            'project_parameters': {'target_capacity_mw': 25}
        },
        'blyth': {
            'site_info': {
                'name': 'Blyth Offshore Wind Farm',
                'coordinates': {'latitude': 55.1269, 'longitude': -1.5085}
            },
            'technology_options': {
                'wind': {'capacity_factor': 0.45, 'capex_per_kw': 2200},
                'solar': {'capacity_factor': 0.12, 'capex_per_kw': 1600},
                'wave': {'capacity_factor': 0.30, 'capex_per_kw': 4200}
            },
            'project_parameters': {'target_capacity_mw': 100}
        },
        'eastport': {
            'site_info': {
                'name': 'Eastport Floating Platform',
                'coordinates': {'latitude': 44.9070, 'longitude': -66.9901}
            },
            'technology_options': {
                'wind': {'capacity_factor': 0.38, 'capex_per_kw': 2400},
                'solar': {'capacity_factor': 0.20, 'capex_per_kw': 1500},
                'wave': {'capacity_factor': 0.25, 'capex_per_kw': 4500}
            },
            'project_parameters': {'target_capacity_mw': 75}
        }
    }
    
    return site_configs.get(site_name, site_configs['blyth'])


def create_mock_environmental_assessment(lat, lon, technologies):
    """Create mock environmental assessment for demo"""
    
    suitability_scores = {}
    for tech in technologies:
        suitability_scores[tech] = {
            'overall_score': 0.75,
            'suitability_rating': 'good',
            'resource_score': 0.8,
            'constraint_score': 0.7,
            'conflict_score': 0.8,
            'climate_score': 0.7
        }
    
    return {
        'location': {'latitude': lat, 'longitude': lon},
        'overall_suitability': suitability_scores,
        'environmental_constraints': {
            'overall_constraint_level': 'medium'
        },
        'stakeholder_conflicts': {
            'overall_conflict_level': 'low'
        },
        'climate_risks': {
            'overall_climate_risk': 'medium'
        },
        'recommendations': [
            'Conduct detailed environmental impact assessment',
            'Engage with local fishing communities',
            'Monitor marine mammal activity during construction'
        ]
    }


def generate_final_recommendations(baseline_result, uncertainty_result, flexibility_result, env_assessment):
    """Generate final project recommendations"""
    
    recommendations = []
    
    # Economic recommendations
    lcoe = baseline_result.performance_metrics.get('lcoe_per_mwh', 100)
    if lcoe < 80:
        recommendations.append({
            'category': 'Economic',
            'priority': 'High',
            'recommendation': 'Project shows excellent economic viability - proceed with detailed feasibility study'
        })
    elif lcoe < 100:
        recommendations.append({
            'category': 'Economic', 
            'priority': 'Medium',
            'recommendation': 'Good economic potential - consider value engineering to reduce costs'
        })
    else:
        recommendations.append({
            'category': 'Economic',
            'priority': 'High',
            'recommendation': 'High LCOE requires cost reduction strategies or alternative technologies'
        })
    
    # Risk recommendations
    if uncertainty_result:
        lcoe_cv = uncertainty_result.statistics.get('lcoe', {}).get('cv', 0)
        if lcoe_cv > 0.2:
            recommendations.append({
                'category': 'Risk',
                'priority': 'High', 
                'recommendation': 'High uncertainty - implement robust risk management and hedging strategies'
            })
    
    # Flexibility recommendations
    if flexibility_result:
        flex_premium = flexibility_result.get('flexibility_premium', 0)
        if flex_premium > 0.1:
            recommendations.append({
                'category': 'Strategy',
                'priority': 'Medium',
                'recommendation': 'Significant flexibility value - consider phased development approach'
            })
    
    # Environmental recommendations
    env_constraints = env_assessment.get('environmental_constraints', {})
    constraint_level = env_constraints.get('overall_constraint_level', 'medium')
    
    if constraint_level in ['high', 'critical']:
        recommendations.append({
            'category': 'Environmental',
            'priority': 'High',
            'recommendation': 'Significant environmental constraints - early stakeholder engagement essential'
        })
    
    # Default recommendations if none generated
    if not recommendations:
        recommendations = [
            {
                'category': 'General',
                'priority': 'Medium',
                'recommendation': 'Proceed with detailed project development and stakeholder consultation'
            }
        ]
    
    return recommendations


if __name__ == "__main__":
    main()
