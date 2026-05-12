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
        """Estimate global sensitivity via one-at-a-time variance decomposition.

        Each parameter is sampled across its full range while others are held at
        their base values. The fraction of total output variance explained by each
        parameter approximates its first-order Sobol index.
        """
        # Evaluate at baseline once
        baseline_perf = self._evaluate_design(baseline_design)
        baseline_lcoe = baseline_perf.get('lcoe', 0)

        param_lcoes: Dict[str, List[float]] = {}
        rng = np.random.default_rng(seed=42)

        for param_name, param_info in self.sensitive_parameters.items():
            low, high = param_info['range']
            samples = rng.uniform(low, high, n_samples)
            lcoe_values = []
            for val in samples:
                perturbed = baseline_design.copy()
                perturbed[param_name] = val
                perf = self._evaluate_design(perturbed)
                lcoe_values.append(perf.get('lcoe', baseline_lcoe))
            param_lcoes[param_name] = lcoe_values

        # Total variance across all samples
        all_lcoes = [v for vals in param_lcoes.values() for v in vals]
        total_var = float(np.var(all_lcoes)) if all_lcoes else 1.0
        if total_var == 0:
            total_var = 1.0

        global_results: Dict[str, Dict[str, float]] = {}
        for param_name, lcoe_vals in param_lcoes.items():
            param_var = float(np.var(lcoe_vals))
            first_order = min(1.0, param_var / total_var)
            global_results[param_name] = {
                'first_order': first_order,
                'total_order': first_order,  # One-at-a-time: total ≈ first order
                'interaction': 0.0,
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
        """Estimate pairwise interaction effects via finite differences."""
        baseline_perf = self._evaluate_design(baseline_design)
        baseline_lcoe = baseline_perf.get('lcoe', 0)

        param_pairs = [
            ('wind_capacity_factor', 'electricity_price'),
            ('wind_capex', 'discount_rate'),
            ('water_depth', 'wave_capex'),
        ]

        interactions: Dict[str, float] = {}
        for param1, param2 in param_pairs:
            info1 = self.sensitive_parameters.get(param1)
            info2 = self.sensitive_parameters.get(param2)
            if not info1 or not info2:
                interactions[f"{param1}_x_{param2}"] = 0.0
                continue

            delta1 = (info1['range'][1] - info1['range'][0]) * 0.1
            delta2 = (info2['range'][1] - info2['range'][0]) * 0.1

            d1 = baseline_design.copy()
            d1[param1] = info1['base'] + delta1
            d2 = baseline_design.copy()
            d2[param2] = info2['base'] + delta2
            d12 = baseline_design.copy()
            d12[param1] = info1['base'] + delta1
            d12[param2] = info2['base'] + delta2

            lcoe1 = self._evaluate_design(d1).get('lcoe', baseline_lcoe)
            lcoe2 = self._evaluate_design(d2).get('lcoe', baseline_lcoe)
            lcoe12 = self._evaluate_design(d12).get('lcoe', baseline_lcoe)

            # Interaction = joint effect minus individual effects
            interaction = ((lcoe12 - baseline_lcoe) - (lcoe1 - baseline_lcoe) - (lcoe2 - baseline_lcoe))
            if baseline_lcoe != 0:
                interaction /= baseline_lcoe  # normalise to fraction
            interactions[f"{param1}_x_{param2}"] = interaction

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
        """Evaluate design performance using analytical LCOE model."""
        enabled_techs = self.config.get_enabled_technologies()

        discount_rate = design.get('discount_rate', self.config.economic.get('discount_rate', 0.08))
        project_life = int(design.get('project_lifetime', self.config.economic.get('project_lifetime', 25)))

        # Normalise electricity_price to $/MWh (config may store $/kWh)
        config_price = self.config.economic.get('electricity_price', 0.085)
        if config_price < 5:
            config_price = config_price * 1000
        electricity_price = design.get('electricity_price', config_price)

        crf = (discount_rate * (1 + discount_rate) ** project_life) / ((1 + discount_rate) ** project_life - 1)
        annuity = (1 - (1 + discount_rate) ** (-project_life)) / discount_rate

        total_capex = 0.0
        total_annual_energy = 0.0
        total_capacity = 0.0

        for tech in enabled_techs:
            capacity = design.get(f'{tech}_capacity', 0.0)
            if capacity <= 0:
                continue

            cf = design.get(f'{tech}_capacity_factor', self.config.technologies[tech].capacity_factor)

            if f'{tech}_capex' in design:
                cost_per_mw = design[f'{tech}_capex'] * 1000  # $/kW → $/MW
            else:
                cost_per_mw = self.config.technologies[tech].cost_per_mw

            total_capex += capacity * cost_per_mw
            total_annual_energy += cf * capacity * 8760
            total_capacity += capacity

        if total_capacity <= 0 or total_annual_energy <= 0:
            return {
                'lcoe': float('inf'), 'npv': 0.0,
                'capacity_factor': 0.0, 'capex': total_capex, 'annual_energy': 0.0
            }

        annual_opex = total_capex * 0.02  # 2% of CAPEX per year
        lcoe = (total_capex * crf + annual_opex) / total_annual_energy  # $/MWh

        annual_revenue = total_annual_energy * electricity_price
        npv = -total_capex + (annual_revenue - annual_opex) * annuity

        return {
            'lcoe': max(0, lcoe),
            'npv': npv,
            'capacity_factor': total_annual_energy / (total_capacity * 8760),
            'capex': total_capex,
            'annual_energy': total_annual_energy
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
