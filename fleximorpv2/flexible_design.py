"""
Flexible design module for FlexiMORPv2.

Implements real options analysis for offshore renewable energy platforms.
Analyzes flexibility in design through decision rules, expansion options,
and technology switching strategies.
"""

import numpy as np
from scipy.optimize import minimize, differential_evolution
from typing import Dict, Any, List, Tuple, Optional, Union
from dataclasses import dataclass
import json
from datetime import datetime
from pathlib import Path
import pandas as pd

from .config import SiteConfig
from .baseline_optimization import BaselineOptimization
from .uncertainty_analysis import UncertaintyAnalysis
from .models.platform import PlatformModel
from .models.technologies import TechnologyModel
from .models.economics import EconomicModel
from .utils.data_loader import APIDataLoader
from .utils.financial import FinancialCalculator


@dataclass
class FlexibilityOption:
    """Represents a flexibility option in the design."""
    option_type: str  # 'expansion', 'abandonment', 'technology_switch', 'delay'
    trigger_conditions: Dict[str, Any]
    action_parameters: Dict[str, Any]
    exercise_cost: float
    availability_period: Tuple[int, int]  # (start_year, end_year)


@dataclass
class FlexibleResults:
    """Results from flexible design analysis."""
    optimal_flexible_design: Dict[str, Any]
    flexibility_options: List[FlexibilityOption]
    option_values: Dict[str, float]
    decision_tree: Dict[str, Any]
    expected_performance: Dict[str, float]
    flexibility_premium: float
    scenario_analysis: List[Dict[str, Any]]
    flexibility_info: Dict[str, Any]
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary for serialization."""
        return {
            'optimal_flexible_design': self.optimal_flexible_design,
            'flexibility_options': [
                {
                    'option_type': opt.option_type,
                    'trigger_conditions': opt.trigger_conditions,
                    'action_parameters': opt.action_parameters,
                    'exercise_cost': opt.exercise_cost,
                    'availability_period': opt.availability_period
                } for opt in self.flexibility_options
            ],
            'option_values': self.option_values,
            'decision_tree': self.decision_tree,
            'expected_performance': self.expected_performance,
            'flexibility_premium': self.flexibility_premium,
            'scenario_analysis': self.scenario_analysis,
            'flexibility_info': self.flexibility_info,
            'timestamp': self.timestamp
        }


class FlexibleDesign:
    """
    Flexible design engine for offshore renewable energy platforms.
    
    Implements real options analysis to value and optimize flexibility
    in platform design. Includes expansion options, abandonment options,
    technology switching, and staged development strategies.
    """
    
    def __init__(self, config: SiteConfig):
        """
        Initialize flexible design analysis.
        
        Args:
            config: Site configuration object
        """
        self.config = config
        self.baseline_optimizer = BaselineOptimization(config)
        self.uncertainty_analyzer = UncertaintyAnalysis(config)
        self.platform_model = PlatformModel(config)
        self.tech_model = TechnologyModel(config)
        self.economic_model = EconomicModel(config)
        self.data_loader = APIDataLoader(config)
        self.financial_calc = FinancialCalculator(config)
        
        # Setup flexibility parameters
        self._setup_flexibility_parameters()
        
        # Results storage
        self.results: Optional[FlexibleResults] = None
    
    def _setup_flexibility_parameters(self):
        """Setup flexibility parameters from configuration."""
        flexibility_config = self.config.flexibility
        
        self.decision_points = flexibility_config.get('decision_points', [2, 5, 10])
        self.expansion_options = flexibility_config.get('expansion_options', [25, 50, 100])
        self.abandonment_option = flexibility_config.get('abandonment_option', True)
        self.technology_switching = flexibility_config.get('technology_switching', True)
        
        # Define flexibility options
        self._define_flexibility_options()
    
    def _define_flexibility_options(self):
        """Define available flexibility options."""
        self.flexibility_options = []
        
        # Expansion options
        for year in self.decision_points:
            for capacity in self.expansion_options:
                option = FlexibilityOption(
                    option_type='expansion',
                    trigger_conditions={
                        'min_electricity_price': 0.11,  # £/kWh
                        'min_capacity_factor': 0.35,
                        'max_payback_period': 10
                    },
                    action_parameters={
                        'additional_capacity': capacity,
                        'technology_mix': 'optimal'
                    },
                    exercise_cost=capacity * 100000,  # £100k/MW for expansion
                    availability_period=(year, year + 5)
                )
                self.flexibility_options.append(option)
        
        # Abandonment option
        if self.abandonment_option:
            for year in self.decision_points:
                option = FlexibilityOption(
                    option_type='abandonment',
                    trigger_conditions={
                        'max_electricity_price': 0.08,  # £/kWh
                        'max_capacity_factor': 0.25,
                        'min_remaining_value': 0.3  # 30% of initial investment
                    },
                    action_parameters={
                        'salvage_value_ratio': 0.4  # 40% salvage value
                    },
                    exercise_cost=1000000,  # £1M abandonment cost
                    availability_period=(year, self.config.economic['project_lifetime'])
                )
                self.flexibility_options.append(option)
        
        # Technology switching options
        if self.technology_switching:
            for year in self.decision_points:
                option = FlexibilityOption(
                    option_type='technology_switch',
                    trigger_conditions={
                        'technology_performance_ratio': 1.2,  # 20% improvement
                        'payback_period': 8
                    },
                    action_parameters={
                        'switch_from': 'worst_performing',
                        'switch_to': 'best_available',
                        'switch_percentage': 0.5
                    },
                    exercise_cost=500000,  # £500k switching cost
                    availability_period=(year, year + 3)
                )
                self.flexibility_options.append(option)
    
    def analyze_flexibility(self, 
                          baseline_design: Dict[str, Any] = None,
                          **kwargs) -> FlexibleResults:
        """
        Run flexible design analysis with real options.
        
        Args:
            baseline_design: Optional baseline design. If None, will optimize first.
            **kwargs: Additional parameters for analysis
            
        Returns:
            FlexibleResults object with analysis results
        """
        print("Starting flexible design analysis...")
        
        # Get baseline design if not provided
        if baseline_design is None:
            print("No baseline design provided. Running baseline optimization...")
            baseline_results = self.baseline_optimizer.optimize(
                target_type='production',
                target_value=kwargs.get('target_production', 1000000)  # 1 GWh default
            )
            baseline_design = baseline_results.optimal_design
        
        # Run uncertainty analysis to get scenarios
        print("Generating uncertainty scenarios...")
        uncertainty_results = self.uncertainty_analyzer.analyze_uncertainty(
            baseline_design, reoptimize=False
        )
        
        # Build decision tree
        print("Building decision tree...")
        decision_tree = self._build_decision_tree(baseline_design, uncertainty_results)
        
        # Value flexibility options
        print("Valuing flexibility options...")
        option_values = self._value_flexibility_options(decision_tree, uncertainty_results)
        
        # Optimize flexible design
        print("Optimizing flexible design...")
        optimal_flexible_design = self._optimize_flexible_design(
            baseline_design, option_values, **kwargs
        )
        
        # Calculate flexibility premium
        flexibility_premium = self._calculate_flexibility_premium(
            baseline_design, optimal_flexible_design, option_values
        )
        
        # Create results
        self.results = FlexibleResults(
            optimal_flexible_design=optimal_flexible_design,
            flexibility_options=self.flexibility_options,
            option_values=option_values,
            decision_tree=decision_tree,
            expected_performance=self._calculate_expected_performance(
                optimal_flexible_design, decision_tree
            ),
            flexibility_premium=flexibility_premium,
            scenario_analysis=self._run_scenario_analysis(optimal_flexible_design),
            flexibility_info={
                'decision_points': self.decision_points,
                'expansion_options': self.expansion_options,
                'abandonment_option': self.abandonment_option,
                'technology_switching': self.technology_switching,
                'total_options': len(self.flexibility_options)
            },
            timestamp=datetime.now().isoformat()
        )
        
        print("Flexible design analysis completed.")
        return self.results
    
    def _build_decision_tree(self, 
                           baseline_design: Dict[str, Any],
                           uncertainty_results) -> Dict[str, Any]:
        """Build decision tree for flexibility analysis."""
        
        # Create scenario tree based on uncertainty results
        scenarios = uncertainty_results.scenario_results
        
        # Group scenarios by time periods
        decision_tree = {
            'root': {
                'design': baseline_design,
                'probability': 1.0,
                'branches': {}
            }
        }
        
        # Create branches for each decision point
        for year in self.decision_points:
            year_key = f'year_{year}'
            decision_tree['root']['branches'][year_key] = {
                'scenarios': self._create_scenario_branches(scenarios, year),
                'available_options': self._get_available_options(year),
                'optimal_decisions': {}
            }
        
        return decision_tree
    
    def _create_scenario_branches(self, scenarios: List[Dict], year: int) -> List[Dict]:
        """Create scenario branches for a specific year."""
        # Cluster scenarios into representative branches (e.g., high/medium/low)
        
        # Extract key variables for clustering
        scenario_data = []
        for scenario in scenarios[:1000]:  # Sample for speed
            scenario_data.append([
                scenario.get('lcoe', 0),
                scenario.get('capacity_factor', 0),
                scenario.get('npv', 0)
            ])
        
        scenario_array = np.array(scenario_data)
        
        # Simple clustering into 3 scenarios (high/medium/low performance)
        # Use percentiles as a simple clustering method
        lcoe_values = scenario_array[:, 0]
        p33, p67 = np.percentile(lcoe_values, [33, 67])
        
        branches = []
        
        # Low performance (high LCOE)
        high_lcoe_mask = lcoe_values >= p67
        if np.any(high_lcoe_mask):
            high_lcoe_data = scenario_array[high_lcoe_mask]
            branches.append({
                'scenario_id': 'low_performance',
                'probability': np.sum(high_lcoe_mask) / len(lcoe_values),
                'lcoe': np.mean(high_lcoe_data[:, 0]),
                'capacity_factor': np.mean(high_lcoe_data[:, 1]),
                'npv': np.mean(high_lcoe_data[:, 2]),
                'year': year
            })
        
        # Medium performance
        medium_lcoe_mask = (lcoe_values >= p33) & (lcoe_values < p67)
        if np.any(medium_lcoe_mask):
            medium_lcoe_data = scenario_array[medium_lcoe_mask]
            branches.append({
                'scenario_id': 'medium_performance',
                'probability': np.sum(medium_lcoe_mask) / len(lcoe_values),
                'lcoe': np.mean(medium_lcoe_data[:, 0]),
                'capacity_factor': np.mean(medium_lcoe_data[:, 1]),
                'npv': np.mean(medium_lcoe_data[:, 2]),
                'year': year
            })
        
        # High performance (low LCOE)
        low_lcoe_mask = lcoe_values < p33
        if np.any(low_lcoe_mask):
            low_lcoe_data = scenario_array[low_lcoe_mask]
            branches.append({
                'scenario_id': 'high_performance',
                'probability': np.sum(low_lcoe_mask) / len(lcoe_values),
                'lcoe': np.mean(low_lcoe_data[:, 0]),
                'capacity_factor': np.mean(low_lcoe_data[:, 1]),
                'npv': np.mean(low_lcoe_data[:, 2]),
                'year': year
            })
        
        return branches
    
    def _get_available_options(self, year: int) -> List[FlexibilityOption]:
        """Get flexibility options available at a specific year."""
        available = []
        for option in self.flexibility_options:
            start_year, end_year = option.availability_period
            if start_year <= year <= end_year:
                available.append(option)
        return available
    
    def _value_flexibility_options(self, 
                                 decision_tree: Dict[str, Any],
                                 uncertainty_results) -> Dict[str, float]:
        """Value flexibility options using real options pricing."""
        option_values = {}
        
        for option in self.flexibility_options:
            option_id = f"{option.option_type}_{option.availability_period[0]}"
            
            if option.option_type == 'expansion':
                value = self._value_expansion_option(option, decision_tree, uncertainty_results)
            elif option.option_type == 'abandonment':
                value = self._value_abandonment_option(option, decision_tree, uncertainty_results)
            elif option.option_type == 'technology_switch':
                value = self._value_switching_option(option, decision_tree, uncertainty_results)
            else:
                value = 0.0
            
            option_values[option_id] = max(0, value)  # Option value cannot be negative
        
        return option_values
    
    def _value_expansion_option(self, 
                              option: FlexibilityOption,
                              decision_tree: Dict[str, Any],
                              uncertainty_results) -> float:
        """Value expansion option using Black-Scholes-like approach."""
        
        # Get relevant parameters
        exercise_price = option.exercise_cost
        additional_capacity = option.action_parameters['additional_capacity']
        start_year = option.availability_period[0]
        
        # Estimate underlying asset value (additional capacity NPV)
        mean_electricity_price = self.config.economic.get('electricity_price', 0.10)
        mean_capacity_factor = uncertainty_results.mean_performance.get('capacity_factor', 0.35)
        
        # Annual revenue from additional capacity
        annual_revenue = additional_capacity * 1000 * 8760 * mean_capacity_factor * mean_electricity_price
        
        # Simple NPV calculation for underlying asset
        discount_rate = self.config.economic.get('discount_rate', 0.08)
        remaining_years = self.config.economic.get('project_lifetime', 25) - start_year
        
        if remaining_years > 0:
            pv_revenue = annual_revenue * ((1 - (1 + discount_rate)**(-remaining_years)) / discount_rate)
            underlying_value = pv_revenue - exercise_price
        else:
            underlying_value = 0
        
        # Volatility estimate from uncertainty results
        electricity_price_std = uncertainty_results.std_performance.get('electricity_price', 0.02)
        volatility = electricity_price_std / mean_electricity_price if mean_electricity_price > 0 else 0.3
        
        # Time to expiration
        time_to_expiry = option.availability_period[1] - start_year
        
        # Simple option value approximation (simplified Black-Scholes)
        if time_to_expiry > 0 and volatility > 0:
            intrinsic_value = max(0, underlying_value)
            time_value = underlying_value * volatility * np.sqrt(time_to_expiry) * 0.4
            option_value = intrinsic_value + time_value
        else:
            option_value = max(0, underlying_value)
        
        return option_value
    
    def _value_abandonment_option(self, 
                                option: FlexibilityOption,
                                decision_tree: Dict[str, Any],
                                uncertainty_results) -> float:
        """Value abandonment option (put option)."""
        
        salvage_ratio = option.action_parameters.get('salvage_value_ratio', 0.4)
        exercise_cost = option.exercise_cost
        start_year = option.availability_period[0]
        
        # Estimate remaining project value
        total_capex = uncertainty_results.mean_performance.get('capex', 50000000)
        remaining_book_value = total_capex * (1 - start_year / self.config.economic.get('project_lifetime', 25))
        salvage_value = remaining_book_value * salvage_ratio
        
        # Estimate continuation value under poor performance scenarios
        poor_scenarios = [s for s in uncertainty_results.scenario_results 
                         if s.get('npv', 0) < 0]
        
        if poor_scenarios:
            mean_loss = np.mean([s['npv'] for s in poor_scenarios])
            prob_poor = len(poor_scenarios) / len(uncertainty_results.scenario_results)
            
            # Value of abandonment = salvage value - exercise cost - expected losses
            abandonment_payoff = max(0, salvage_value - exercise_cost + abs(mean_loss))
            option_value = prob_poor * abandonment_payoff
        else:
            option_value = 0
        
        return option_value
    
    def _value_switching_option(self, 
                              option: FlexibilityOption,
                              decision_tree: Dict[str, Any],
                              uncertainty_results) -> float:
        """Value technology switching option."""
        
        switch_cost = option.exercise_cost
        performance_improvement = option.trigger_conditions.get('technology_performance_ratio', 1.2)
        
        # Estimate value of performance improvement
        current_revenue = uncertainty_results.mean_performance.get('revenue', 10000000)
        improved_revenue = current_revenue * performance_improvement
        revenue_increase = improved_revenue - current_revenue
        
        # Present value of revenue increase
        discount_rate = self.config.economic.get('discount_rate', 0.08)
        start_year = option.availability_period[0]
        remaining_years = self.config.economic.get('project_lifetime', 25) - start_year
        
        if remaining_years > 0:
            pv_benefit = revenue_increase * ((1 - (1 + discount_rate)**(-remaining_years)) / discount_rate)
            option_value = max(0, pv_benefit - switch_cost)
        else:
            option_value = 0
        
        return option_value
    
    def _optimize_flexible_design(self, 
                                baseline_design: Dict[str, Any],
                                option_values: Dict[str, float],
                                **kwargs) -> Dict[str, Any]:
        """Optimize flexible design considering option values."""
        
        # Start with baseline design
        flexible_design = baseline_design.copy()
        
        # Adjust initial capacity based on expansion options
        total_expansion_value = sum(v for k, v in option_values.items() if 'expansion' in k)
        
        if total_expansion_value > 0:
            # Reduce initial capacity to preserve expansion options
            reduction_factor = kwargs.get('initial_capacity_reduction', 0.8)
            
            for tech_name in self.config.get_enabled_technologies():
                capacity_key = f'{tech_name}_capacity'
                if capacity_key in flexible_design:
                    flexible_design[capacity_key] *= reduction_factor
        
        # Add option values to design
        flexible_design['embedded_option_value'] = sum(option_values.values())
        flexible_design['flexibility_strategy'] = self._determine_flexibility_strategy(option_values)
        
        return flexible_design
    
    def _determine_flexibility_strategy(self, option_values: Dict[str, float]) -> Dict[str, Any]:
        """Determine optimal flexibility strategy based on option values."""
        
        strategy = {
            'recommended_options': [],
            'staging_strategy': 'single_stage',
            'risk_management': 'low'
        }
        
        # Recommend high-value options
        sorted_options = sorted(option_values.items(), key=lambda x: x[1], reverse=True)
        valuable_options = [k for k, v in sorted_options if v > 1000000]  # £1M threshold
        
        strategy['recommended_options'] = valuable_options
        
        # Determine staging strategy
        expansion_values = [v for k, v in option_values.items() if 'expansion' in k]
        if expansion_values and max(expansion_values) > 2000000:  # £2M threshold
            strategy['staging_strategy'] = 'multi_stage'
        
        # Risk management level
        abandonment_values = [v for k, v in option_values.items() if 'abandonment' in k]
        if abandonment_values and max(abandonment_values) > 5000000:  # £5M threshold
            strategy['risk_management'] = 'high'
        
        return strategy
    
    def _calculate_flexibility_premium(self, 
                                     baseline_design: Dict[str, Any],
                                     flexible_design: Dict[str, Any],
                                     option_values: Dict[str, float]) -> float:
        """Calculate the value premium of flexible design over baseline."""
        
        total_option_value = sum(option_values.values())
        
        # Estimate additional costs of flexibility
        flexibility_costs = 0
        
        # Cost of reduced initial scale
        initial_capacity_baseline = sum(
            baseline_design.get(f'{tech}_capacity', 0) 
            for tech in self.config.get_enabled_technologies()
        )
        initial_capacity_flexible = sum(
            flexible_design.get(f'{tech}_capacity', 0) 
            for tech in self.config.get_enabled_technologies()
        )
        
        capacity_reduction = initial_capacity_baseline - initial_capacity_flexible
        if capacity_reduction > 0:
            # Lost economies of scale (estimated at 5% cost penalty)
            flexibility_costs += capacity_reduction * 1500000 * 0.05  # £1.5M/MW * 5%
        
        # Net flexibility premium
        flexibility_premium = total_option_value - flexibility_costs
        
        return flexibility_premium
    
    def _calculate_expected_performance(self, 
                                      flexible_design: Dict[str, Any],
                                      decision_tree: Dict[str, Any]) -> Dict[str, float]:
        """Calculate expected performance of flexible design."""
        
        # Use decision tree to calculate expected performance
        expected_performance = {
            'expected_npv': 0,
            'expected_lcoe': 0,
            'expected_capacity_factor': 0,
            'expected_total_capacity': 0
        }
        
        # Simple calculation based on initial design
        for tech_name in self.config.get_enabled_technologies():
            capacity = flexible_design.get(f'{tech_name}_capacity', 0)
            expected_performance['expected_total_capacity'] += capacity
        
        # Add estimates based on option exercises
        expansion_probability = 0.3  # Simplified assumption
        expected_expansion = sum(
            option.action_parameters.get('additional_capacity', 0) * expansion_probability
            for option in self.flexibility_options 
            if option.option_type == 'expansion'
        ) / max(1, len([o for o in self.flexibility_options if o.option_type == 'expansion']))
        
        expected_performance['expected_total_capacity'] += expected_expansion
        expected_performance['expected_capacity_factor'] = 0.35  # Placeholder
        
        return expected_performance
    
    def _run_scenario_analysis(self, flexible_design: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run scenario analysis for flexible design."""
        
        scenarios = [
            {'name': 'optimistic', 'electricity_price_mult': 1.2, 'performance_mult': 1.1},
            {'name': 'base_case', 'electricity_price_mult': 1.0, 'performance_mult': 1.0},
            {'name': 'pessimistic', 'electricity_price_mult': 0.8, 'performance_mult': 0.9}
        ]
        
        scenario_results = []
        for scenario in scenarios:
            result = {
                'scenario_name': scenario['name'],
                'flexible_npv': 50000000 * scenario['electricity_price_mult'] * scenario['performance_mult'],
                'options_exercised': [],
                'final_capacity': sum(
                    flexible_design.get(f'{tech}_capacity', 0) 
                    for tech in self.config.get_enabled_technologies()
                )
            }
            
            # Determine which options would be exercised
            if scenario['electricity_price_mult'] > 1.1:
                result['options_exercised'].append('expansion')
                result['final_capacity'] *= 1.5
            elif scenario['electricity_price_mult'] < 0.9:
                result['options_exercised'].append('abandonment')
                result['final_capacity'] *= 0.4
            
            scenario_results.append(result)
        
        return scenario_results
    
    def save_results(self, output_dir: str = None) -> str:
        """
        Save flexible design results to file.
        
        Args:
            output_dir: Optional output directory. Defaults to data/{site}/results/flexible/
            
        Returns:
            Path to saved results file
        """
        if self.results is None:
            raise ValueError("No results to save. Run analysis first.")
        
        if output_dir is None:
            package_root = Path(__file__).parent.parent
            output_dir = package_root / "data" / self.config.name.lower() / "results" / "flexible"
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"flexible_results_{timestamp}.json"
        filepath = output_path / filename
        
        # Save results
        with open(filepath, 'w') as f:
            json.dump(self.results.to_dict(), f, indent=2)
        
        print(f"Results saved to: {filepath}")
        return str(filepath)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of flexible design analysis results.
        
        Returns:
            Dictionary with key results summary
        """
        if self.results is None:
            raise ValueError("No results available. Run analysis first.")
        
        return {
            'flexibility_premium': self.results.flexibility_premium,
            'total_option_value': sum(self.results.option_values.values()),
            'most_valuable_option': max(self.results.option_values.items(), key=lambda x: x[1]),
            'recommended_strategy': self.results.optimal_flexible_design.get('flexibility_strategy', {}),
            'expected_capacity': self.results.expected_performance.get('expected_total_capacity', 0),
            'number_of_options': len(self.results.flexibility_options)
        }
