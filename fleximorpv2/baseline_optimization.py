"""
Baseline optimization module for FlexiMORPv2.

Performs deterministic optimization of offshore renewable energy platforms
under perfect information conditions. Finds optimal design parameters for
location, technology mix, and production targets.
"""

import numpy as np
from scipy.optimize import minimize, differential_evolution, LinearConstraint
from typing import Dict, Any, List, Tuple, Optional, Union
from dataclasses import dataclass
import json
from datetime import datetime
from pathlib import Path

from .config import SiteConfig
from .models.platform import PlatformModel
from .models.technologies import TechnologyModel
from .models.economics import EconomicModel
from .utils.data_loader import APIDataLoader
from .utils.optimization import OptimizationUtils
from .utils.financial import FinancialCalculator


@dataclass
class OptimizationTarget:
    """Represents the optimization target specified by user."""
    target_type: str  # 'location', 'technologies', 'production'
    target_value: Any
    constraints: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.constraints is None:
            self.constraints = {}


@dataclass
class BaselineResults:
    """Results from baseline optimization."""
    optimal_design: Dict[str, Any]
    objective_value: float
    technology_capacities: Dict[str, float]
    financial_metrics: Dict[str, float]
    technical_metrics: Dict[str, float]
    optimization_info: Dict[str, Any]
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary for serialization."""
        return {
            'optimal_design': self.optimal_design,
            'objective_value': self.objective_value,
            'technology_capacities': self.technology_capacities,
            'financial_metrics': self.financial_metrics,
            'technical_metrics': self.technical_metrics,
            'optimization_info': self.optimization_info,
            'timestamp': self.timestamp
        }


class BaselineOptimization:
    """
    Baseline optimization engine for offshore renewable energy platforms.
    
    Performs deterministic optimization to find optimal platform design
    under perfect information conditions. Supports multiple optimization
    targets and objectives.
    """
    
    def __init__(self, config: SiteConfig):
        """
        Initialize baseline optimization.
        
        Args:
            config: Site configuration object
        """
        self.config = config
        self.platform_model = PlatformModel(config)
        self.tech_model = TechnologyModel(config)
        self.economic_model = EconomicModel(config)
        self.data_loader = APIDataLoader(config)
        self.financial_calc = FinancialCalculator(config)
        
        # Optimization bounds and constraints
        self._setup_optimization_bounds()
        
        # Results storage
        self.results: Optional[BaselineResults] = None
    
    def _setup_optimization_bounds(self):
        """Set up optimization variable bounds based on configuration."""
        self.bounds = {}
        self.constraints_list = []
        
        # Technology capacity bounds
        for tech_name in self.config.get_enabled_technologies():
            tech_config = self.config.technologies[tech_name]
            max_capacity = self.config.optimization.get('constraints', {}).get('max_total_capacity', 500)
            self.bounds[f'{tech_name}_capacity'] = (0, max_capacity)
        
        # Platform design bounds
        self.bounds.update({
            'platform_area': (1000, 50000),    # m²
            'water_depth': (20, 200),          # meters
            'distance_to_shore': (5, 100),     # km
        })
    
    def optimize(self, 
                target_type: str, 
                target_value: Any,
                method: str = 'differential_evolution',
                **kwargs) -> BaselineResults:
        """
        Run baseline optimization for specified target.
        
        Args:
            target_type: Type of optimization target ('location', 'technologies', 'production')
            target_value: Target specification (coordinates, tech list, or kWh)
            method: Optimization method ('scipy', 'differential_evolution', 'genetic')
            **kwargs: Additional optimization parameters
            
        Returns:
            BaselineResults object with optimization results
            
        Raises:
            ValueError: If target type is invalid or optimization fails
        """
        print(f"Starting baseline optimization for target: {target_type}")
        
        # Create optimization target
        target = OptimizationTarget(
            target_type=target_type,
            target_value=target_value,
            constraints=kwargs.get('constraints', {})
        )
        
        # Load data for optimization
        self._load_optimization_data(target)

        if not hasattr(self, 'resource_data') or not self.resource_data:
            raise ValueError("Resource data could not be loaded for optimization.")
        
        # Set up objective function
        objective_func = self._create_objective_function(target)
        
        # Run optimization
        if method == 'differential_evolution':
            result = self._optimize_differential_evolution(objective_func, target, **kwargs)
        elif method == 'scipy':
            result = self._optimize_scipy(objective_func, target, **kwargs)
        else:
            raise ValueError(f"Unknown optimization method: {method}")
        
        # Process and store results
        self.results = self._process_optimization_result(result, target)
        
        print(f"Optimization completed. Objective value: {self.results.objective_value:.2f}")
        return self.results
    
    def _load_optimization_data(self, target: OptimizationTarget):
        """Load required data for optimization based on target."""
        print("Loading optimization data...")
        
        if target.target_type == 'location':
            # Load weather and resource data for specified coordinates
            self.resource_data = self.data_loader.load_weather_data(
                coordinates=target.target_value,
                technologies=self.config.get_enabled_technologies()
            )
        elif target.target_type == 'technologies':
            # Load data for specified technology mix
            self.resource_data = self.data_loader.load_weather_data(
                coordinates=self.config.coordinates,
                technologies=target.target_value
            )
        elif target.target_type == 'production':
            # Load data for production optimization
            self.resource_data = self.data_loader.load_weather_data(
                coordinates=self.config.coordinates,
                technologies=self.config.get_enabled_technologies()
            )
        else:
            raise ValueError(f"Invalid target type: {target.target_type}")
    
    def _create_objective_function(self, target: OptimizationTarget):
        """Create objective function for optimization."""
        
        def objective(x):
            """
            Objective function for optimization.
            
            Args:
                x: Optimization variables vector
                
            Returns:
                Objective value (to be minimized)
            """
            try:
                # Decode optimization variables
                design_vars = self._decode_variables(x, target)
                
                # Calculate platform performance
                performance = self._evaluate_platform_performance(design_vars, target)
                
                # Calculate objective based on optimization type
                objective_type = self.config.optimization.get('objective', 'minimize_lcoe')
                
                if objective_type == 'minimize_lcoe':
                    return performance['lcoe']
                elif objective_type == 'maximize_npv':
                    return -performance['npv']  # Negative for minimization
                elif objective_type == 'minimize_capex':
                    return performance['capex']
                elif objective_type == 'maximize_capacity_factor':
                    return -performance['capacity_factor']
                else:
                    raise ValueError(f"Unknown objective type: {objective_type}")
                    
            except Exception as e:
                print(f"Error in objective function: {e}")
                return 1e10  # Return large penalty for invalid solutions
        
        return objective
    
    def _decode_variables(self, x: np.ndarray, target: OptimizationTarget) -> Dict[str, Any]:
        """Decode optimization variables vector into design parameters."""
        design_vars = {}
        idx = 0
        
        # Technology capacities
        for tech_name in self.config.get_enabled_technologies():
            # FIXED: Only check tech_name in target_value when target_type is 'technologies'
            # and target_value is actually a list/iterable
            if (target.target_type == 'technologies' and 
                hasattr(target.target_value, '__iter__') and 
                not isinstance(target.target_value, str) and
                tech_name not in target.target_value):
                design_vars[f'{tech_name}_capacity'] = 0.0
            else:
                design_vars[f'{tech_name}_capacity'] = x[idx]
                idx += 1
        
        # Platform design variables - only add if we have enough variables
        remaining_vars = len(x) - idx
        if remaining_vars >= 3:
            design_vars.update({
                'platform_area': x[idx] if target.target_type != 'location' else 10000,
                'water_depth': x[idx+1] if target.target_type != 'location' else 50,
                'distance_to_shore': x[idx+2] if target.target_type != 'location' else 20
            })
        else:
            # Use defaults if not enough variables
            design_vars.update({
                'platform_area': 10000,
                'water_depth': 50,
                'distance_to_shore': 20
            })
        
        return design_vars
    
    def _evaluate_platform_performance(self, 
                                     design_vars: Dict[str, Any], 
                                     target: OptimizationTarget) -> Dict[str, float]:
        """Evaluate platform performance for given design variables."""
        
        # === Hard Constraints on Capacity and CapEx ===
        max_total_capacity = self.config.optimization.get('constraints', {}).get('max_total_capacity', 2.0)  # MW
        max_investment = self.config.optimization.get('constraints', {}).get('max_investment', 5_000_000)   # USD

        # Extract capacities
        technology_capacities = {
            tech: design_vars.get(f"{tech}_capacity", 0.0)
            for tech in self.config.get_enabled_technologies()
        }
        total_capacity = sum(technology_capacities.values())

        # Calculate CapEx manually
        capex_per_mw = {
            tech: self.config.technologies[tech].cost_per_mw
            for tech in self.config.get_enabled_technologies()
        }
        total_capex = sum(
            technology_capacities[tech] * capex_per_mw[tech]
            for tech in technology_capacities
        )

        # Enforce hard limits
        if total_capacity > max_total_capacity:
            print(f"❌ Rejecting: total capacity {total_capacity:.2f} MW exceeds {max_total_capacity} MW")
            # Return penalty dictionary for expected keys
            return {
                'lcoe': 1e9,
                'npv': -1e9,
                'capex': 1e9,
                'capacity_factor': 0.0,
                'annual_energy': 0.0,
                'irr': 0.0,
                'opex': 1e9
            }

        if total_capex > max_investment:
            print(f"❌ Rejecting: total CapEx ${total_capex:,.0f} exceeds budget ${max_investment:,.0f}")
            return {
                'lcoe': 1e9,
                'npv': -1e9,
                'capex': 1e9,
                'capacity_factor': 0.0,
                'annual_energy': 0.0,
                'irr': 0.0,
                'opex': 1e9
            }


        
        # Calculate technical performance
        tech_performance = self.tech_model.calculate_performance(
            design_vars, self.resource_data
        )
        
        # Calculate economic performance
        economic_performance = self.economic_model.calculate_economics(
            design_vars, tech_performance
        )
        
        # Calculate financial metrics
        financial_metrics = self.financial_calc.calculate_metrics(
            capex=economic_performance['capex'],
            opex=economic_performance['opex'],
            revenue=economic_performance['revenue'],
            project_life=self.config.economic['project_lifetime']
        )
        
        # Combine all performance metrics
        performance = {
            **tech_performance,
            **economic_performance,
            **financial_metrics
        }
        
        # Apply constraints and penalties
        performance = self._apply_constraints(performance, design_vars, target)
        
        return performance
    
    def _apply_constraints(self, 
                          performance: Dict[str, float], 
                          design_vars: Dict[str, Any],
                          target: OptimizationTarget) -> Dict[str, float]:
        """Apply constraints and add penalties for violations."""
        
        penalty = 0.0
        constraints = self.config.optimization.get('constraints', {})
        
        # Investment constraint
        max_investment = constraints.get('max_investment', float('inf'))
        if performance['capex'] > max_investment:
            penalty += (performance['capex'] - max_investment) * 1e-6
        
        # Capacity factor constraint
        min_cf = constraints.get('min_capacity_factor', 0.0)
        if performance['capacity_factor'] < min_cf:
            penalty += (min_cf - performance['capacity_factor']) * 1e4
        
        # Production target constraint (if applicable)
        if target.target_type == 'production':
            target_production = target.target_value  # kWh
            actual_production = performance['annual_energy']  # kWh
            production_error = abs(actual_production - target_production) / target_production
            penalty += production_error * 1e3
        
        # Add penalty to objective values
        if 'lcoe' in performance:
            performance['lcoe'] += penalty
        if 'npv' in performance:
            performance['npv'] -= penalty * 1e6
        
        return performance
    
    def _get_optimized_technologies(self, target: OptimizationTarget) -> List[str]:
        """Return enabled technologies that should receive optimization variables."""
        enabled_techs = self.config.get_enabled_technologies()

        if (
            target.target_type == 'technologies'
            and hasattr(target.target_value, '__iter__')
            and not isinstance(target.target_value, str)
        ):
            return [tech for tech in enabled_techs if tech in target.target_value]

        return enabled_techs

    def _get_capacity_bounds(self, target: OptimizationTarget) -> List[Tuple[float, float]]:
        """Build capacity bounds for optimized technology variables."""
        constraints = self.config.optimization.get('constraints', {})
        max_total_capacity = constraints.get('max_total_capacity', 500)
        return [(0.0, max_total_capacity) for _ in self._get_optimized_technologies(target)]

    def _get_bounds_list(self, target: OptimizationTarget) -> List[Tuple[float, float]]:
        """Build bounds for the optimizer variable vector."""
        bounds_list = self._get_capacity_bounds(target)
        bounds_list.extend([
            self.bounds['platform_area'],
            self.bounds['water_depth'],
            self.bounds['distance_to_shore']
        ])
        return bounds_list

    def _get_capacity_variable_count(self, target: OptimizationTarget) -> int:
        """Return number of capacity variables in the optimization vector."""
        return len(self._get_optimized_technologies(target))

    def _estimate_capacity_capex(self, x: np.ndarray, target: OptimizationTarget) -> float:
        """Estimate technology CapEx from the optimizer vector."""
        total_capex = 0.0
        for i, tech_name in enumerate(self._get_optimized_technologies(target)):
            total_capex += x[i] * self.config.technologies[tech_name].cost_per_mw
        return total_capex

    def _get_linear_constraints(self, target: OptimizationTarget, variable_count: int) -> List[LinearConstraint]:
        """Build linear optimizer constraints for capacity and investment limits."""
        constraints_config = self.config.optimization.get('constraints', {})
        capacity_var_count = self._get_capacity_variable_count(target)
        linear_constraints = []

        max_total_capacity = constraints_config.get('max_total_capacity')
        if max_total_capacity is not None:
            coefficients = np.zeros(variable_count)
            coefficients[:capacity_var_count] = 1.0
            linear_constraints.append(LinearConstraint(coefficients, -np.inf, max_total_capacity))

        max_investment = constraints_config.get('max_investment')
        if max_investment is not None:
            coefficients = np.zeros(variable_count)
            for i, tech_name in enumerate(self._get_optimized_technologies(target)):
                coefficients[i] = self.config.technologies[tech_name].cost_per_mw
            linear_constraints.append(LinearConstraint(coefficients, -np.inf, max_investment))

        return linear_constraints

    def _optimize_differential_evolution(self, objective_func, target: OptimizationTarget, **kwargs) -> Any:
        """Run optimization using differential evolution."""
        bounds_list = self._get_bounds_list(target)
        
        # Prepare differential evolution parameters
        de_params = {
            'bounds': bounds_list,
            'maxiter': kwargs.get('maxiter', 1000),
            'popsize': kwargs.get('popsize', 15),
            'disp': True
        }

        linear_constraints = self._get_linear_constraints(target, len(bounds_list))
        if linear_constraints:
            de_params['constraints'] = tuple(linear_constraints)
        
        # Handle seed parameter - check if it's supported in current scipy version
        if 'random_state' in kwargs or 'seed' in kwargs:
            # Try random_state first (newer scipy versions), fallback to seed
            random_state = kwargs.get('random_state', kwargs.get('seed', 42))
            
            # Check scipy version compatibility
            try:
                import scipy
                scipy_version = tuple(map(int, scipy.__version__.split('.')[:2]))
                
                if scipy_version >= (1, 7):  # scipy >= 1.7 uses 'seed'
                    de_params['seed'] = random_state
                else:  # older scipy versions might use different parameter
                    # For older versions, try both and catch errors
                    de_params['seed'] = random_state
                    
            except (ImportError, AttributeError, ValueError):
                # If we can't determine version, try seed parameter
                de_params['seed'] = random_state
        
        # Run differential evolution with error handling
        try:
            result = differential_evolution(objective_func, **de_params)
        except TypeError as e:
            if 'seed' in str(e):
                # Remove seed parameter and try again
                print("Warning: 'seed' parameter not supported in this scipy version, running without seed")
                de_params.pop('seed', None)
                result = differential_evolution(objective_func, **de_params)
            else:
                raise e
        
        return result
    
    def _optimize_scipy(self, objective_func, target: OptimizationTarget, **kwargs) -> Any:
        """Run optimization using scipy minimize."""
        
        # Initial guess
        x0 = self._get_initial_guess(target)
        
        # Get bounds
        bounds_list = self._get_bounds_list(target)

        scipy_constraints = self._get_linear_constraints(target, len(bounds_list))

        method = kwargs.get('scipy_method', kwargs.get('optimizer_method', 'SLSQP'))
        
        # Run scipy optimization
        result = minimize(
            objective_func,
            x0=x0,
            bounds=bounds_list,
            constraints=scipy_constraints,
            method=method,
            options={'disp': True, 'maxiter': kwargs.get('maxiter', 1000)}
        )
        
        return result
    
    def _get_initial_guess(self, target: Optional[OptimizationTarget] = None) -> np.ndarray:
        """Generate initial guess for optimization variables."""
        x0 = []

        if target is None:
            target = OptimizationTarget('production', 0)

        optimized_techs = self._get_optimized_technologies(target)
        constraints = self.config.optimization.get('constraints', {})
        max_total_capacity = constraints.get('max_total_capacity')

        if optimized_techs:
            if max_total_capacity is None:
                starting_capacity = 50.0
            else:
                starting_capacity = max_total_capacity / len(optimized_techs)

            for _ in optimized_techs:
                x0.append(starting_capacity)
        
        # Platform design variables
        x0.extend([10000, 50, 20])  # platform_area, water_depth, distance_to_shore
        
        return np.array(x0)
    
    def _process_optimization_result(self, 
                                   result: Any, 
                                   target: OptimizationTarget) -> BaselineResults:
        """Process optimization result into BaselineResults object."""
        
        # Decode optimal variables
        optimal_vars = self._decode_variables(result.x, target)
        
        # Calculate final performance
        final_performance = self._evaluate_platform_performance(optimal_vars, target)
        
        # Extract technology capacities
        tech_capacities = {
            tech: optimal_vars.get(f'{tech}_capacity', 0.0)
            for tech in self.config.get_enabled_technologies()
        }
        
        # Create results object
        results = BaselineResults(
            optimal_design=optimal_vars,
            objective_value=result.fun,
            technology_capacities=tech_capacities,
            financial_metrics={
                'lcoe': final_performance.get('lcoe', 0.0),
                'npv': final_performance.get('npv', 0.0),
                'irr': final_performance.get('irr', 0.0),
                'capex': final_performance.get('capex', 0.0),
                'opex': final_performance.get('opex', 0.0)
            },
            technical_metrics={
                'capacity_factor': final_performance.get('capacity_factor', 0.0),
                'annual_energy': final_performance.get('annual_energy', 0.0),
                'total_capacity': sum(tech_capacities.values())
            },
            optimization_info={
                'success': result.success,
                'message': getattr(result, 'message', ''),
                'iterations': getattr(result, 'nit', 0),
                'function_evaluations': getattr(result, 'nfev', 0),
                'target_type': target.target_type,
                'target_value': target.target_value
            },
            timestamp=datetime.now().isoformat()
        )
        
        return results
    
    def save_results(self, output_dir: Optional[str] = None) -> str:
        """
        Save optimization results to file.
        
        Args:
            output_dir: Optional output directory. Defaults to data/{site}/results/baseline/
            
        Returns:
            Path to saved results file
            
        Raises:
            ValueError: If no results to save
        """
        if self.results is None:
            raise ValueError("No results to save. Run optimization first.")
        
        if output_dir is None:
            package_root = Path(__file__).parent.parent
            output_dir = str(package_root / "data" / self.config.name.lower() / "results" / "baseline")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"baseline_results_{timestamp}.json"
        filepath = output_path / filename
        
        # Save results
        with open(filepath, 'w') as f:
            json.dump(self.results.to_dict(), f, indent=2)
        
        print(f"Results saved to: {filepath}")
        return str(filepath)
    
    def load_results(self, filepath: str) -> BaselineResults:
        """
        Load optimization results from file.
        
        Args:
            filepath: Path to results file
            
        Returns:
            BaselineResults object
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.results = BaselineResults(**data)
        return self.results
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of optimization results.
        
        Returns:
            Dictionary with key results summary
            
        Raises:
            ValueError: If no results available
        """
        if self.results is None:
            raise ValueError("No results available. Run optimization first.")
        
        return {
            'objective_value': self.results.objective_value,
            'total_capacity_mw': self.results.technical_metrics['total_capacity'],
            'capacity_factor': self.results.technical_metrics['capacity_factor'],
            'lcoe_gbp_per_mwh': self.results.financial_metrics['lcoe'],
            'npv_gbp': self.results.financial_metrics['npv'],
            'capex_gbp': self.results.financial_metrics['capex'],
            'technology_mix': self.results.technology_capacities,
            'optimization_success': self.results.optimization_info['success']
        }
