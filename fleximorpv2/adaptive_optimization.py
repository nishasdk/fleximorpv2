"""
Adaptive Optimization Engine for FlexiMORP v2

This module implements adaptive optimization strategies that adjust based on 
what design variables are known vs unknown by the user. The optimization
approach dynamically changes based on the configuration.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging
from scipy.optimize import minimize, differential_evolution
from sklearn.preprocessing import MinMaxScaler

from .utils.optimization import OptimizationResult
from .models.platform import Platform
from .models.technologies import TechnologyMix
from .models.economics import EconomicModel

logger = logging.getLogger(__name__)


class VariableStatus(Enum):
    """Status of design variables"""
    KNOWN = "known"
    UNKNOWN = "unknown"
    CONSTRAINED = "constrained"


class OptimizationStrategy(Enum):
    """Optimization strategies for different variable combinations"""
    TECHNOLOGY_SCREENING = "multi_objective_screening"
    SPATIAL_OPTIMIZATION = "spatial_optimization"
    CAPACITY_SIZING = "economic_sizing"
    ENVIRONMENTAL_WEIGHTING = "environmental_weighting"
    EXCLUSION_FILTERING = "exclusion_filtering"
    COMMUNITY_SIZING = "community_sizing"
    FISHING_COMPATIBLE = "fishing_compatible_screening"


@dataclass
class DesignVariable:
    """Design variable with status and constraints"""
    name: str
    status: VariableStatus
    value: Optional[Any] = None
    constraints: Optional[Dict] = None
    environmental_restrictions: Optional[List[str]] = None


@dataclass
class OptimizationConfig:
    """Configuration for adaptive optimization"""
    objective: str
    secondary_objectives: List[str]
    constraints: Dict[str, Any]
    environmental_thresholds: Dict[str, Any]
    adaptation_strategy: Dict[str, str]


class AdaptiveOptimization:
    """
    Adaptive optimization engine that adjusts strategy based on 
    known vs unknown design variables
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize adaptive optimization engine
        
        Args:
            config: Site configuration dictionary
        """
        self.config = config
        self.site_name = config['site']['name']
        self.design_variables = self._parse_design_variables(config)
        self.optimization_config = self._parse_optimization_config(config)
        self.environmental_constraints = config.get('environmental_thresholds', {})
        
        # Initialize models
        self.platform = Platform(config)
        self.economics = EconomicModel(config['economic'])
        
        logger.info(f"Initialized adaptive optimization for {self.site_name}")
        
    def _parse_design_variables(self, config: Dict) -> Dict[str, DesignVariable]:
        """Parse design variables from configuration"""
        variables = {}
        
        for var_name, var_config in config['design_variables'].items():
            variables[var_name] = DesignVariable(
                name=var_name,
                status=VariableStatus(var_config['status']),
                value=var_config.get('value'),
                constraints=var_config.get('constraints'),
                environmental_restrictions=var_config.get('environmental_restrictions')
            )
            
        return variables
        
    def _parse_optimization_config(self, config: Dict) -> OptimizationConfig:
        """Parse optimization configuration"""
        opt_config = config['optimization']
        
        return OptimizationConfig(
            objective=opt_config['objective'],
            secondary_objectives=opt_config.get('secondary_objectives', []),
            constraints=opt_config.get('constraints', {}),
            environmental_thresholds=opt_config.get('environmental_thresholds', {}),
            adaptation_strategy=opt_config.get('adaptation_strategy', {})
        )
    
    def determine_optimization_strategy(self) -> Dict[str, str]:
        """
        Determine optimization approach based on known/unknown variables
        
        Returns:
            Dictionary mapping variable types to optimization strategies
        """
        unknown_vars = self.identify_unknown_variables()
        strategy = {}
        
        # Technology mix strategy
        if 'technology_mix' in unknown_vars:
            if 'fishing_industry_weight' in self.config.get('stakeholders', {}).get('decision_criteria', {}):
                strategy['technology'] = OptimizationStrategy.FISHING_COMPATIBLE.value
            elif self._has_environmental_priority():
                strategy['technology'] = OptimizationStrategy.ENVIRONMENTAL_WEIGHTING.value
            else:
                strategy['technology'] = OptimizationStrategy.TECHNOLOGY_SCREENING.value
        
        # Location strategy
        if 'location' in unknown_vars:
            if self._has_exclusion_zones():
                strategy['location'] = OptimizationStrategy.EXCLUSION_FILTERING.value
            else:
                strategy['location'] = OptimizationStrategy.SPATIAL_OPTIMIZATION.value
        
        # Capacity strategy
        if 'capacity' in unknown_vars:
            if 'community' in self.site_name.lower():
                strategy['capacity'] = OptimizationStrategy.COMMUNITY_SIZING.value
            else:
                strategy['capacity'] = OptimizationStrategy.CAPACITY_SIZING.value
        
        logger.info(f"Selected optimization strategies: {strategy}")
        return strategy
    
    def identify_unknown_variables(self) -> List[str]:
        """Identify which design variables are unknown"""
        unknown = []
        for name, variable in self.design_variables.items():
            if variable.status == VariableStatus.UNKNOWN:
                unknown.append(name)
        return unknown
    
    def _has_environmental_priority(self) -> bool:
        """Check if environmental considerations have high priority"""
        stakeholders = self.config.get('stakeholders', {})
        criteria = stakeholders.get('decision_criteria', {})
        env_weight = criteria.get('environmental_weight', 0)
        return env_weight > 0.3
    
    def _has_exclusion_zones(self) -> bool:
        """Check if location has exclusion zones defined"""
        location_var = self.design_variables.get('location')
        if location_var and location_var.constraints:
            return 'exclusion_zones' in location_var.constraints
        return False
    
    def optimize_unknown_technology(self) -> Dict[str, Any]:
        """
        Multi-objective screening of technology options
        
        Returns:
            Optimal technology mix and performance metrics
        """
        logger.info("Running technology mix optimization...")
        
        tech_var = self.design_variables['technology_mix']
        allowed_techs = tech_var.constraints.get('allowed_technologies', ['wind', 'solar', 'wave'])
        
        # Generate technology combinations
        tech_combinations = self._generate_tech_combinations(allowed_techs)
        
        results = []
        for tech_combo in tech_combinations:
            # Evaluate each combination
            tech_mix = TechnologyMix(tech_combo, self.config['technologies'])
            
            # Calculate performance metrics
            performance = self._evaluate_technology_performance(tech_mix)
            
            # Apply environmental weighting if applicable
            if self._has_environmental_priority():
                performance = self._apply_environmental_weighting(performance, tech_mix)
            
            results.append({
                'technologies': tech_combo,
                'performance': performance,
                'tech_mix': tech_mix
            })
        
        # Select optimal combination based on primary objective
        optimal = self._select_optimal_technology(results)
        
        logger.info(f"Selected optimal technology mix: {optimal['technologies']}")
        return optimal
    
    def optimize_unknown_location(self) -> Dict[str, Any]:
        """
        Spatial optimization with exclusion zones
        
        Returns:
            Optimal location coordinates and site characteristics
        """
        logger.info("Running location optimization...")
        
        location_var = self.design_variables['location']
        constraints = location_var.constraints
        
        # Define search space
        search_bounds = constraints['search_area']['bounds']
        depth_range = constraints.get('depth_range', [10, 100])
        distance_range = constraints.get('shore_distance_range', [1, 20])
        
        # Handle exclusion zones
        exclusion_zones = constraints.get('exclusion_zones', [])
        
        # Set up optimization bounds
        bounds = [
            (search_bounds[0][0], search_bounds[1][0]),  # latitude
            (search_bounds[0][1], search_bounds[1][1]),  # longitude
            (depth_range[0], depth_range[1]),            # depth
            (distance_range[0], distance_range[1])       # distance to shore
        ]
        
        # Objective function for location optimization
        def location_objective(x):
            lat, lon, depth, shore_distance = x
            
            # Check exclusion zones
            if self._point_in_exclusion_zones(lat, lon, exclusion_zones):
                return 1e6  # Large penalty for excluded areas
            
            # Calculate location performance
            location_score = self._evaluate_location_performance(lat, lon, depth, shore_distance)
            
            return -location_score  # Minimize negative score (maximize score)
        
        # Run optimization
        result = differential_evolution(
            location_objective,
            bounds,
            maxiter=100,
            popsize=15,
            seed=42
        )
        
        optimal_location = {
            'coordinates': [result.x[0], result.x[1]],
            'depth': result.x[2],
            'shore_distance': result.x[3],
            'performance_score': -result.fun
        }
        
        logger.info(f"Selected optimal location: {optimal_location['coordinates']}")
        return optimal_location
    
    def optimize_unknown_capacity(self) -> Dict[str, Any]:
        """
        Economic capacity sizing with constraints
        
        Returns:
            Optimal capacity allocation and economic metrics
        """
        logger.info("Running capacity optimization...")
        
        capacity_var = self.design_variables['capacity']
        constraints = capacity_var.constraints
        
        total_range = constraints.get('total_range', [10, 500])
        tech_limits = constraints.get('individual_tech_limits', {})
        
        # Get technology mix (either known or from previous optimization)
        if self.design_variables['technology_mix'].status == VariableStatus.KNOWN:
            tech_mix = self.design_variables['technology_mix'].value
        else:
            # Need to run technology optimization first
            tech_result = self.optimize_unknown_technology()
            tech_mix = tech_result['technologies']
        
        # Set up capacity optimization bounds
        bounds = []
        tech_names = []
        
        for tech in tech_mix:
            if tech_mix[tech]:  # If technology is selected
                tech_bounds = tech_limits.get(tech, [1, total_range[1]])
                bounds.append(tech_bounds)
                tech_names.append(tech)
        
        # Add total capacity constraint
        def capacity_constraint(x):
            return total_range[1] - sum(x)  # Total capacity <= max
        
        def min_capacity_constraint(x):
            return sum(x) - total_range[0]  # Total capacity >= min
        
        constraints_list = [
            {'type': 'ineq', 'fun': capacity_constraint},
            {'type': 'ineq', 'fun': min_capacity_constraint}
        ]
        
        # Objective function for capacity optimization
        def capacity_objective(x):
            capacity_dict = dict(zip(tech_names, x))
            
            # Calculate economic performance
            economic_metrics = self._evaluate_capacity_economics(capacity_dict)
            
            # Return negative value to maximize (scipy minimizes)
            if self.optimization_config.objective == 'maximize_npv':
                return -economic_metrics['npv']
            elif self.optimization_config.objective == 'minimize_lcoe':
                return economic_metrics['lcoe']
            else:
                return -economic_metrics['npv']  # Default to NPV maximization
        
        # Initial guess (midpoint of ranges)
        x0 = [(b[0] + b[1]) / 2 for b in bounds]
        
        # Run optimization
        result = minimize(
            capacity_objective,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints_list
        )
        
        optimal_capacity = dict(zip(tech_names, result.x))
        
        # Calculate final economic metrics
        economic_metrics = self._evaluate_capacity_economics(optimal_capacity)
        
        optimal_result = {
            'capacity_mw': optimal_capacity,
            'total_capacity': sum(optimal_capacity.values()),
            'economic_metrics': economic_metrics,
            'optimization_success': result.success
        }
        
        logger.info(f"Selected optimal capacity: {optimal_capacity}")
        return optimal_result
    
    def run_adaptive_optimization(self) -> Dict[str, Any]:
        """
        Run complete adaptive optimization based on unknown variables
        
        Returns:
            Complete optimization results
        """
        logger.info(f"Starting adaptive optimization for {self.site_name}")
        
        # Determine optimization strategy
        strategy = self.determine_optimization_strategy()
        unknown_vars = self.identify_unknown_variables()
        
        results = {
            'site': self.site_name,
            'unknown_variables': unknown_vars,
            'optimization_strategy': strategy,
            'results': {}
        }
        
        # Run optimization for each unknown variable
        if 'technology_mix' in unknown_vars:
            results['results']['technology'] = self.optimize_unknown_technology()
        
        if 'location' in unknown_vars:
            results['results']['location'] = self.optimize_unknown_location()
        
        if 'capacity' in unknown_vars:
            results['results']['capacity'] = self.optimize_unknown_capacity()
        
        # Combine results for final integrated optimization if multiple unknowns
        if len(unknown_vars) > 1:
            results['results']['integrated'] = self._run_integrated_optimization(results['results'])
        
        logger.info("Adaptive optimization completed successfully")
        return results
    
    def _generate_tech_combinations(self, allowed_techs: List[str]) -> List[Dict[str, bool]]:
        """Generate all valid technology combinations"""
        from itertools import combinations
        
        tech_combos = []
        
        # Generate all possible combinations
        for r in range(1, len(allowed_techs) + 1):
            for combo in combinations(allowed_techs, r):
                tech_dict = {tech: tech in combo for tech in allowed_techs}
                tech_combos.append(tech_dict)
        
        return tech_combos
    
    def _evaluate_technology_performance(self, tech_mix: TechnologyMix) -> Dict[str, float]:
        """Evaluate performance metrics for a technology combination"""
        # Placeholder implementation - would integrate with actual models
        performance = {
            'capacity_factor': 0.35,  # Combined capacity factor
            'lcoe': 0.12,            # Levelized cost of energy
            'npv': 1000000,          # Net present value
            'environmental_score': 0.7,  # Environmental impact score (higher is better)
            'feasibility_score': 0.8    # Technical feasibility
        }
        
        return performance
    
    def _apply_environmental_weighting(self, performance: Dict[str, float], tech_mix: TechnologyMix) -> Dict[str, float]:
        """Apply environmental weighting to performance metrics"""
        env_weight = self.config['stakeholders']['decision_criteria']['environmental_weight']
        
        # Adjust performance based on environmental priorities
        adjusted_performance = performance.copy()
        
        # Boost environmental score importance
        env_factor = 1 + env_weight
        adjusted_performance['environmental_score'] *= env_factor
        
        # Calculate weighted composite score
        composite_score = (
            performance['npv'] * (1 - env_weight) + 
            performance['environmental_score'] * 1000000 * env_weight
        )
        
        adjusted_performance['composite_score'] = composite_score
        
        return adjusted_performance
    
    def _select_optimal_technology(self, results: List[Dict]) -> Dict[str, Any]:
        """Select optimal technology combination from results"""
        if self.optimization_config.objective == 'minimize_lcoe':
            optimal = min(results, key=lambda x: x['performance']['lcoe'])
        elif self.optimization_config.objective == 'maximize_npv':
            optimal = max(results, key=lambda x: x['performance']['npv'])
        else:
            # Use composite score if available, otherwise NPV
            if 'composite_score' in results[0]['performance']:
                optimal = max(results, key=lambda x: x['performance']['composite_score'])
            else:
                optimal = max(results, key=lambda x: x['performance']['npv'])
        
        return optimal
    
    def _point_in_exclusion_zones(self, lat: float, lon: float, exclusion_zones: List[Dict]) -> bool:
        """Check if point is within any exclusion zones"""
        # Simplified implementation - would integrate with GIS libraries
        for zone in exclusion_zones:
            if zone.get('priority') == 'critical':
                # Implement actual geometric checks here
                # For now, return False (not in exclusion zone)
                pass
        
        return False
    
    def _evaluate_location_performance(self, lat: float, lon: float, depth: float, shore_distance: float) -> float:
        """Evaluate performance score for a location"""
        # Placeholder implementation
        # Would integrate with resource assessment APIs and models
        
        # Basic scoring based on depth and distance
        depth_score = 1.0 - abs(depth - 30) / 50  # Optimal depth around 30m
        distance_score = 1.0 - shore_distance / 20  # Closer is better
        
        # Resource quality (would come from APIs)
        resource_score = 0.7  # Placeholder
        
        total_score = (depth_score + distance_score + resource_score) / 3
        
        return max(0, min(1, total_score))  # Clamp to [0, 1]
    
    def _evaluate_capacity_economics(self, capacity_dict: Dict[str, float]) -> Dict[str, float]:
        """Evaluate economic metrics for capacity allocation"""
        # Placeholder implementation - would integrate with economic models
        
        total_capacity = sum(capacity_dict.values())
        
        # Basic economic calculations
        capex = total_capacity * 3000000  # $3M per MW average
        annual_generation = total_capacity * 8760 * 0.35  # MWh/year
        revenue = annual_generation * 0.15 * 1000  # $150/MWh
        
        # Simple NPV calculation
        years = self.config['economic']['project_lifetime']
        discount_rate = self.config['economic']['discount_rate']
        
        npv = -capex
        for year in range(1, years + 1):
            npv += (revenue - capex * 0.03) / ((1 + discount_rate) ** year)  # 3% annual O&M
        
        lcoe = capex / (annual_generation * years / discount_rate)
        
        return {
            'npv': npv,
            'lcoe': lcoe,
            'total_capacity': total_capacity,
            'annual_generation': annual_generation
        }
    
    def _run_integrated_optimization(self, individual_results: Dict[str, Any]) -> Dict[str, Any]:
        """Run integrated optimization combining all unknown variables"""
        # Placeholder for integrated optimization
        # Would combine technology, location, and capacity optimization
        
        integrated_result = {
            'integrated_npv': 0,
            'integrated_lcoe': 0.12,
            'optimization_iterations': 50,
            'convergence': True
        }
        
        return integrated_result


class EnvironmentalAssessment:
    """Environmental impact assessment and constraint handling"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.environmental_data = config.get('environmental_constraints', {})
    
    def calculate_ecosystem_impact(self, technology_mix: Dict[str, bool], location: Tuple[float, float]) -> float:
        """Calculate ecosystem impact score"""
        # Placeholder implementation
        impact_score = 0.3  # 0 = no impact, 1 = high impact
        return impact_score
    
    def assess_visual_impact(self, location: Tuple[float, float], capacity: float) -> float:
        """Assess visual impact from shore"""
        # Placeholder implementation
        visual_impact = 0.4
        return visual_impact
    
    def evaluate_noise_impact(self, technology_mix: Dict[str, bool], location: Tuple[float, float]) -> float:
        """Evaluate noise impact on wildlife and community"""
        # Placeholder implementation
        noise_impact = 0.2
        return noise_impact
    
    def check_cultural_conflicts(self, location: Tuple[float, float]) -> List[str]:
        """Check for conflicts with cultural/traditional use areas"""
        # Placeholder implementation
        conflicts = []
        return conflicts
    
    def apply_stakeholder_weights(self, impact_scores: Dict[str, float]) -> float:
        """Apply stakeholder weighting to impact scores"""
        stakeholders = self.config.get('stakeholders', {})
        weights = stakeholders.get('decision_criteria', {})
        
        weighted_score = (
            impact_scores.get('economic', 0) * weights.get('economic_weight', 0.4) +
            impact_scores.get('environmental', 0) * weights.get('environmental_weight', 0.3) +
            impact_scores.get('social', 0) * weights.get('social_weight', 0.3)
        )
        
        return weighted_score
