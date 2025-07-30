"""
Optimization utilities for FlexiMORPv2.

Helper functions and classes for optimization algorithms, constraint handling,
and optimization result processing.
"""

import numpy as np
from scipy.optimize import minimize, differential_evolution, NonlinearConstraint
from typing import Dict, Any, List, Tuple, Optional, Callable
from dataclasses import dataclass
import warnings

from ..config import SiteConfig


@dataclass
class OptimizationBounds:
    """Container for optimization variable bounds."""
    lower: np.ndarray
    upper: np.ndarray
    names: List[str]


@dataclass
class OptimizationConstraints:
    """Container for optimization constraints."""
    equality: List[Callable]
    inequality: List[Callable]
    bounds: OptimizationBounds


@dataclass
class OptimizationResult:
    """Enhanced optimization result container."""
    success: bool
    x: np.ndarray
    fun: float
    nfev: int
    nit: int
    message: str
    method: str
    constraints_satisfied: bool
    variable_names: List[str]


class OptimizationUtils:
    """
    Utility class for optimization operations.
    
    Provides helper functions for setting up optimization problems,
    handling constraints, and processing results.
    """
    
    def __init__(self, config: SiteConfig):
        """
        Initialize optimization utilities.
        
        Args:
            config: Site configuration object
        """
        self.config = config
        
        # Optimization algorithm settings
        self.algorithm_settings = {
            'differential_evolution': {
                'popsize': 15,
                'maxiter': 1000,
                'atol': 1e-6,
                'seed': 42,
                'workers': 1
            },
            'scipy_minimize': {
                'method': 'L-BFGS-B',
                'options': {
                    'maxiter': 1000,
                    'ftol': 1e-9,
                    'gtol': 1e-6
                }
            },
            'genetic': {
                'population_size': 100,
                'generations': 500,
                'mutation_rate': 0.01,
                'crossover_rate': 0.8
            }
        }
    
    def setup_optimization_problem(self, 
                                  target_type: str,
                                  target_value: Any) -> Tuple[OptimizationBounds, OptimizationConstraints]:
        """
        Set up optimization bounds and constraints.
        
        Args:
            target_type: Type of optimization target
            target_value: Target specification
            
        Returns:
            Tuple of (bounds, constraints)
        """
        # Get enabled technologies
        enabled_techs = self.config.get_enabled_technologies()
        
        # Set up variable names and bounds
        variable_names = []
        lower_bounds = []
        upper_bounds = []
        
        # Technology capacity variables
        for tech_name in enabled_techs:
            if target_type == 'technologies' and tech_name not in target_value:
                # This technology is not in the target mix
                variable_names.append(f'{tech_name}_capacity')
                lower_bounds.append(0.0)
                upper_bounds.append(0.0)  # Force to zero
            else:
                variable_names.append(f'{tech_name}_capacity')
                lower_bounds.append(0.0)
                max_capacity = self.config.optimization.get('constraints', {}).get('max_total_capacity', 500)
                upper_bounds.append(max_capacity)
        
        # Platform design variables (if not fixed by target)
        if target_type != 'location':
            variable_names.extend(['platform_area', 'water_depth', 'distance_to_shore'])
            lower_bounds.extend([1000, 20, 5])    # Minimum values
            upper_bounds.extend([50000, 200, 100]) # Maximum values
        
        bounds = OptimizationBounds(
            lower=np.array(lower_bounds),
            upper=np.array(upper_bounds),
            names=variable_names
        )
        
        # Set up constraints
        constraints = self._setup_constraints(target_type, target_value, variable_names)
        
        return bounds, constraints
    
    def _setup_constraints(self, 
                          target_type: str, 
                          target_value: Any, 
                          variable_names: List[str]) -> OptimizationConstraints:
        """Set up optimization constraints."""
        
        equality_constraints = []
        inequality_constraints = []
        
        # Investment constraint
        max_investment = self.config.optimization.get('constraints', {}).get('max_investment')
        if max_investment:
            def investment_constraint(x):
                # Estimate total investment based on variables
                total_capex = self._estimate_total_capex(x, variable_names)
                return max_investment - total_capex  # Should be >= 0
            
            inequality_constraints.append(investment_constraint)
        
        # Minimum capacity factor constraint
        min_cf = self.config.optimization.get('constraints', {}).get('min_capacity_factor')
        if min_cf:
            def capacity_factor_constraint(x):
                # This would need access to the full model to calculate CF
                # For now, just a placeholder
                return 0.0  # Placeholder
            
            inequality_constraints.append(capacity_factor_constraint)
        
        # Production target constraint (for production optimization)
        if target_type == 'production':
            def production_constraint(x):
                # Calculate difference from target production
                # This would need full model evaluation
                return 0.0  # Placeholder
            
            equality_constraints.append(production_constraint)
        
        # Total capacity constraint
        max_total_capacity = self.config.optimization.get('constraints', {}).get('max_total_capacity')
        if max_total_capacity:
            def total_capacity_constraint(x):
                # Sum of technology capacities
                total_capacity = 0.0
                for i, name in enumerate(variable_names):
                    if '_capacity' in name:
                        total_capacity += x[i]
                return max_total_capacity - total_capacity  # Should be >= 0
            
            inequality_constraints.append(total_capacity_constraint)
        
        return OptimizationConstraints(
            equality=equality_constraints,
            inequality=inequality_constraints,
            bounds=None  # Will be handled separately
        )
    
    def _estimate_total_capex(self, x: np.ndarray, variable_names: List[str]) -> float:
        """Estimate total CAPEX from optimization variables."""
        
        total_capex = 0.0
        
        # Technology CAPEX
        for i, name in enumerate(variable_names):
            if '_capacity' in name:
                tech_name = name.replace('_capacity', '')
                if tech_name in self.config.technologies:
                    capacity = x[i]
                    cost_per_mw = self.config.technologies[tech_name].cost_per_mw
                    total_capex += capacity * cost_per_mw
        
        # Platform CAPEX (simplified estimation)
        platform_area_idx = None
        water_depth_idx = None
        distance_idx = None
        
        for i, name in enumerate(variable_names):
            if name == 'platform_area':
                platform_area_idx = i
            elif name == 'water_depth':
                water_depth_idx = i
            elif name == 'distance_to_shore':
                distance_idx = i
        
        if platform_area_idx is not None and water_depth_idx is not None:
            area = x[platform_area_idx]
            depth = x[water_depth_idx]
            
            # Simplified platform cost calculation
            if depth <= 50:
                cost_per_m2 = 15000
            elif depth <= 100:
                cost_per_m2 = 25000
            else:
                cost_per_m2 = 35000
            
            platform_capex = area * cost_per_m2
            total_capex += platform_capex
        
        # Grid connection costs
        if distance_idx is not None:
            distance = x[distance_idx]
            grid_cost = distance * 100000  # £100k per km
            total_capex += grid_cost
        
        # Add installation and development costs (estimated as % of equipment)
        total_capex *= 1.4  # 40% additional for installation and development
        
        return total_capex
    
    def run_optimization(self, 
                        objective_function: Callable,
                        bounds: OptimizationBounds,
                        constraints: OptimizationConstraints,
                        method: str = 'differential_evolution',
                        **kwargs) -> OptimizationResult:
        """
        Run optimization with specified method.
        
        Args:
            objective_function: Function to minimize
            bounds: Variable bounds
            constraints: Optimization constraints
            method: Optimization method
            **kwargs: Additional method-specific parameters
            
        Returns:
            OptimizationResult object
        """
        print(f"Running optimization with method: {method}")
        
        # Get method settings
        settings = self.algorithm_settings.get(method, {})
        settings.update(kwargs)
        
        # Set up bounds for scipy
        scipy_bounds = list(zip(bounds.lower, bounds.upper))
        
        try:
            if method == 'differential_evolution':
                result = self._run_differential_evolution(
                    objective_function, scipy_bounds, constraints, settings
                )
            elif method == 'scipy_minimize':
                result = self._run_scipy_minimize(
                    objective_function, scipy_bounds, constraints, settings
                )
            elif method == 'genetic':
                result = self._run_genetic_algorithm(
                    objective_function, bounds, constraints, settings
                )
            else:
                raise ValueError(f"Unknown optimization method: {method}")
            
            # Check constraint satisfaction
            constraints_satisfied = self._check_constraints(result.x, constraints)
            
            return OptimizationResult(
                success=result.success,
                x=result.x,
                fun=result.fun,
                nfev=getattr(result, 'nfev', 0),
                nit=getattr(result, 'nit', 0),
                message=getattr(result, 'message', ''),
                method=method,
                constraints_satisfied=constraints_satisfied,
                variable_names=bounds.names
            )
            
        except Exception as e:
            print(f"Optimization failed: {e}")
            return OptimizationResult(
                success=False,
                x=np.zeros(len(bounds.names)),
                fun=float('inf'),
                nfev=0,
                nit=0,
                message=str(e),
                method=method,
                constraints_satisfied=False,
                variable_names=bounds.names
            )
    
    def _run_differential_evolution(self, 
                                   objective_function: Callable,
                                   bounds: List[Tuple],
                                   constraints: OptimizationConstraints,
                                   settings: Dict) -> Any:
        """Run differential evolution optimization."""
        
        # Convert constraints to scipy format
        scipy_constraints = []
        
        for constraint in constraints.inequality:
            scipy_constraints.append(NonlinearConstraint(constraint, 0, np.inf))
        
        for constraint in constraints.equality:
            scipy_constraints.append(NonlinearConstraint(constraint, 0, 0))
        
        return differential_evolution(
            objective_function,
            bounds=bounds,
            constraints=scipy_constraints if scipy_constraints else (),
            popsize=settings.get('popsize', 15),
            maxiter=settings.get('maxiter', 1000),
            atol=settings.get('atol', 1e-6),
            seed=settings.get('seed', 42),
            workers=settings.get('workers', 1),
            disp=True
        )
    
    def _run_scipy_minimize(self, 
                           objective_function: Callable,
                           bounds: List[Tuple],
                           constraints: OptimizationConstraints,
                           settings: Dict) -> Any:
        """Run scipy minimize optimization."""
        
        # Initial guess (midpoint of bounds)
        x0 = np.array([(b[0] + b[1]) / 2 for b in bounds])
        
        # Convert constraints to scipy format
        scipy_constraints = []
        
        for constraint in constraints.inequality:
            scipy_constraints.append({'type': 'ineq', 'fun': constraint})
        
        for constraint in constraints.equality:
            scipy_constraints.append({'type': 'eq', 'fun': constraint})
        
        return minimize(
            objective_function,
            x0=x0,
            bounds=bounds,
            constraints=scipy_constraints,
            method=settings.get('method', 'L-BFGS-B'),
            options=settings.get('options', {})
        )
    
    def _run_genetic_algorithm(self, 
                              objective_function: Callable,
                              bounds: OptimizationBounds,
                              constraints: OptimizationConstraints,
                              settings: Dict) -> Any:
        """Run simple genetic algorithm (custom implementation)."""
        
        # This is a simplified genetic algorithm implementation
        # In practice, you might want to use a more sophisticated library
        
        population_size = settings.get('population_size', 100)
        generations = settings.get('generations', 500)
        mutation_rate = settings.get('mutation_rate', 0.01)
        crossover_rate = settings.get('crossover_rate', 0.8)
        
        # Initialize population
        population = self._initialize_population(bounds, population_size)
        
        best_individual = None
        best_fitness = float('inf')
        
        for generation in range(generations):
            # Evaluate fitness
            fitness_scores = []
            for individual in population:
                try:
                    fitness = objective_function(individual)
                    # Add penalty for constraint violations
                    penalty = self._calculate_constraint_penalty(individual, constraints)
                    fitness += penalty
                    fitness_scores.append(fitness)
                    
                    # Track best
                    if fitness < best_fitness:
                        best_fitness = fitness
                        best_individual = individual.copy()
                        
                except:
                    fitness_scores.append(float('inf'))
            
            # Selection, crossover, mutation
            population = self._evolve_population(
                population, fitness_scores, crossover_rate, mutation_rate, bounds
            )
            
            if generation % 50 == 0:
                print(f"Generation {generation}: Best fitness = {best_fitness:.6f}")
        
        # Create result object
        class GAResult:
            def __init__(self):
                self.success = best_individual is not None
                self.x = best_individual if best_individual is not None else np.zeros(len(bounds.names))
                self.fun = best_fitness
                self.nfev = population_size * generations
                self.nit = generations
                self.message = "Genetic algorithm completed"
        
        return GAResult()
    
    def _initialize_population(self, bounds: OptimizationBounds, size: int) -> np.ndarray:
        """Initialize random population within bounds."""
        
        population = np.zeros((size, len(bounds.names)))
        
        for i in range(len(bounds.names)):
            population[:, i] = np.random.uniform(
                bounds.lower[i], bounds.upper[i], size
            )
        
        return population
    
    def _calculate_constraint_penalty(self, 
                                    individual: np.ndarray, 
                                    constraints: OptimizationConstraints) -> float:
        """Calculate penalty for constraint violations."""
        
        penalty = 0.0
        
        # Inequality constraints (should be >= 0)
        for constraint in constraints.inequality:
            try:
                value = constraint(individual)
                if value < 0:
                    penalty += abs(value) * 1e6  # Large penalty
            except:
                penalty += 1e10  # Very large penalty for evaluation errors
        
        # Equality constraints (should be = 0)
        for constraint in constraints.equality:
            try:
                value = constraint(individual)
                penalty += abs(value) * 1e6
            except:
                penalty += 1e10
        
        return penalty
    
    def _evolve_population(self, 
                          population: np.ndarray,
                          fitness_scores: List[float],
                          crossover_rate: float,
                          mutation_rate: float,
                          bounds: OptimizationBounds) -> np.ndarray:
        """Evolve population through selection, crossover, and mutation."""
        
        size, nvars = population.shape
        new_population = np.zeros_like(population)
        
        # Convert fitness to selection probabilities (lower is better)
        fitness_array = np.array(fitness_scores)
        if np.all(np.isfinite(fitness_array)):
            # Rank-based selection
            ranks = np.argsort(np.argsort(fitness_array))
            probabilities = 1.0 / (ranks + 1)
            probabilities /= probabilities.sum()
        else:
            # Uniform selection if fitness values are problematic
            probabilities = np.ones(size) / size
        
        for i in range(size):
            # Selection
            parent1_idx = np.random.choice(size, p=probabilities)
            parent2_idx = np.random.choice(size, p=probabilities)
            
            parent1 = population[parent1_idx]
            parent2 = population[parent2_idx]
            
            # Crossover
            if np.random.random() < crossover_rate:
                # Uniform crossover
                mask = np.random.random(nvars) < 0.5
                child = parent1.copy()
                child[mask] = parent2[mask]
            else:
                child = parent1.copy()
            
            # Mutation
            for j in range(nvars):
                if np.random.random() < mutation_rate:
                    # Gaussian mutation
                    std = (bounds.upper[j] - bounds.lower[j]) * 0.1
                    child[j] += np.random.normal(0, std)
                    child[j] = np.clip(child[j], bounds.lower[j], bounds.upper[j])
            
            new_population[i] = child
        
        return new_population
    
    def _check_constraints(self, 
                          x: np.ndarray, 
                          constraints: OptimizationConstraints) -> bool:
        """Check if solution satisfies all constraints."""
        
        tolerance = 1e-6
        
        # Check inequality constraints
        for constraint in constraints.inequality:
            try:
                value = constraint(x)
                if value < -tolerance:
                    return False
            except:
                return False
        
        # Check equality constraints
        for constraint in constraints.equality:
            try:
                value = constraint(x)
                if abs(value) > tolerance:
                    return False
            except:
                return False
        
        return True
    
    def analyze_sensitivity(self, 
                           objective_function: Callable,
                           optimal_x: np.ndarray,
                           bounds: OptimizationBounds,
                           perturbation: float = 0.01) -> Dict[str, float]:
        """
        Analyze sensitivity of objective function to variable changes.
        
        Args:
            objective_function: Objective function
            optimal_x: Optimal solution
            bounds: Variable bounds
            perturbation: Relative perturbation for sensitivity analysis
            
        Returns:
            Dictionary with sensitivity values for each variable
        """
        
        base_value = objective_function(optimal_x)
        sensitivities = {}
        
        for i, var_name in enumerate(bounds.names):
            # Calculate perturbation size
            var_range = bounds.upper[i] - bounds.lower[i]
            delta = var_range * perturbation
            
            # Positive perturbation
            x_plus = optimal_x.copy()
            x_plus[i] = min(x_plus[i] + delta, bounds.upper[i])
            
            # Negative perturbation
            x_minus = optimal_x.copy()
            x_minus[i] = max(x_minus[i] - delta, bounds.lower[i])
            
            try:
                value_plus = objective_function(x_plus)
                value_minus = objective_function(x_minus)
                
                # Calculate sensitivity (derivative approximation)
                sensitivity = (value_plus - value_minus) / (2 * delta)
                sensitivities[var_name] = sensitivity
                
            except:
                sensitivities[var_name] = 0.0
        
        return sensitivities
    
    def get_optimization_summary(self, result: OptimizationResult) -> Dict[str, Any]:
        """Get summary of optimization results."""
        
        return {
            'success': result.success,
            'method': result.method,
            'objective_value': result.fun,
            'iterations': result.nit,
            'function_evaluations': result.nfev,
            'constraints_satisfied': result.constraints_satisfied,
            'message': result.message,
            'optimal_variables': {
                name: value for name, value in zip(result.variable_names, result.x)
            }
        }
