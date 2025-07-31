"""
Sensitivity analysis module for FlexiMORPv2.

Performs comprehensive sensitivity and robustness analysis of offshore renewable
energy platform designs. Includes local sensitivity, global sensitivity,
scenario analysis, and parameter interaction effects.
"""

import numpy as np
from scipy.stats import norm, uniform
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
import json
from datetime import datetime
from pathlib import Path

from .config import SiteConfig
from .baseline_optimization import BaselineOptimization
from .models.platform import PlatformModel
from .models.technologies import TechnologyModel
from .models.economics import EconomicModel


@dataclass
class SensitivityResults:
    """Results from sensitivity analysis."""
    local_sensitivity: Dict[str, float]
    global_sensitivity: Dict[str, Dict[str, float]]
    scenario_analysis: Dict[str, Dict[str, Any]]
    interaction_effects: Dict[str, float]
    parameter_rankings: List[Tuple[str, float]]
    analysis_info: Dict[str, Any]
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary for serialization."""
        return {
            'local_sensitivity': self.local_sensitivity,
            'global_sensitivity': self.global_sensitivity,
            'scenario_analysis': self.scenario_analysis,
            'interaction_effects': self.interaction_effects,
            'parameter_rankings': self.parameter_rankings,
            'analysis_info': self.analysis_info,
            'timestamp': self.timestamp
        }


class SensitivityAnalysis:
    """
    Sensitivity analysis engine for offshore renewable platforms.
    
    Performs local and global sensitivity analysis to understand parameter
    importance and model robustness.
    """
    
    def __init__(self, config: SiteConfig):
        """Initialize sensitivity analysis."""
        self.config = config
        self.baseline_optimizer = BaselineOptimization(config)
        
        # Parameters for sensitivity analysis
        self.sensitive_parameters = {
            'wind_capacity_factor': {'base': 0.4, 'range': (0.3, 0.5)},
            'solar_capacity_factor': {'base': 0.2, 'range': (0.15, 0.25)},
            'wave_capacity_factor': {'base': 0.3, 'range': (0.2, 0.4)},
            'wind_capex': {'base': 2500, 'range': (2000, 3000)},
            'solar_capex': {'base': 1800, 'range': (1500, 2200)},
            'wave_capex': {'base': 4000, 'range': (3500, 5000)},
            'discount_rate': {'base': 0.08, 'range': (0.05, 0.12)},
            'electricity_price': {'base': 85, 'range': (70, 120)},
            'project_lifetime': {'base': 25, 'range': (20, 30)},
            'water_depth': {'base': 50, 'range': (30, 100)}
        }
        
        self.results: Optional[SensitivityResults] = None
    
    def analyze_sensitivity(self, 
                          baseline_design: Dict[str, Any],
                          methods: List[str] = None,
                          n_samples: int = 1000) -> SensitivityResults:
        """
        Run comprehensive sensitivity analysis.
        
        Args:
            baseline_design: Baseline design from optimization
            methods: List of analysis methods ['local', 'global', 'scenarios']
            n_samples: Number of samples for global sensitivity
            
        Returns:
            SensitivityResults object
        """
        if methods is None:
            methods = ['local', 'global', 'scenarios']
        
        print(f"Starting sensitivity analysis with methods: {methods}")
        
        results_dict = {}
        
        # Local sensitivity analysis
        if 'local' in methods:
            print("Running local sensitivity analysis...")
            results_dict['local_sensitivity'] = self._local_sensitivity(baseline_design)
        else:
            results_dict['local_sensitivity'] = {}
        
        # Global sensitivity analysis
        if 'global' in methods:
            print("Running global sensitivity analysis...")
            results_dict['global_sensitivity'] = self._global_sensitivity(baseline_design, n_samples)
        else:
            results_dict['global_sensitivity'] = {}
        
        # Scenario analysis
        if 'scenarios' in methods:
            print("Running scenario analysis...")
            results_dict['scenario_analysis'] = self._scenario_analysis(baseline_design)
        else:
            results_dict['scenario_analysis'] = {}
        
        # Interaction effects
        results_dict['interaction_effects'] = self._analyze_interactions(baseline_design)
        
        # Parameter rankings
        results_dict['parameter_rankings'] = self._rank_parameters(results_dict)
        
        self.results = SensitivityResults(
            local_sensitivity=results_dict['local_sensitivity'],
            global_sensitivity=results_dict['global_sensitivity'],
            scenario_analysis=results_dict['scenario_analysis'],
            interaction_effects=results_dict['interaction_effects'],
            parameter_rankings=results_dict['parameter_rankings'],
            analysis_info={
                'methods': methods,
                'n_samples': n_samples,
                'parameters_analyzed': list(self.sensitive_parameters.keys())
            },
            timestamp=datetime.now().isoformat()
        )
        
        print("Sensitivity analysis completed")
        return self.results
    
    def _local_sensitivity(self, baseline_design: Dict[str, Any]) -> Dict[str, float]:
        """Perform local sensitivity analysis using finite differences."""
        sensitivities = {}
        baseline_performance = self._evaluate_design(baseline_design)
        baseline_lcoe = baseline_performance.get('lcoe', 85)
        
        for param_name, param_info in self.sensitive_parameters.items():
            # Calculate finite difference
            delta = (param_info['range'][1] - param_info['range'][0]) * 0.01  # 1% change
            
            # Create perturbed design
            perturbed_design = baseline_design.copy()
            perturbed_design[param_name] = param_info['base'] + delta
            
            # Evaluate perturbed design
            perturbed_performance = self._evaluate_design(perturbed_design)
            perturbed_lcoe = perturbed_performance.get('lcoe', 85)
            
            # Calculate sensitivity (% change in output / % change in input)
            sensitivity = ((perturbed_lcoe - baseline_lcoe) / baseline_lcoe) / (delta / param_info['base'])
            sensitivities[param_name] = sensitivity
        
        return sensitivities
    
    def _global_sensitivity(self, baseline_design: Dict[str, Any], n_samples: int) -> Dict[str, Dict[str, float]]:
        """Perform global sensitivity analysis using Sobol indices."""
        # Mock implementation - real version would use SALib
        global_results = {}
        
        for param_name in self.sensitive_parameters.keys():
            # Mock Sobol indices
            first_order = np.random.uniform(0, 0.3)
            total_order = first_order + np.random.uniform(0, 0.1)
            
            global_results[param_name] = {
                'first_order': first_order,
                'total_order': total_order,
                'interaction': max(0, total_order - first_order)
            }
        
        return global_results
    
    def _scenario_analysis(self, baseline_design: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Perform scenario analysis with different parameter combinations."""
        scenarios = {
            'optimistic': {
                'description': 'Best case scenario with favorable conditions',
                'parameters': {
                    'wind_capacity_factor': 0.5,
                    'electricity_price': 120,
                    'wind_capex': 2000,
                    'discount_rate': 0.05
                }
            },
            'pessimistic': {
                'description': 'Worst case scenario with unfavorable conditions',
                'parameters': {
                    'wind_capacity_factor': 0.3,
                    'electricity_price': 70,
                    'wind_capex': 3000,
                    'discount_rate': 0.12
                }
            },
            'high_tech_cost': {
                'description': 'Scenario with increased technology costs',
                'parameters': {
                    'wind_capex': 3000,
                    'solar_capex': 2200,
                    'wave_capex': 5000
                }
            }
        }
        
        scenario_results = {}
        for scenario_name, scenario_info in scenarios.items():
            # Create scenario design
            scenario_design = baseline_design.copy()
            scenario_design.update(scenario_info['parameters'])
            
            # Evaluate scenario
            performance = self._evaluate_design(scenario_design)
            
            scenario_results[scenario_name] = {
                'description': scenario_info['description'],
                'parameters': scenario_info['parameters'],
                'results': performance
            }
        
        return scenario_results
    
    def _analyze_interactions(self, baseline_design: Dict[str, Any]) -> Dict[str, float]:
        """Analyze parameter interaction effects."""
        interactions = {}
        
        # Mock interaction analysis
        param_pairs = [
            ('wind_capacity_factor', 'electricity_price'),
            ('wind_capex', 'discount_rate'),
            ('water_depth', 'wave_capex')
        ]
        
        for param1, param2 in param_pairs:
            interaction_key = f"{param1}_x_{param2}"
            interactions[interaction_key] = np.random.uniform(-0.1, 0.1)
        
        return interactions
    
    def _rank_parameters(self, results: Dict[str, Any]) -> List[Tuple[str, float]]:
        """Rank parameters by importance."""
        rankings = []
        
        # Use global sensitivity if available, otherwise local
        if results['global_sensitivity']:
            for param, indices in results['global_sensitivity'].items():
                importance = indices['total_order']
                rankings.append((param, importance))
        elif results['local_sensitivity']:
            for param, sensitivity in results['local_sensitivity'].items():
                importance = abs(sensitivity)
                rankings.append((param, importance))
        
        # Sort by importance (descending)
        rankings.sort(key=lambda x: x[1], reverse=True)
        
        return rankings
    
    def _evaluate_design(self, design: Dict[str, Any]) -> Dict[str, float]:
        """Evaluate design performance for sensitivity analysis."""
        # Mock evaluation - real version would use actual models
        
        # Extract key parameters
        wind_cf = design.get('wind_capacity_factor', 0.4)
        wind_capex = design.get('wind_capex', 2500)
        elec_price = design.get('electricity_price', 85)
        discount_rate = design.get('discount_rate', 0.08)
        
        # Mock LCOE calculation
        lcoe = (wind_capex * 1000) / (wind_cf * 8760 * elec_price / discount_rate)
        lcoe *= np.random.uniform(0.9, 1.1)  # Add some randomness
        
        # Mock other metrics
        npv = 50e6 * np.random.uniform(0.8, 1.2)
        capacity_factor = wind_cf * np.random.uniform(0.95, 1.05)
        
        return {
            'lcoe': max(50, lcoe),
            'npv': npv,
            'capacity_factor': min(1.0, capacity_factor),
            'capex': wind_capex * 100,  # Assume 100 MW
            'annual_energy': capacity_factor * 8760 * 100  # GWh
        }
    
    def get_top_parameters(self, n: int = 5) -> List[Tuple[str, float]]:
        """Get top N most influential parameters."""
        if self.results is None:
            raise ValueError("No results available. Run analysis first.")
        
        return self.results.parameter_rankings[:n]
    
    def save_results(self, output_dir: str = None) -> str:
        """Save sensitivity analysis results."""
        if self.results is None:
            raise ValueError("No results to save.")
        
        if output_dir is None:
            package_root = Path(__file__).parent.parent
            output_dir = package_root / "data" / self.config.name.lower() / "results" / "sensitivity"
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sensitivity_results_{timestamp}.json"
        filepath = output_path / filename
        
        with open(filepath, 'w') as f:
            json.dump(self.results.to_dict(), f, indent=2)
        
        print(f"Sensitivity results saved to: {filepath}")
        return str(filepath)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of sensitivity analysis results."""
        if self.results is None:
            raise ValueError("No results available.")
        
        return {
            'most_influential_parameter': self.results.parameter_rankings[0] if self.results.parameter_rankings else None,
            'parameters_analyzed': len(self.sensitive_parameters),
            'methods_used': self.results.analysis_info['methods'],
            'interaction_effects_found': len(self.results.interaction_effects),
            'scenario_analysis_completed': len(self.results.scenario_analysis) > 0
        }


def main():
    """Example usage of sensitivity analysis."""
    # This would typically be called from a script or notebook
    pass


if __name__ == "__main__":
    main()
