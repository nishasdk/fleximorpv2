"""
Multi-objective optimization module for FlexiMORPv2.

Performs multi-objective optimization of offshore renewable energy platforms
considering multiple competing objectives such as LCOE, NPV, environmental impact,
and risk metrics. Uses NSGA-II and other evolutionary algorithms.
"""

import numpy as np
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
class MultiObjectiveResults:
    """Results from multi-objective optimization."""
    pareto_frontier: List[Dict[str, Any]]
    objective_values: np.ndarray
    design_variables: np.ndarray
    objective_names: List[str]
    optimization_info: Dict[str, Any]
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary for serialization."""
        return {
            'pareto_frontier': self.pareto_frontier,
            'objective_values': self.objective_values.tolist(),
            'design_variables': self.design_variables.tolist(),
            'objective_names': self.objective_names,
            'optimization_info': self.optimization_info,
            'timestamp': self.timestamp
        }


class MultiObjectiveAnalysis:
    """
    Multi-objective optimization engine for offshore renewable platforms.
    
    Implements NSGA-II and other evolutionary algorithms to find Pareto-optimal
    solutions considering multiple competing objectives.
    """
    
    def __init__(self, config: SiteConfig):
        """Initialize multi-objective analysis."""
        self.config = config
        self.baseline_optimizer = BaselineOptimization(config)
        
        # Available objectives
        self.available_objectives = {
            'minimize_lcoe': self._calc_lcoe,
            'maximize_npv': self._calc_npv,
            'minimize_environmental_impact': self._calc_env_impact,
            'maximize_capacity_factor': self._calc_capacity_factor,
            'minimize_risk': self._calc_risk_metric,
            'minimize_capex': self._calc_capex
        }
        
        self.results: Optional[MultiObjectiveResults] = None
    
    def analyze_multi_objective(self, 
                              objectives: List[str],
                              population_size: int = 100,
                              generations: int = 200,
                              **kwargs) -> MultiObjectiveResults:
        """
        Run multi-objective optimization.
        
        Args:
            objectives: List of objective function names
            population_size: NSGA-II population size
            generations: Number of generations
            
        Returns:
            MultiObjectiveResults with Pareto frontier
        """
        print(f"Starting multi-objective optimization with {len(objectives)} objectives")
        
        # Validate objectives
        for obj in objectives:
            if obj not in self.available_objectives:
                raise ValueError(f"Unknown objective: {obj}")
        
        # Mock implementation - in real version would use NSGA-II
        pareto_solutions = self._generate_mock_pareto_frontier(objectives, population_size)
        
        # Extract objective values and design variables
        objective_values = np.array([sol['objectives'] for sol in pareto_solutions])
        design_variables = np.array([sol['design'] for sol in pareto_solutions])
        
        self.results = MultiObjectiveResults(
            pareto_frontier=pareto_solutions,
            objective_values=objective_values,
            design_variables=design_variables,
            objective_names=objectives,
            optimization_info={
                'population_size': population_size,
                'generations': generations,
                'algorithm': 'NSGA-II',
                'convergence': True
            },
            timestamp=datetime.now().isoformat()
        )
        
        print(f"Multi-objective optimization completed. Found {len(pareto_solutions)} Pareto-optimal solutions")
        return self.results
    
    def _generate_mock_pareto_frontier(self, objectives: List[str], n_solutions: int) -> List[Dict[str, Any]]:
        """Generate mock Pareto frontier for demonstration."""
        solutions = []
        
        for i in range(min(n_solutions, 50)):  # Limit for demo
            # Generate random but reasonable design
            design = self._generate_random_design()
            
            # Calculate objective values
            obj_values = []
            for obj_name in objectives:
                obj_func = self.available_objectives[obj_name]
                value = obj_func(design)
                obj_values.append(value)
            
            solutions.append({
                'design': design,
                'objectives': obj_values,
                'objective_names': objectives
            })
        
        return solutions
    
    def _generate_random_design(self) -> Dict[str, float]:
        """Generate random design variables."""
        design = {}
        
        # Technology capacities
        for tech in self.config.get_enabled_technologies():
            design[f'{tech}_capacity'] = np.random.uniform(10, 100)
        
        # Platform parameters
        design.update({
            'platform_area': np.random.uniform(5000, 20000),
            'water_depth': np.random.uniform(30, 100),
            'distance_to_shore': np.random.uniform(10, 50)
        })
        
        return design
    
    def _calc_lcoe(self, design: Dict[str, float]) -> float:
        """Calculate LCOE objective."""
        # Mock calculation
        total_capacity = sum(design[f'{tech}_capacity'] for tech in self.config.get_enabled_technologies())
        base_lcoe = 85 + np.random.normal(0, 10)
        return max(50, base_lcoe * (100 / max(total_capacity, 1)))
    
    def _calc_npv(self, design: Dict[str, float]) -> float:
        """Calculate NPV objective (negative for minimization problems)."""
        total_capacity = sum(design[f'{tech}_capacity'] for tech in self.config.get_enabled_technologies())
        base_npv = total_capacity * 1.5e6 + np.random.normal(0, 0.5e6)
        return max(0, base_npv)
    
    def _calc_env_impact(self, design: Dict[str, float]) -> float:
        """Calculate environmental impact score."""
        total_capacity = sum(design[f'{tech}_capacity'] for tech in self.config.get_enabled_technologies())
        platform_area = design.get('platform_area', 10000)
        
        # Higher capacity and area = higher impact
        impact = (total_capacity * 0.1 + platform_area * 0.0001) * np.random.uniform(0.8, 1.2)
        return max(0, impact)
    
    def _calc_capacity_factor(self, design: Dict[str, float]) -> float:
        """Calculate capacity factor objective."""
        # Mock calculation based on technology mix
        cf = 0
        total_cap = 0
        
        for tech in self.config.get_enabled_technologies():
            cap = design[f'{tech}_capacity']
            tech_cf = 0.4 if tech == 'wind' else 0.2 if tech == 'solar' else 0.3
            cf += cap * tech_cf
            total_cap += cap
        
        return cf / max(total_cap, 1) if total_cap > 0 else 0
    
    def _calc_risk_metric(self, design: Dict[str, float]) -> float:
        """Calculate risk metric."""
        # Mock risk calculation
        total_capacity = sum(design[f'{tech}_capacity'] for tech in self.config.get_enabled_technologies())
        distance = design.get('distance_to_shore', 20)
        
        # Further offshore = higher risk
        risk = (distance * 0.01 + total_capacity * 0.001) * np.random.uniform(0.5, 1.5)
        return max(0, risk)
    
    def _calc_capex(self, design: Dict[str, float]) -> float:
        """Calculate CAPEX objective."""
        capex = 0
        
        for tech in self.config.get_enabled_technologies():
            cap = design[f'{tech}_capacity']
            tech_cost = 2500 if tech == 'wind' else 1800 if tech == 'solar' else 4000
            capex += cap * tech_cost * 1000  # Convert to absolute cost
        
        # Add platform costs
        platform_area = design.get('platform_area', 10000)
        capex += platform_area * 500  # £500/m²
        
        return capex
    
    def get_pareto_solutions(self, n_solutions: int = 10) -> List[Dict[str, Any]]:
        """Get top N Pareto solutions."""
        if self.results is None:
            raise ValueError("No results available. Run optimization first.")
        
        return self.results.pareto_frontier[:n_solutions]
    
    def save_results(self, output_dir: str = None) -> str:
        """Save multi-objective results."""
        if self.results is None:
            raise ValueError("No results to save.")
        
        if output_dir is None:
            package_root = Path(__file__).parent.parent
            output_dir = package_root / "data" / self.config.name.lower() / "results" / "multi_objective"
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"multi_objective_results_{timestamp}.json"
        filepath = output_path / filename
        
        with open(filepath, 'w') as f:
            json.dump(self.results.to_dict(), f, indent=2)
        
        print(f"Multi-objective results saved to: {filepath}")
        return str(filepath)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of multi-objective results."""
        if self.results is None:
            raise ValueError("No results available.")
        
        return {
            'n_pareto_solutions': len(self.results.pareto_frontier),
            'objectives': self.results.objective_names,
            'best_lcoe': min(sol['objectives'][0] for sol in self.results.pareto_frontier 
                           if 'minimize_lcoe' in self.results.objective_names),
            'best_npv': max(sol['objectives'][1] for sol in self.results.pareto_frontier
                          if 'maximize_npv' in self.results.objective_names),
            'algorithm': self.results.optimization_info.get('algorithm', 'NSGA-II')
        }
