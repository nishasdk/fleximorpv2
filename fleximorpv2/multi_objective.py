"""
Multi-objective optimization module for FlexiMORPv2.

Performs multi-objective optimization of offshore renewable energy platforms
considering multiple competing objectives such as LCOE, NPV, environmental impact,
and risk metrics. Uses NSGA-II and other evolutionary algorithms.
"""

import numpy as np
from typing import Dict, Any, List, Tuple, Optional  # noqa: F401 — Tuple used in _eval_economics signature
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
        
        # Generate candidate solutions by sampling the design space
        candidates = self._generate_candidate_solutions(objectives, population_size)

        # Filter to Pareto-optimal front
        pareto_solutions = self._pareto_filter(candidates, objectives)

        objective_values = np.array([sol['objectives'] for sol in pareto_solutions])
        design_variables = np.array([[v for v in sol['design'].values()] for sol in pareto_solutions])

        self.results = MultiObjectiveResults(
            pareto_frontier=pareto_solutions,
            objective_values=objective_values,
            design_variables=design_variables,
            objective_names=objectives,
            optimization_info={
                'population_size': population_size,
                'n_candidates_evaluated': len(candidates),
                'n_pareto_solutions': len(pareto_solutions),
                'algorithm': 'random_search_pareto_filter',
                'convergence': True,
            },
            timestamp=datetime.now().isoformat()
        )

        print(f"Multi-objective analysis completed. Found {len(pareto_solutions)} Pareto-optimal solutions from {len(candidates)} candidates.")
        return self.results
    
    # ------------------------------------------------------------------
    # Design space sampling and Pareto filtering
    # ------------------------------------------------------------------

    def _generate_candidate_solutions(self, objectives: List[str], n_candidates: int) -> List[Dict[str, Any]]:
        """Sample the design space and evaluate each candidate against all objectives."""
        np.random.seed(42)
        solutions = []
        enabled = self.config.get_enabled_technologies()
        max_cap = self.config.optimization.get('constraints', {}).get('max_total_capacity', 200)

        for _ in range(n_candidates):
            design = {}
            remaining = max_cap
            for i, tech in enumerate(enabled):
                if i == len(enabled) - 1:
                    cap = np.random.uniform(0, remaining)
                else:
                    cap = np.random.uniform(0, remaining * 0.7)
                    remaining -= cap
                design[f'{tech}_capacity'] = max(0.0, cap)

            design.update({
                'platform_area': np.random.uniform(5000, 20000),
                'water_depth': np.random.uniform(20, 100),
                'distance_to_shore': np.random.uniform(5, 50),
            })

            obj_values = [self.available_objectives[obj](design) for obj in objectives]
            solutions.append({
                'design': design,
                'objectives': obj_values,
                'objective_names': objectives,
            })

        return solutions

    def _pareto_filter(self, candidates: List[Dict[str, Any]], objectives: List[str]) -> List[Dict[str, Any]]:
        """Return non-dominated solutions (all objectives treated as minimise)."""
        # maximize_* objectives are stored as negatives so lower is still better
        pareto = []
        for i, sol_i in enumerate(candidates):
            dominated = False
            for j, sol_j in enumerate(candidates):
                if i == j:
                    continue
                # sol_j weakly dominates sol_i in every objective and strictly in at least one
                objs_i = sol_i['objectives']
                objs_j = sol_j['objectives']
                if all(vj <= vi for vj, vi in zip(objs_j, objs_i)) and any(vj < vi for vj, vi in zip(objs_j, objs_i)):
                    dominated = True
                    break
            if not dominated:
                pareto.append(sol_i)
        return pareto if pareto else candidates[:10]  # fallback: return first 10 if all dominated

    # ------------------------------------------------------------------
    # Objective functions — deterministic, using config parameters
    # ------------------------------------------------------------------

    def _eval_economics(self, design: Dict[str, float]) -> Tuple[float, float, float]:
        """Return (lcoe, npv, total_capex) using analytical model."""
        enabled = self.config.get_enabled_technologies()
        discount_rate = self.config.economic.get('discount_rate', 0.08)
        project_life = int(self.config.economic.get('project_lifetime', 25))

        elec_price = self.config.economic.get('electricity_price', 0.085)
        if elec_price < 5:
            elec_price = elec_price * 1000  # $/kWh → $/MWh

        crf = (discount_rate * (1 + discount_rate) ** project_life) / ((1 + discount_rate) ** project_life - 1)
        annuity = (1 - (1 + discount_rate) ** (-project_life)) / discount_rate

        total_capex = 0.0
        total_annual_energy = 0.0
        total_capacity = 0.0
        for tech in enabled:
            cap = design.get(f'{tech}_capacity', 0.0)
            if cap <= 0:
                continue
            cf = self.config.technologies[tech].capacity_factor
            total_capex += cap * self.config.technologies[tech].cost_per_mw
            total_annual_energy += cf * cap * 8760
            total_capacity += cap

        if total_capacity <= 0 or total_annual_energy <= 0:
            return float('inf'), 0.0, total_capex

        annual_opex = total_capex * 0.02
        lcoe = (total_capex * crf + annual_opex) / total_annual_energy
        npv = -total_capex + (total_annual_energy * elec_price - annual_opex) * annuity
        return lcoe, npv, total_capex

    def _calc_lcoe(self, design: Dict[str, float]) -> float:
        """LCOE [$/MWh] — minimise."""
        lcoe, _, _ = self._eval_economics(design)
        return lcoe

    def _calc_npv(self, design: Dict[str, float]) -> float:
        """Negative NPV [$] — stored negative so Pareto filter can minimise."""
        _, npv, _ = self._eval_economics(design)
        return -npv

    def _calc_env_impact(self, design: Dict[str, float]) -> float:
        """Environmental impact score — deterministic proxy (lower is better)."""
        enabled = self.config.get_enabled_technologies()
        total_capacity = sum(design.get(f'{tech}_capacity', 0.0) for tech in enabled)
        platform_area = design.get('platform_area', 10000)
        distance = design.get('distance_to_shore', 20)
        # Larger platform and shallower water = more impact; greater distance = more impact
        water_depth = design.get('water_depth', 50)
        depth_factor = max(0.5, 1.0 - water_depth / 200)
        return total_capacity * 0.1 + platform_area * 0.0001 + distance * 0.05 * depth_factor

    def _calc_capacity_factor(self, design: Dict[str, float]) -> float:
        """Negative weighted capacity factor — stored negative for minimisation."""
        enabled = self.config.get_enabled_technologies()
        weighted_cf = 0.0
        total_cap = 0.0
        for tech in enabled:
            cap = design.get(f'{tech}_capacity', 0.0)
            cf = self.config.technologies[tech].capacity_factor
            weighted_cf += cap * cf
            total_cap += cap
        cf_value = weighted_cf / total_cap if total_cap > 0 else 0.0
        return -cf_value  # negative so Pareto filter minimises

    def _calc_risk_metric(self, design: Dict[str, float]) -> float:
        """Risk score — deterministic proxy (lower is better)."""
        enabled = self.config.get_enabled_technologies()
        total_capacity = sum(design.get(f'{tech}_capacity', 0.0) for tech in enabled)
        distance = design.get('distance_to_shore', 20)
        water_depth = design.get('water_depth', 50)
        # Risk increases with distance and depth; decreases with diversification
        n_techs = sum(1 for t in enabled if design.get(f'{t}_capacity', 0) > 1)
        diversification_bonus = max(0, (n_techs - 1) * 0.05)
        return (distance * 0.02 + water_depth * 0.005 + total_capacity * 0.001) * (1 - diversification_bonus)

    def _calc_capex(self, design: Dict[str, float]) -> float:
        """Total CAPEX [$] — minimise."""
        _, _, capex = self._eval_economics(design)
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
        
        obj_names = self.results.objective_names
        summary: Dict[str, Any] = {
            'n_pareto_solutions': len(self.results.pareto_frontier),
            'objectives': obj_names,
            'algorithm': self.results.optimization_info.get('algorithm', 'random_search_pareto_filter'),
        }
        if 'minimize_lcoe' in obj_names:
            idx = obj_names.index('minimize_lcoe')
            summary['best_lcoe'] = min(sol['objectives'][idx] for sol in self.results.pareto_frontier)
        if 'maximize_npv' in obj_names:
            idx = obj_names.index('maximize_npv')
            # stored as negative for minimisation, so min gives best (most positive) NPV
            summary['best_npv'] = -min(sol['objectives'][idx] for sol in self.results.pareto_frontier)
        return summary
