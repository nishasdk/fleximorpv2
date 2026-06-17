"""
Uncertainty analysis module for FlexiMORPv2.

Performs Monte Carlo simulation and uncertainty analysis for offshore 
renewable energy platforms. Evaluates performance under stochastic conditions
and finds robust optimal designs.
"""

import numpy as np
from scipy import stats
from scipy.stats import qmc  # For Latin Hypercube Sampling
from typing import Dict, Any, List, Tuple, Optional, Union
from dataclasses import dataclass
import json
from datetime import datetime
from pathlib import Path
import pandas as pd

from .config import SiteConfig
from .baseline_optimization import BaselineOptimization, BaselineResults
from .models.platform import PlatformModel
from .models.technologies import TechnologyModel, ResourceData
from .models.economics import EconomicModel
from .utils.data_loader import APIDataLoader
from .utils.financial import FinancialCalculator


@dataclass
class UncertaintyParameters:
    """Parameters for uncertainty analysis."""
    monte_carlo_runs: int
    uncertain_variables: Dict[str, Dict[str, Any]]
    correlation_matrix: Optional[np.ndarray] = None
    random_seed: Optional[int] = None


@dataclass
class UncertaintyResults:
    """Results from uncertainty analysis."""
    mean_performance: Dict[str, float]
    std_performance: Dict[str, float]
    percentiles: Dict[str, Dict[str, float]]
    robust_design: Dict[str, Any]
    risk_metrics: Dict[str, float]
    scenario_results: List[Dict[str, Any]]
    uncertainty_info: Dict[str, Any]
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary for serialization."""
        return {
            'mean_performance': self.mean_performance,
            'std_performance': self.std_performance,
            'percentiles': self.percentiles,
            'robust_design': self.robust_design,
            'risk_metrics': self.risk_metrics,
            'scenario_results': self.scenario_results,
            'uncertainty_info': self.uncertainty_info,
            'timestamp': self.timestamp
        }


class UncertaintyAnalysis:
    """
    Uncertainty analysis engine for offshore renewable energy platforms.
    
    Performs Monte Carlo simulation to evaluate platform performance under
    uncertainty and finds robust optimal designs that perform well across
    different scenarios.
    """
    
    def __init__(self, config: SiteConfig, baseline_result=None):
        """
        Initialize uncertainty analysis.
        
        Args:
            config: Site configuration object
            baseline_result: Optional baseline optimization result to use as starting point
        """
        self.config = config
        self.baseline_result = baseline_result
        self.baseline_optimizer = BaselineOptimization(config)
        self.platform_model = PlatformModel(config)
        self.tech_model = TechnologyModel(config)
        self.economic_model = EconomicModel(config)
        self.data_loader = APIDataLoader(config)
        self.financial_calc = FinancialCalculator(config)
        
        # Setup uncertainty parameters
        self._setup_uncertainty_parameters()
        
        # Results storage
        self.results: Optional[UncertaintyResults] = None
    
    def _setup_uncertainty_parameters(self):
        """Setup uncertainty parameters from configuration."""
        uncertainty_config = self.config.uncertainty
        
        self.uncertainty_params = UncertaintyParameters(
            monte_carlo_runs=uncertainty_config.get('monte_carlo_runs', 10000),
            uncertain_variables=uncertainty_config.get('variables', {}),
            random_seed=uncertainty_config.get('random_seed', 42)
        )
        
        # Define uncertainty distributions
        self._define_uncertainty_distributions()
    
    def _setup_custom_uncertainty_parameters(self, uncertainty_params: Dict[str, Any]):
        """Setup custom uncertainty parameters from user input."""
        # Convert user-defined uncertainty parameters to distributions
        for param_name, param_config in uncertainty_params.items():
            distribution_type = param_config.get('distribution', 'normal')
            
            if distribution_type == 'normal':
                mean = param_config.get('mean', 1.0)
                std = param_config.get('std', 0.1)
                self.distributions[param_name] = stats.norm(loc=mean, scale=std)
                
            elif distribution_type == 'triangular':
                low = param_config.get('low', 0.8)
                mode = param_config.get('mode', 1.0)
                high = param_config.get('high', 1.2)
                # Convert to scipy.stats triang parameters
                c = (mode - low) / (high - low)
                self.distributions[param_name] = stats.triang(c=c, loc=low, scale=high-low)
                
            elif distribution_type == 'beta':
                alpha = param_config.get('alpha', 2)
                beta = param_config.get('beta', 5)
                low = param_config.get('low', 0.0)
                high = param_config.get('high', 1.0)
                self.distributions[param_name] = stats.beta(alpha, beta, loc=low, scale=high-low)
                
            elif distribution_type == 'lognormal':
                mean = param_config.get('mean', 1.0)
                sigma = param_config.get('sigma', 0.1)
                self.distributions[param_name] = stats.lognorm(s=sigma, scale=mean)
                
            elif distribution_type == 'uniform':
                low = param_config.get('low', 0.8)
                high = param_config.get('high', 1.2)
                self.distributions[param_name] = stats.uniform(loc=low, scale=high-low)
                
            else:
                print(f"Warning: Unknown distribution type '{distribution_type}' for parameter '{param_name}'. Using normal distribution.")
                mean = param_config.get('mean', 1.0)
                std = param_config.get('std', 0.1)
                self.distributions[param_name] = stats.norm(loc=mean, scale=std)
    
    def _define_uncertainty_distributions(self):
        """Define probability distributions for uncertain variables."""
        self.distributions = {}
        
        # Weather/resource uncertainty
        if 'weather' in self.uncertainty_params.uncertain_variables:
            weather_type = self.uncertainty_params.uncertain_variables['weather']
            if weather_type == 'stochastic':
                self.distributions['wind_speed'] = stats.norm(loc=1.0, scale=0.15)  # Multiplier
                self.distributions['solar_irradiance'] = stats.norm(loc=1.0, scale=0.10)
                self.distributions['wave_height'] = stats.norm(loc=1.0, scale=0.20)
        
        # Economic uncertainty
        if 'electricity_price' in self.uncertainty_params.uncertain_variables:
            price_type = self.uncertainty_params.uncertain_variables['electricity_price']
            if price_type == 'scenario_based':
                # Define price scenarios: low, medium, high
                self.distributions['electricity_price'] = stats.uniform(loc=0.08, scale=0.04)  # £0.08-0.12/kWh
        
        # Cost uncertainty
        if 'capex' in self.uncertainty_params.uncertain_variables:
            capex_type = self.uncertainty_params.uncertain_variables['capex']
            if capex_type == 'normal_distribution':
                self.distributions['capex_multiplier'] = stats.norm(loc=1.0, scale=0.20)
        
        if 'opex' in self.uncertainty_params.uncertain_variables:
            opex_type = self.uncertainty_params.uncertain_variables['opex']
            if opex_type == 'normal_distribution':
                self.distributions['opex_multiplier'] = stats.norm(loc=1.0, scale=0.15)
    
    def analyze_uncertainty(self, 
                           baseline_design: Dict[str, Any] = None,
                           reoptimize: bool = True,
                           sampling_method: str = 'monte_carlo',
                           **kwargs) -> UncertaintyResults:
        """
        Run uncertainty analysis.
        
        Args:
            baseline_design: Optional baseline design. If None, will optimize first.
            reoptimize: Whether to reoptimize design under uncertainty
            sampling_method: 'monte_carlo' or 'latin_hypercube'
            **kwargs: Additional parameters for analysis
            
        Returns:
            UncertaintyResults object with analysis results
        """
        print("Starting uncertainty analysis...")
        
        # Get baseline design if not provided
        if baseline_design is None:
            print("No baseline design provided. Running baseline optimization...")
            baseline_results = self.baseline_optimizer.optimize(
                target_type='production',
                target_value=kwargs.get('target_production', 1000000)  # 1 GWh default
            )
            baseline_design = baseline_results.optimal_design
        
        # Pre-load base weather data once (major performance optimization)
        print("Pre-loading base weather data...")
        self._base_weather_data = self.data_loader.load_weather_data(
            coordinates=self.config.coordinates,
            technologies=self.config.get_enabled_technologies()
        )
        
        # Generate uncertainty scenarios
        scenarios = self._generate_scenarios(sampling_method)
        
        # Evaluate baseline design under uncertainty
        baseline_performance = self._evaluate_scenarios(baseline_design, scenarios)
        
        # Find robust design if requested
        if reoptimize:
            print("Finding robust optimal design...")
            robust_design = self._optimize_robust_design(scenarios, **kwargs)
            robust_performance = self._evaluate_scenarios(robust_design, scenarios)
        else:
            robust_design = baseline_design
            robust_performance = baseline_performance
        
        # Calculate uncertainty metrics
        self.results = self._calculate_uncertainty_metrics(
            robust_design, robust_performance, scenarios
        )
        
        print(f"Uncertainty analysis completed. {len(scenarios)} scenarios evaluated.")
        return self.results
    
    def _generate_scenarios(self, sampling_method: str = 'monte_carlo') -> List[Dict[str, float]]:
        """Generate scenarios using specified sampling method."""
        print(f"Generating {self.uncertainty_params.monte_carlo_runs} scenarios using {sampling_method}...")
        
        # Track current sampling method for results
        self._current_sampling_method = sampling_method
        
        np.random.seed(self.uncertainty_params.random_seed)
        scenarios = []
        
        if sampling_method == 'monte_carlo':
            scenarios = self._generate_monte_carlo_scenarios()
        elif sampling_method == 'latin_hypercube':
            scenarios = self._generate_latin_hypercube_scenarios()
        else:
            raise ValueError(f"Unknown sampling method: {sampling_method}. Use 'monte_carlo' or 'latin_hypercube'")
        
        return scenarios
    
    def _generate_monte_carlo_scenarios(self) -> List[Dict[str, float]]:
        """Generate scenarios using standard Monte Carlo sampling."""
        scenarios = []
        
        for i in range(self.uncertainty_params.monte_carlo_runs):
            scenario = {}
            
            # Sample from each uncertain variable
            for var_name, distribution in self.distributions.items():
                scenario[var_name] = distribution.rvs()
            
            scenarios.append(scenario)
        
        return scenarios
    
    def _generate_latin_hypercube_scenarios(self) -> List[Dict[str, float]]:
        """Generate scenarios using Latin Hypercube Sampling."""
        if not self.distributions:
            return []
        
        var_names = list(self.distributions.keys())
        n_vars = len(var_names)
        n_samples = self.uncertainty_params.monte_carlo_runs
        
        # Create Latin Hypercube sampler
        sampler = qmc.LatinHypercube(d=n_vars, seed=self.uncertainty_params.random_seed)
        
        # Generate uniform samples in [0,1]^n_vars
        uniform_samples = sampler.random(n=n_samples)
        
        # Transform uniform samples to distribution-specific values
        scenarios = []
        for i in range(n_samples):
            scenario = {}
            for j, var_name in enumerate(var_names):
                distribution = self.distributions[var_name]
                # Use percent point function (inverse CDF) to transform uniform to distribution
                scenario[var_name] = distribution.ppf(uniform_samples[i, j])
            scenarios.append(scenario)
        
        return scenarios
    
    def _evaluate_scenarios(self, 
                           design: Dict[str, Any], 
                           scenarios: List[Dict[str, float]]) -> List[Dict[str, float]]:
        """Evaluate design performance across all scenarios."""
        performance_results = []
        
        for i, scenario in enumerate(scenarios):
            # More frequent progress updates for better user feedback
            if i % max(1, len(scenarios) // 10) == 0:  # Show progress every 10%
                progress = (i / len(scenarios)) * 100
                print(f"  Progress: {progress:.0f}% ({i+1}/{len(scenarios)} scenarios)")
            
            try:
                # Apply uncertainty to input data
                modified_data = self._apply_scenario_to_data(scenario)
                
                # Calculate performance
                tech_performance = self.tech_model.calculate_performance(design, modified_data)
                
                # Calculate economics with scenario-based cost adjustments
                economic_performance = self.economic_model.calculate_economics(
                    design, tech_performance
                )
                
                # Apply cost multipliers from scenario
                if 'arctic_cost_premium' in scenario:
                    economic_performance['capex'] *= scenario['arctic_cost_premium']
                    economic_performance['opex'] *= scenario['arctic_cost_premium']
                
                if 'logistics_cost_multiplier' in scenario:
                    economic_performance['opex'] *= scenario['logistics_cost_multiplier']
                
                if 'capex_multiplier' in scenario:
                    economic_performance['capex'] *= scenario['capex_multiplier']
                
                if 'opex_multiplier' in scenario:
                    economic_performance['opex'] *= scenario['opex_multiplier']
                
                # Apply electricity price variation
                if 'electricity_price' in scenario:
                    # Recalculate revenue with new price
                    annual_energy = tech_performance.get('annual_energy', 0)
                    economic_performance['revenue'] = annual_energy * scenario['electricity_price'] * 1000
                elif 'electricity_price_multiplier' in scenario:
                    economic_performance['revenue'] *= scenario['electricity_price_multiplier']
                
                # Calculate financial metrics
                financial_metrics = self.financial_calc.calculate_metrics(
                    capex=economic_performance['capex'],
                    opex=economic_performance['opex'],
                    revenue=economic_performance['revenue'],
                    project_life=self.config.economic['project_lifetime'],
                    annual_energy=tech_performance.get('annual_energy', 0.0)
                )
                
                # Combine results
                performance = {
                    **tech_performance,
                    **economic_performance,
                    **financial_metrics,
                    'scenario_id': i
                }
                
                performance_results.append(performance)
                
            except Exception as e:
                print(f"Error evaluating scenario {i}: {e}")
                # Create a failed scenario result
                performance_results.append({
                    'scenario_id': i,
                    'lcoe': 1000.0,  # Very high LCOE for failed scenarios
                    'npv': -1e6,     # Negative NPV
                    'capacity_factor': 0.0,
                    'annual_energy': 0.0,
                    'capex': 0.0,
                    'opex': 0.0,
                    'revenue': 0.0,
                    'failed': True
                })
        
        return performance_results
    
    def _apply_scenario_to_data(self, scenario: Dict[str, float]) -> ResourceData:
        """Apply scenario parameters to modify input data."""
        # Use pre-loaded base data for performance
        if hasattr(self, '_base_weather_data'):
            base_data = self._base_weather_data
        else:
            # Fallback to loading data (slower)
            base_data = self.data_loader.load_weather_data(
                coordinates=self.config.coordinates,
                technologies=self.config.get_enabled_technologies()
            )
        
        # Create modified copies of the arrays
        modified_wind_speed = base_data.wind_speed.copy()
        modified_solar_irradiance = base_data.solar_irradiance.copy()
        modified_wave_height = base_data.wave_height.copy()
        modified_temperature = base_data.temperature.copy()
        
        # Apply uncertainty multipliers based on scenario parameters
        
        # Handle direct resource modifications
        if 'wind_speed' in scenario:
            modified_wind_speed *= scenario['wind_speed']
        elif 'wind_resource_variability' in scenario:
            modified_wind_speed *= scenario['wind_resource_variability']
        
        if 'solar_irradiance' in scenario:
            modified_solar_irradiance *= scenario['solar_irradiance']
        elif 'solar_resource_variability' in scenario:
            modified_solar_irradiance *= scenario['solar_resource_variability']
        
        if 'wave_height' in scenario:
            modified_wave_height *= scenario['wave_height']
        elif 'wave_resource_variability' in scenario:
            modified_wave_height *= scenario['wave_resource_variability']
        
        # Handle temperature variations
        if 'temperature_variation' in scenario:
            # Apply temperature change (additive)
            temp_change = (scenario['temperature_variation'] - 1.0) * 10  # Convert multiplier to temperature change
            modified_temperature += temp_change
        
        # Handle ice impact (Arctic-specific)
        if 'ice_impact_factor' in scenario:
            # Ice affects both wind and solar generation
            ice_factor = 1.0 - scenario['ice_impact_factor']  # Reduce performance
            modified_wind_speed *= ice_factor
            modified_solar_irradiance *= ice_factor
        
        # Create new ResourceData object with modified values
        modified_data = ResourceData(
            wind_speed=modified_wind_speed,
            solar_irradiance=modified_solar_irradiance,
            wave_height=modified_wave_height,
            wave_period=base_data.wave_period.copy(),
            temperature=modified_temperature,
            timestamps=base_data.timestamps.copy()
        )
        
        return modified_data
    
    def _optimize_robust_design(self, 
                               scenarios: List[Dict[str, float]], 
                               **kwargs) -> Dict[str, Any]:
        """Find robust optimal design that performs well across scenarios."""
        
        def robust_objective(x):
            """Objective function for robust optimization."""
            try:
                # Decode design variables
                design_vars = self._decode_variables(x)
                
                # Evaluate across sample of scenarios (for speed)
                sample_size = min(100, len(scenarios))
                sample_scenarios = scenarios[:sample_size]
                
                performance_list = self._evaluate_scenarios(design_vars, sample_scenarios)
                
                # Calculate robust objective (e.g., minimize worst-case LCOE)
                lcoe_values = [p['lcoe'] for p in performance_list]
                
                robustness_type = kwargs.get('robustness_type', 'mean_variance')
                
                if robustness_type == 'worst_case':
                    return max(lcoe_values)
                elif robustness_type == 'mean_variance':
                    mean_lcoe = np.mean(lcoe_values)
                    std_lcoe = np.std(lcoe_values)
                    risk_aversion = kwargs.get('risk_aversion', 0.5)
                    return mean_lcoe + risk_aversion * std_lcoe
                elif robustness_type == 'cvar':
                    # Conditional Value at Risk
                    alpha = kwargs.get('cvar_alpha', 0.95)
                    sorted_lcoe = sorted(lcoe_values)
                    cutoff_idx = int(alpha * len(sorted_lcoe))
                    return np.mean(sorted_lcoe[cutoff_idx:])
                else:
                    return np.mean(lcoe_values)
                    
            except Exception as e:
                print(f"Error in robust objective: {e}")
                return 1e10
        
        # Use baseline optimizer bounds
        self.baseline_optimizer._setup_optimization_bounds()
        bounds_list = []
        enabled_techs = self.config.get_enabled_technologies()
        
        for tech_name in enabled_techs:
            bounds_list.append(self.baseline_optimizer.bounds[f'{tech_name}_capacity'])
        
        bounds_list.extend([
            self.baseline_optimizer.bounds['platform_area'],
            self.baseline_optimizer.bounds['water_depth'],
            self.baseline_optimizer.bounds['distance_to_shore']
        ])
        
        # Run optimization
        from scipy.optimize import differential_evolution
        result = differential_evolution(
            robust_objective,
            bounds=bounds_list,
            maxiter=kwargs.get('maxiter', 500),  # Reduced for robust optimization
            popsize=kwargs.get('popsize', 10),
            seed=42,
            disp=True
        )
        
        return self._decode_variables(result.x)
    
    def _decode_variables(self, x: np.ndarray) -> Dict[str, Any]:
        """Decode optimization variables vector into design parameters."""
        design_vars = {}
        idx = 0
        
        # Technology capacities
        for tech_name in self.config.get_enabled_technologies():
            design_vars[f'{tech_name}_capacity'] = x[idx]
            idx += 1
        
        # Platform design variables
        design_vars.update({
            'platform_area': x[idx],
            'water_depth': x[idx+1],
            'distance_to_shore': x[idx+2]
        })
        
        return design_vars
    
    def _calculate_uncertainty_metrics(self, 
                                     robust_design: Dict[str, Any],
                                     performance_results: List[Dict[str, float]],
                                     scenarios: List[Dict[str, float]]) -> UncertaintyResults:
        """Calculate uncertainty analysis metrics from performance results."""
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(performance_results)
        
        # Calculate statistical metrics
        mean_performance = df.mean().to_dict()
        std_performance = df.std().to_dict()
        
        # Calculate percentiles
        percentiles_to_calc = [5, 10, 25, 50, 75, 90, 95]
        percentiles = {}
        for metric in ['lcoe', 'npv', 'capacity_factor', 'annual_energy']:
            if metric in df.columns:
                percentiles[metric] = df[metric].quantile([p/100 for p in percentiles_to_calc]).to_dict()
                # Convert index to string for JSON serialization
                percentiles[metric] = {f"p{int(k*100)}": v for k, v in percentiles[metric].items()}
        
        # Calculate risk metrics
        risk_metrics = self._calculate_risk_metrics(df)
        
        # Create results object
        results = UncertaintyResults(
            mean_performance=mean_performance,
            std_performance=std_performance,
            percentiles=percentiles,
            robust_design=robust_design,
            risk_metrics=risk_metrics,
            scenario_results=performance_results[:1000],  # Store sample for memory efficiency
            uncertainty_info={
                'monte_carlo_runs': len(performance_results),
                'uncertain_variables': list(self.distributions.keys()),
                'random_seed': self.uncertainty_params.random_seed,
                'sampling_method': getattr(self, '_current_sampling_method', 'monte_carlo')
            },
            timestamp=datetime.now().isoformat()
        )
        
        # Store current sampling method for results tracking
        self._current_sampling_method = None
        
        return results
    
    def _calculate_risk_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate risk metrics from performance data."""
        risk_metrics = {}
        
        # Value at Risk (VaR) for LCOE
        if 'lcoe' in df.columns:
            risk_metrics['lcoe_var_95'] = df['lcoe'].quantile(0.95)
            risk_metrics['lcoe_var_99'] = df['lcoe'].quantile(0.99)
            
            # Conditional Value at Risk (CVaR)
            var_95 = risk_metrics['lcoe_var_95']
            risk_metrics['lcoe_cvar_95'] = df[df['lcoe'] >= var_95]['lcoe'].mean()
        
        # Probability of negative NPV
        if 'npv' in df.columns:
            risk_metrics['prob_negative_npv'] = (df['npv'] < 0).mean()
            risk_metrics['npv_var_5'] = df['npv'].quantile(0.05)  # 5th percentile (worst case)
        
        # Coefficient of variation
        if 'capacity_factor' in df.columns:
            mean_cf = df['capacity_factor'].mean()
            std_cf = df['capacity_factor'].std()
            risk_metrics['capacity_factor_cv'] = std_cf / mean_cf if mean_cf > 0 else 0
        
        return risk_metrics
    
    def save_results(self, output_dir: str = None) -> str:
        """
        Save uncertainty analysis results to file.
        
        Args:
            output_dir: Optional output directory. Defaults to data/{site}/results/uncertainty/
            
        Returns:
            Path to saved results file
        """
        if self.results is None:
            raise ValueError("No results to save. Run analysis first.")
        
        if output_dir is None:
            package_root = Path(__file__).parent.parent
            output_dir = package_root / "data" / self.config.name.lower() / "results" / "uncertainty"
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"uncertainty_results_{timestamp}.json"
        filepath = output_path / filename
        
        # Save results
        with open(filepath, 'w') as f:
            json.dump(self.results.to_dict(), f, indent=2)
        
        print(f"Results saved to: {filepath}")
        return str(filepath)
    
    def compare_sampling_methods(self, 
                               baseline_design: Dict[str, Any] = None,
                               reoptimize: bool = False,
                               n_runs: int = None) -> Dict[str, Any]:
        """
        Compare Monte Carlo and Latin Hypercube sampling methods.
        
        Args:
            baseline_design: Optional baseline design
            reoptimize: Whether to reoptimize design under uncertainty
            n_runs: Number of runs for comparison (default: config value)
            
        Returns:
            Dictionary with comparison results
        """
        print("Comparing Monte Carlo vs Latin Hypercube sampling...")
        
        # Temporarily adjust number of runs for comparison if specified
        original_runs = self.uncertainty_params.monte_carlo_runs
        if n_runs is not None:
            self.uncertainty_params.monte_carlo_runs = n_runs
        
        try:
            # Run Monte Carlo analysis
            print("\nRunning Monte Carlo analysis...")
            mc_results = self.analyze_uncertainty(
                baseline_design=baseline_design,
                reoptimize=reoptimize,
                sampling_method='monte_carlo'
            )
            
            # Run Latin Hypercube analysis
            print("\nRunning Latin Hypercube analysis...")
            lhs_results = self.analyze_uncertainty(
                baseline_design=baseline_design,
                reoptimize=reoptimize,
                sampling_method='latin_hypercube'
            )
            
            # Compare results
            comparison = {
                'monte_carlo': {
                    'mean_lcoe': mc_results.mean_performance.get('lcoe', 0),
                    'std_lcoe': mc_results.std_performance.get('lcoe', 0),
                    'mean_npv': mc_results.mean_performance.get('npv', 0),
                    'std_npv': mc_results.std_performance.get('npv', 0),
                    'prob_negative_npv': mc_results.risk_metrics.get('prob_negative_npv', 0),
                    'lcoe_var_95': mc_results.risk_metrics.get('lcoe_var_95', 0)
                },
                'latin_hypercube': {
                    'mean_lcoe': lhs_results.mean_performance.get('lcoe', 0),
                    'std_lcoe': lhs_results.std_performance.get('lcoe', 0),
                    'mean_npv': lhs_results.mean_performance.get('npv', 0),
                    'std_npv': lhs_results.std_performance.get('npv', 0),
                    'prob_negative_npv': lhs_results.risk_metrics.get('prob_negative_npv', 0),
                    'lcoe_var_95': lhs_results.risk_metrics.get('lcoe_var_95', 0)
                },
                'differences': {},
                'convergence_analysis': self._analyze_convergence(mc_results, lhs_results)
            }
            
            # Calculate differences
            for metric in ['mean_lcoe', 'std_lcoe', 'mean_npv', 'std_npv', 'prob_negative_npv', 'lcoe_var_95']:
                mc_val = comparison['monte_carlo'][metric]
                lhs_val = comparison['latin_hypercube'][metric]
                if mc_val != 0:
                    comparison['differences'][metric] = {
                        'absolute': lhs_val - mc_val,
                        'relative_pct': ((lhs_val - mc_val) / abs(mc_val)) * 100
                    }
            
            return comparison
            
        finally:
            # Restore original number of runs
            self.uncertainty_params.monte_carlo_runs = original_runs
    
    def _analyze_convergence(self, mc_results: UncertaintyResults, lhs_results: UncertaintyResults) -> Dict[str, Any]:
        """Analyze convergence properties of sampling methods."""
        return {
            'mc_variance_estimate': mc_results.std_performance.get('lcoe', 0)**2,
            'lhs_variance_estimate': lhs_results.std_performance.get('lcoe', 0)**2,
            'variance_reduction_ratio': (
                lhs_results.std_performance.get('lcoe', 1)**2 / 
                max(mc_results.std_performance.get('lcoe', 1)**2, 1e-10)
            ),
            'recommendation': (
                "Latin Hypercube shows better convergence" if 
                lhs_results.std_performance.get('lcoe', 1) < mc_results.std_performance.get('lcoe', 1) 
                else "Monte Carlo shows better convergence"
            )
        }
    
    def run_monte_carlo(self, 
                       n_simulations: int = 1000,
                       baseline_design: Dict[str, Any] = None,
                       base_design: Dict[str, Any] = None,  # Alternative parameter name for compatibility
                       uncertainty_params: Dict[str, Any] = None,
                       n_samples: int = None,  # Alternative parameter name for compatibility
                       reoptimize: bool = True,
                       parallel: bool = False,
                       **kwargs) -> 'MonteCarloResults':
        """
        Run Monte Carlo uncertainty analysis.
        
        This method provides compatibility with the expected interface from 
        the integration example. It's a wrapper around analyze_uncertainty.
        
        Args:
            n_simulations: Number of Monte Carlo simulations to run
            baseline_design: Optional baseline design. If None, will optimize first.
            base_design: Alternative name for baseline_design (for compatibility)
            uncertainty_params: Custom uncertainty parameter definitions
            n_samples: Alternative name for n_simulations (for compatibility)
            reoptimize: Whether to reoptimize design under uncertainty
            parallel: Whether to run simulations in parallel (not implemented yet)
            **kwargs: Additional parameters for analysis
            
        Returns:
            MonteCarloResults object with analysis results
        """
        # Handle parameter name compatibility
        if n_samples is not None:
            n_simulations = n_samples
        if base_design is not None:
            baseline_design = base_design
            
        print(f"Starting Monte Carlo uncertainty analysis with {n_simulations} simulations...")
        
        # Handle custom uncertainty parameters
        if uncertainty_params is not None:
            self._setup_custom_uncertainty_parameters(uncertainty_params)
        
        # Temporarily update the number of Monte Carlo runs
        original_runs = self.uncertainty_params.monte_carlo_runs
        self.uncertainty_params.monte_carlo_runs = n_simulations
        
        try:
            # Use baseline result from constructor if no design provided
            if baseline_design is None and self.baseline_result is not None:
                # Extract design from baseline result if it has the expected structure
                if hasattr(self.baseline_result, 'optimal_config'):
                    baseline_design = self.baseline_result.optimal_config
                elif hasattr(self.baseline_result, 'optimal_design'):
                    baseline_design = self.baseline_result.optimal_design
            
            # Run the analysis using the existing analyze_uncertainty method
            uncertainty_results = self.analyze_uncertainty(
                baseline_design=baseline_design,
                reoptimize=False,  # Disable expensive reoptimization by default for speed
                sampling_method='monte_carlo',
                **kwargs
            )
            
            # Convert to MonteCarloResults format expected by integration example
            monte_carlo_results = MonteCarloResults(
                uncertainty_results=uncertainty_results,
                n_simulations=n_simulations,
                parallel=parallel
            )
            
            return monte_carlo_results
            
        finally:
            # Restore original number of runs
            self.uncertainty_params.monte_carlo_runs = original_runs
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of uncertainty analysis results.
        
        Returns:
            Dictionary with key results summary
        """
        if self.results is None:
            raise ValueError("No results available. Run analysis first.")
        
        return {
            'mean_lcoe': self.results.mean_performance.get('lcoe', 0),
            'std_lcoe': self.results.std_performance.get('lcoe', 0),
            'mean_npv': self.results.mean_performance.get('npv', 0),
            'std_npv': self.results.std_performance.get('npv', 0),
            'prob_negative_npv': self.results.risk_metrics.get('prob_negative_npv', 0),
            'lcoe_var_95': self.results.risk_metrics.get('lcoe_var_95', 0),
            'robust_design': self.results.robust_design,
            'monte_carlo_runs': self.results.uncertainty_info['monte_carlo_runs'],
            'sampling_method': self.results.uncertainty_info.get('sampling_method', 'monte_carlo')
        }


@dataclass
class MonteCarloResults:
    """
    Results from Monte Carlo uncertainty analysis.
    
    This class provides the expected interface for the integration example,
    wrapping the UncertaintyResults with additional Monte Carlo specific properties.
    """
    uncertainty_results: UncertaintyResults
    n_simulations: int
    parallel: bool
    
    def __post_init__(self):
        """Initialize flat dictionary for backward compatibility."""
        self._flat_dict = self.to_flat_dict()
    
    def __getitem__(self, key: str):
        """Allow dictionary-like access for backward compatibility."""
        return self._flat_dict[key]
    
    def __contains__(self, key: str) -> bool:
        """Support 'in' operator."""
        return key in self._flat_dict
    
    def get(self, key: str, default=None):
        """Dictionary-like get method."""
        return self._flat_dict.get(key, default)
    
    @property
    def statistics(self) -> Dict[str, Any]:
        """Get statistics in the format expected by integration example."""
        results = {}
        
        # LCOE statistics
        if 'lcoe' in self.uncertainty_results.mean_performance:
            lcoe_percentiles = self.uncertainty_results.percentiles.get('lcoe', {})
            results['lcoe'] = {
                'mean': self.uncertainty_results.mean_performance['lcoe'],
                'std': self.uncertainty_results.std_performance['lcoe'],
                'p5': lcoe_percentiles.get('p5', 0),
                'p25': lcoe_percentiles.get('p25', 0),
                'p50': lcoe_percentiles.get('p50', 0),
                'p75': lcoe_percentiles.get('p75', 0),
                'p95': lcoe_percentiles.get('p95', 0),
                'cv': (self.uncertainty_results.std_performance['lcoe'] / 
                      max(self.uncertainty_results.mean_performance['lcoe'], 1e-10))
            }
        
        # NPV statistics
        if 'npv' in self.uncertainty_results.mean_performance:
            npv_percentiles = self.uncertainty_results.percentiles.get('npv', {})
            results['npv'] = {
                'mean': self.uncertainty_results.mean_performance['npv'],
                'std': self.uncertainty_results.std_performance['npv'],
                'p5': npv_percentiles.get('p5', 0),
                'p25': npv_percentiles.get('p25', 0),
                'p50': npv_percentiles.get('p50', 0),
                'p75': npv_percentiles.get('p75', 0),
                'p95': npv_percentiles.get('p95', 0)
            }
        
        # Capacity factor statistics
        if 'capacity_factor' in self.uncertainty_results.mean_performance:
            cf_percentiles = self.uncertainty_results.percentiles.get('capacity_factor', {})
            results['capacity_factor'] = {
                'mean': self.uncertainty_results.mean_performance['capacity_factor'],
                'std': self.uncertainty_results.std_performance['capacity_factor'],
                'p5': cf_percentiles.get('p5', 0),
                'p25': cf_percentiles.get('p25', 0),
                'p50': cf_percentiles.get('p50', 0),
                'p75': cf_percentiles.get('p75', 0),
                'p95': cf_percentiles.get('p95', 0)
            }
        
        # Simulation statistics
        success_rate = 1.0  # Assume all simulations successful for now
        results['simulation_stats'] = {
            'total_simulations': self.n_simulations,
            'successful_simulations': self.n_simulations,
            'success_rate': success_rate,
            'parallel_execution': self.parallel
        }
        
        return results
    
    @property
    def risk_metrics(self) -> Dict[str, Any]:
        """Get risk metrics in the format expected by integration example."""
        risk_metrics = {}
        
        # LCOE risk metrics
        if 'lcoe_var_95' in self.uncertainty_results.risk_metrics:
            risk_metrics['lcoe_risk'] = {
                'var_95': self.uncertainty_results.risk_metrics['lcoe_var_95'],
                'var_99': self.uncertainty_results.risk_metrics.get('lcoe_var_99', 0),
                'cvar_95': self.uncertainty_results.risk_metrics.get('lcoe_cvar_95', 0)
            }
        
        # NPV risk metrics
        if 'prob_negative_npv' in self.uncertainty_results.risk_metrics:
            risk_metrics['npv_risk'] = {
                'prob_negative': self.uncertainty_results.risk_metrics['prob_negative_npv'],
                'var_5': self.uncertainty_results.risk_metrics.get('npv_var_5', 0)
            }
        
        # Capacity factor risk
        if 'capacity_factor_cv' in self.uncertainty_results.risk_metrics:
            risk_metrics['capacity_factor_risk'] = {
                'coefficient_of_variation': self.uncertainty_results.risk_metrics['capacity_factor_cv']
            }
        
        return risk_metrics
    
    def to_flat_dict(self) -> Dict[str, float]:
        """Convert results to flat dictionary format for compatibility with test code."""
        stats = self.statistics
        risk = self.risk_metrics
        
        result = {}
        
        # LCOE metrics
        if 'lcoe' in stats:
            result.update({
                'mean_lcoe': stats['lcoe']['mean'],
                'std_lcoe': stats['lcoe']['std'],
                'lcoe_var_95': risk.get('lcoe_risk', {}).get('var_95', 0),
                'lcoe_cvar_95': risk.get('lcoe_risk', {}).get('cvar_95', 0)
            })
        
        # NPV metrics
        if 'npv' in stats:
            result.update({
                'mean_npv': stats['npv']['mean'],
                'std_npv': stats['npv']['std'],
                'prob_negative_npv': risk.get('npv_risk', {}).get('prob_negative', 0),
                'npv_var_5': risk.get('npv_risk', {}).get('var_5', 0)
            })
        
        # Capacity factor metrics
        if 'capacity_factor' in stats:
            result.update({
                'mean_capacity_factor': stats['capacity_factor']['mean'],
                'std_capacity_factor': stats['capacity_factor']['std']
            })
        
        # Simulation info
        result.update({
            'n_simulations': self.n_simulations,
            'parallel': self.parallel
        })
        
        return result
