"""
Step 1: Baseline Optimization

Deterministic optimization to find the optimal design configuration
under base case conditions without uncertainty.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import logging
from scipy.optimize import minimize, differential_evolution
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Results from baseline optimization"""
    optimal_config: Dict[str, Any]
    optimal_value: float
    optimization_details: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    convergence_info: Dict[str, Any]


class BaselineOptimization:
    """
    Baseline deterministic optimization for offshore renewable energy systems
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize baseline optimization
        
        Args:
            config: Configuration dictionary with site parameters, constraints, and objectives
        """
        self.config = config
        self.site_data = config.get('site_data', {})
        self.technology_options = config.get('technology_options', {})
        self.constraints = config.get('constraints', {})
        self.objectives = config.get('objectives', {})
        
        logger.info("Baseline optimization initialized")
    
    def optimize(self, target_type: str = "capacity", target_value: float = None) -> OptimizationResult:
        """
        Run baseline optimization
        
        Args:
            target_type: Type of target - "capacity", "energy", or "location"
            target_value: Target value (MW for capacity, MWh for energy)
            
        Returns:
            OptimizationResult with optimal configuration
        """
        logger.info(f"Starting baseline optimization with target: {target_type} = {target_value}")
        
        if target_type == "location":
            return self._optimize_location()
        elif target_type == "capacity":
            return self._optimize_capacity(target_value)
        elif target_type == "energy":
            return self._optimize_energy_target(target_value)
        else:
            raise ValueError(f"Unknown target type: {target_type}")
    
    def _optimize_location(self) -> OptimizationResult:
        """Optimize location selection"""
        logger.info("Optimizing location selection")
        
        # Get candidate locations from config
        candidate_locations = self.config.get('candidate_locations', [])
        
        if not candidate_locations:
            # Use single location from site_data
            location = {
                'latitude': self.site_data.get('latitude', 0),
                'longitude': self.site_data.get('longitude', 0)
            }
            candidate_locations = [location]
        
        best_location = None
        best_value = -np.inf
        location_results = []
        
        for i, location in enumerate(candidate_locations):
            logger.info(f"Evaluating location {i+1}/{len(candidate_locations)}: {location}")
            
            # Update site data with current location
            temp_config = self.config.copy()
            temp_config['site_data'].update(location)
            
            # Optimize technology mix for this location
            result = self._optimize_technology_mix(temp_config)
            
            location_result = {
                'location': location,
                'optimal_config': result['optimal_config'],
                'objective_value': result['objective_value'],
                'performance_metrics': result['performance_metrics']
            }
            
            location_results.append(location_result)
            
            if result['objective_value'] > best_value:
                best_value = result['objective_value']
                best_location = location_result
        
        return OptimizationResult(
            optimal_config=best_location['optimal_config'],
            optimal_value=best_value,
            optimization_details={
                'target_type': 'location',
                'locations_evaluated': len(candidate_locations),
                'all_location_results': location_results
            },
            performance_metrics=best_location['performance_metrics'],
            convergence_info={'status': 'success', 'method': 'exhaustive_search'}
        )
    
    def _optimize_capacity(self, target_capacity: float) -> OptimizationResult:
        """Optimize for target capacity"""
        logger.info(f"Optimizing for target capacity: {target_capacity} MW")
        
        # Define decision variables: capacity allocation across technologies
        technologies = list(self.technology_options.keys())
        n_tech = len(technologies)
        
        def objective_function(x):
            """Minimize LCOE while meeting capacity constraint"""
            capacities = dict(zip(technologies, x))
            
            # Check capacity constraint
            total_capacity = sum(capacities.values())
            if abs(total_capacity - target_capacity) > 0.1:  # 100 kW tolerance
                return 1e6  # Penalty for not meeting capacity
            
            # Calculate LCOE
            lcoe = self._calculate_lcoe(capacities)
            return lcoe
        
        # Bounds: each technology can be 0 to target_capacity
        bounds = [(0, target_capacity) for _ in technologies]
        
        # Constraint: total capacity must equal target
        constraints = [
            {'type': 'eq', 'fun': lambda x: sum(x) - target_capacity}
        ]
        
        # Initial guess: equal distribution
        x0 = [target_capacity / n_tech] * n_tech
        
        # Optimize
        result = minimize(
            objective_function,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            optimal_capacities = dict(zip(technologies, result.x))
            optimal_lcoe = result.fun
            
            performance_metrics = self._calculate_performance_metrics(optimal_capacities)
            
            return OptimizationResult(
                optimal_config={
                    'capacities': optimal_capacities,
                    'total_capacity_mw': sum(optimal_capacities.values()),
                    'lcoe_per_mwh': optimal_lcoe
                },
                optimal_value=-optimal_lcoe,  # Negative because we minimized
                optimization_details={
                    'target_type': 'capacity',
                    'target_value': target_capacity,
                    'optimization_method': 'SLSQP'
                },
                performance_metrics=performance_metrics,
                convergence_info={
                    'status': 'success',
                    'iterations': result.nit,
                    'function_evaluations': result.nfev
                }
            )
        else:
            logger.error(f"Optimization failed: {result.message}")
            raise RuntimeError(f"Baseline optimization failed: {result.message}")
    
    def _optimize_energy_target(self, target_energy: float) -> OptimizationResult:
        """Optimize for target energy production"""
        logger.info(f"Optimizing for target energy: {target_energy} MWh/year")
        
        technologies = list(self.technology_options.keys())
        
        def objective_function(x):
            """Minimize total cost while meeting energy target"""
            capacities = dict(zip(technologies, x))
            
            # Calculate annual energy production
            annual_energy = self._calculate_annual_energy(capacities)
            
            # Check energy constraint
            if annual_energy < target_energy * 0.99:  # Allow 1% shortfall
                return 1e6  # Penalty for not meeting energy target
            
            # Calculate total cost (CAPEX + OPEX NPV)
            total_cost = self._calculate_total_cost(capacities)
            return total_cost
        
        # Use differential evolution for global optimization
        max_individual_capacity = target_energy / 1000  # Conservative upper bound
        bounds = [(0, max_individual_capacity) for _ in technologies]
        
        result = differential_evolution(
            objective_function,
            bounds,
            maxiter=1000,
            popsize=15,
            seed=42
        )
        
        if result.success:
            optimal_capacities = dict(zip(technologies, result.x))
            optimal_cost = result.fun
            
            performance_metrics = self._calculate_performance_metrics(optimal_capacities)
            
            return OptimizationResult(
                optimal_config={
                    'capacities': optimal_capacities,
                    'total_capacity_mw': sum(optimal_capacities.values()),
                    'annual_energy_mwh': self._calculate_annual_energy(optimal_capacities),
                    'total_cost_usd': optimal_cost
                },
                optimal_value=-optimal_cost,  # Negative because we minimized cost
                optimization_details={
                    'target_type': 'energy',  
                    'target_value': target_energy,
                    'optimization_method': 'differential_evolution'
                },
                performance_metrics=performance_metrics,
                convergence_info={
                    'status': 'success',
                    'iterations': result.nit,
                    'function_evaluations': result.nfev
                }
            )
        else:
            logger.error(f"Energy target optimization failed: {result.message}")
            raise RuntimeError(f"Energy target optimization failed: {result.message}")
    
    def _optimize_technology_mix(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize technology mix for a given location"""
        
        # Get resource data for this location
        resource_quality = self._get_resource_quality(config['site_data'])
        
        # Simple heuristic optimization based on resource quality
        technologies = list(self.technology_options.keys())
        optimal_mix = {}
        
        # Allocate capacity based on resource quality and cost
        total_capacity = 100  # Default 100 MW system
        
        for tech in technologies:
            if tech in resource_quality:
                quality_score = resource_quality[tech].get('capacity_factor', 0.3)
                cost_factor = self.technology_options[tech].get('cost_factor', 1.0)
                
                # Simple scoring: higher capacity factor and lower cost is better
                score = quality_score / cost_factor
                optimal_mix[tech] = score
        
        # Normalize to total capacity
        total_score = sum(optimal_mix.values())
        if total_score > 0:
            for tech in optimal_mix:
                optimal_mix[tech] = optimal_mix[tech] / total_score * total_capacity
        
        # Calculate performance metrics
        lcoe = self._calculate_lcoe(optimal_mix)
        annual_energy = self._calculate_annual_energy(optimal_mix)
        
        return {
            'optimal_config': optimal_mix,
            'objective_value': -lcoe,  # Negative LCOE as objective (higher is better)
            'performance_metrics': {
                'lcoe_per_mwh': lcoe,
                'annual_energy_mwh': annual_energy,
                'capacity_factor': annual_energy / (sum(optimal_mix.values()) * 8760) if sum(optimal_mix.values()) > 0 else 0
            }
        }
    
    def _get_resource_quality(self, site_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get resource quality estimates for the site"""
        lat = site_data.get('latitude', 0)
        lon = site_data.get('longitude', 0)
        
        # Simplified resource quality estimation
        resource_quality = {}
        
        # Wind resource (higher at high latitudes and coastal areas)
        wind_cf = 0.35 + 0.1 * (abs(lat) / 60) + 0.05 * (1 / (1 + abs(lon) / 100))
        wind_cf = min(wind_cf, 0.6)  # Cap at 60%
        
        resource_quality['wind'] = {
            'capacity_factor': wind_cf,
            'resource_quality': 'excellent' if wind_cf > 0.45 else 'good' if wind_cf > 0.35 else 'fair'
        }
        
        # Solar resource (higher near equator)
        solar_cf = 0.25 - 0.15 * (abs(lat) / 90)
        solar_cf = max(solar_cf, 0.1)  # Minimum 10%
        
        resource_quality['solar'] = {
            'capacity_factor': solar_cf,
            'resource_quality': 'excellent' if solar_cf > 0.25 else 'good' if solar_cf > 0.20 else 'fair'
        }
        
        # Wave resource (higher in mid to high latitudes, coastal areas)
        wave_cf = 0.25 + 0.1 * (abs(lat) / 60) if abs(lat) > 30 else 0.15
        wave_cf = min(wave_cf, 0.4)  # Cap at 40%
        
        resource_quality['wave'] = {
            'capacity_factor': wave_cf,
            'resource_quality': 'excellent' if wave_cf > 0.35 else 'good' if wave_cf > 0.25 else 'fair'
        }
        
        return resource_quality
    
    def _calculate_lcoe(self, capacities: Dict[str, float]) -> float:
        """Calculate Levelized Cost of Energy"""
        total_capex = 0
        total_opex_annual = 0
        total_energy_annual = 0
        
        for tech, capacity in capacities.items():
            if capacity > 0:
                tech_data = self.technology_options.get(tech, {})
                
                # CAPEX
                capex_per_kw = tech_data.get('capex_per_kw', 2000)
                total_capex += capacity * 1000 * capex_per_kw  # Convert MW to kW
                
                # Annual OPEX
                opex_per_kw_year = tech_data.get('opex_per_kw_year', 50)
                total_opex_annual += capacity * 1000 * opex_per_kw_year
                
                # Annual energy
                capacity_factor = tech_data.get('capacity_factor', 0.35)
                annual_energy = capacity * 8760 * capacity_factor  # MWh
                total_energy_annual += annual_energy
        
        if total_energy_annual == 0:
            return 1e6  # Very high LCOE if no energy production
        
        # LCOE calculation (simplified)
        discount_rate = 0.08
        project_life = 25
        
        # Present value of OPEX
        pv_opex = total_opex_annual * ((1 - (1 + discount_rate)**(-project_life)) / discount_rate)
        
        # LCOE
        lcoe = (total_capex + pv_opex) / (total_energy_annual * ((1 - (1 + discount_rate)**(-project_life)) / discount_rate))
        
        return lcoe
    
    def _calculate_annual_energy(self, capacities: Dict[str, float]) -> float:
        """Calculate total annual energy production"""
        total_energy = 0
        
        for tech, capacity in capacities.items():
            if capacity > 0:
                tech_data = self.technology_options.get(tech, {})
                capacity_factor = tech_data.get('capacity_factor', 0.35)
                annual_energy = capacity * 8760 * capacity_factor  # MWh
                total_energy += annual_energy
        
        return total_energy
    
    def _calculate_total_cost(self, capacities: Dict[str, float]) -> float:
        """Calculate total project cost (CAPEX + OPEX NPV)"""
        total_capex = 0
        total_opex_pv = 0
        
        discount_rate = 0.08
        project_life = 25
        
        for tech, capacity in capacities.items():
            if capacity > 0:
                tech_data = self.technology_options.get(tech, {})
                
                # CAPEX
                capex_per_kw = tech_data.get('capex_per_kw', 2000)
                capex = capacity * 1000 * capex_per_kw  # Convert MW to kW
                total_capex += capex
                
                # OPEX present value
                opex_per_kw_year = tech_data.get('opex_per_kw_year', 50)
                annual_opex = capacity * 1000 * opex_per_kw_year
                pv_opex = annual_opex * ((1 - (1 + discount_rate)**(-project_life)) / discount_rate)
                total_opex_pv += pv_opex
        
        return total_capex + total_opex_pv
    
    def _calculate_performance_metrics(self, capacities: Dict[str, float]) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics"""
        metrics = {}
        
        # Basic metrics
        total_capacity = sum(capacities.values())
        annual_energy = self._calculate_annual_energy(capacities)
        total_cost = self._calculate_total_cost(capacities)
        lcoe = self._calculate_lcoe(capacities)
        
        metrics.update({
            'total_capacity_mw': total_capacity,
            'annual_energy_mwh': annual_energy,
            'total_cost_usd': total_cost,
            'lcoe_per_mwh': lcoe,
            'overall_capacity_factor': annual_energy / (total_capacity * 8760) if total_capacity > 0 else 0
        })
        
        # Technology breakdown
        tech_breakdown = {}
        for tech, capacity in capacities.items():
            if capacity > 0:
                tech_data = self.technology_options.get(tech, {})
                cf = tech_data.get('capacity_factor', 0.35)
                
                tech_breakdown[tech] = {
                    'capacity_mw': capacity,
                    'capacity_share': capacity / total_capacity if total_capacity > 0 else 0,
                    'annual_energy_mwh': capacity * 8760 * cf,
                    'capacity_factor': cf
                }
        
        metrics['technology_breakdown'] = tech_breakdown
        
        # Financial metrics
        metrics['financial_metrics'] = {
            'capex_per_kw': total_cost * 0.7 / (total_capacity * 1000) if total_capacity > 0 else 0,  # Assuming 70% CAPEX
            'opex_per_kw_year': total_cost * 0.3 / 25 / (total_capacity * 1000) if total_capacity > 0 else 0,  # Assuming 30% OPEX over 25 years
            'energy_yield_kwh_per_kw': annual_energy * 1000 / (total_capacity * 1000) if total_capacity > 0 else 0
        }
        
        return metrics
    
    def sensitivity_analysis(self, optimal_result: OptimizationResult, parameters: List[str] = None) -> Dict[str, Any]:
        """
        Perform sensitivity analysis on the optimal solution
        
        Args:
            optimal_result: Result from baseline optimization
            parameters: List of parameters to analyze
            
        Returns:
            Sensitivity analysis results
        """
        if parameters is None:
            parameters = ['wind_capex', 'solar_capex', 'wave_capex', 'discount_rate']
        
        sensitivity_results = {}
        base_lcoe = optimal_result.performance_metrics['lcoe_per_mwh']
        
        for param in parameters:
            param_results = []
            
            # Test ±20% variation in 5% steps
            for variation in np.arange(-0.2, 0.25, 0.05):
                # Modify parameter
                modified_config = self._modify_parameter(self.config, param, variation)
                
                # Re-optimize with modified parameter
                temp_optimizer = BaselineOptimization(modified_config)
                try:
                    result = temp_optimizer._optimize_technology_mix(modified_config)
                    new_lcoe = result['performance_metrics']['lcoe_per_mwh']
                    
                    param_results.append({
                        'parameter_change': variation,
                        'lcoe_change': (new_lcoe - base_lcoe) / base_lcoe,
                        'absolute_lcoe': new_lcoe
                    })
                except Exception as e:
                    logger.warning(f"Sensitivity analysis failed for {param} at {variation}: {e}")
            
            sensitivity_results[param] = param_results
        
        return sensitivity_results
    
    def _modify_parameter(self, config: Dict[str, Any], parameter: str, variation: float) -> Dict[str, Any]:
        """Modify a parameter for sensitivity analysis"""
        modified_config = config.copy()
        
        if parameter == 'discount_rate':
            modified_config['financial_parameters'] = modified_config.get('financial_parameters', {})
            base_rate = modified_config['financial_parameters'].get('discount_rate', 0.08)
            modified_config['financial_parameters']['discount_rate'] = base_rate * (1 + variation)
            
        elif parameter.endswith('_capex'):
            tech = parameter.replace('_capex', '')
            if tech in modified_config['technology_options']:
                base_capex = modified_config['technology_options'][tech].get('capex_per_kw', 2000)
                modified_config['technology_options'][tech]['capex_per_kw'] = base_capex * (1 + variation)
        
        return modified_config
