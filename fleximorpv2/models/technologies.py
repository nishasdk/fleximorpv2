"""
Technology model for offshore renewable energy systems.

Handles performance modeling for wind, solar, and wave technologies
including resource assessment, capacity factor calculations, and
technology-specific constraints.
"""

import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
import math

from ..config import SiteConfig, TechnologyConfig


@dataclass
class TechnologyPerformance:
    """Performance metrics for a specific technology."""
    capacity: float  # MW
    capacity_factor: float  # 0-1
    annual_energy: float  # MWh/year
    availability: float  # 0-1
    degradation_rate: float  # per year
    space_requirement: float  # m²/MW
    load_requirement: float  # tonnes/MW


@dataclass
class ResourceData:
    """Resource data for technology performance calculations."""
    wind_speed: np.ndarray  # m/s
    solar_irradiance: np.ndarray  # W/m²
    wave_height: np.ndarray  # m
    wave_period: np.ndarray  # s
    temperature: np.ndarray  # °C
    timestamps: np.ndarray


class TechnologyModel:
    """
    Model for renewable energy technology performance on offshore platforms.
    
    Handles wind, solar, and wave energy technologies with site-specific
    resource assessment and performance calculations.
    """
    
    def __init__(self, config: SiteConfig):
        """
        Initialize technology model.
        
        Args:
            config: Site configuration object
        """
        self.config = config
        self.performance_data: Dict[str, TechnologyPerformance] = {}
        
        # Technology-specific parameters
        self.technology_params = {
            'wind': {
                'cut_in_speed': 3.0,  # m/s
                'rated_speed': 12.0,  # m/s
                'cut_out_speed': 25.0,  # m/s
                'air_density': 1.225,  # kg/m³
                'wake_loss': 0.15,  # 15% wake losses
                'area_per_mw': 300,  # m² per MW (including spacing)
                'load_per_mw': 80,  # tonnes per MW
                'hub_height_default': 100,  # meters
                'rotor_diameter_default': 120  # meters
            },
            'solar': {
                'standard_irradiance': 1000,  # W/m²
                'temperature_coefficient': -0.004,  # per °C
                'standard_temperature': 25,  # °C
                'degradation_rate': 0.005,  # per year
                'area_per_mw': 4000,  # m² per MW
                'load_per_mw': 15,  # tonnes per MW
                'tilt_angle_default': 35,  # degrees
                'tracking_gain': 1.25  # tracking vs fixed tilt
            },
            'wave': {
                'optimal_wave_height': 2.5,  # m
                'optimal_wave_period': 8.0,  # s
                'max_operational_height': 6.0,  # m
                'power_conversion_efficiency': 0.35,
                'area_per_mw': 500,  # m² per MW
                'load_per_mw': 120,  # tonnes per MW
                'availability_factor': 0.90
            }
        }
    
    def calculate_performance(self, 
                            design_vars: Dict[str, Any], 
                            resource_data: ResourceData) -> Dict[str, float]:
        """
        Calculate technology performance for given design and resource data.
        
        Args:
            design_vars: Design variables including technology capacities
            resource_data: Site resource data
            
        Returns:
            Dictionary with combined technology performance metrics
        """
        self.performance_data = {}
        combined_metrics = {}
        
        total_capacity = 0.0
        total_annual_energy = 0.0
        total_space_requirement = 0.0
        total_load_requirement = 0.0
        
        # Calculate performance for each enabled technology
        for tech_name in self.config.get_enabled_technologies():
            capacity = design_vars.get(f'{tech_name}_capacity', 0.0)
            
            if capacity > 0:
                performance = self._calculate_technology_performance(
                    tech_name, capacity, resource_data, design_vars
                )
                self.performance_data[tech_name] = performance
                
                # Accumulate totals
                total_capacity += performance.capacity
                total_annual_energy += performance.annual_energy
                total_space_requirement += performance.space_requirement
                total_load_requirement += performance.load_requirement
                
                # Add technology-specific metrics
                combined_metrics.update({
                    f'{tech_name}_capacity_factor': performance.capacity_factor,
                    f'{tech_name}_annual_energy': performance.annual_energy,
                    f'{tech_name}_availability': performance.availability
                })
        
        # Calculate combined metrics
        combined_capacity_factor = total_annual_energy / (total_capacity * 8760) if total_capacity > 0 else 0.0
        
        combined_metrics.update({
            'total_capacity': total_capacity,
            'annual_energy': total_annual_energy,
            'capacity_factor': combined_capacity_factor,
            'total_space_requirement': total_space_requirement,
            'total_load_requirement': total_load_requirement,
            'technology_diversity': len(self.performance_data)
        })
        
        return combined_metrics
    
    def _calculate_technology_performance(self, 
                                        tech_name: str, 
                                        capacity: float, 
                                        resource_data: ResourceData,
                                        design_vars: Optional[Dict[str, Any]] = None) -> TechnologyPerformance:
        """Calculate performance for a specific technology."""
        
        if tech_name == 'wind':
            return self._calculate_wind_performance(capacity, resource_data)
        elif tech_name == 'solar':
            return self._calculate_solar_performance(capacity, resource_data, design_vars)
        elif tech_name == 'wave':
            return self._calculate_wave_performance(capacity, resource_data)
        elif tech_name.startswith('hydro_river_flow'):
            return self._calculate_hydro_performance(tech_name, capacity, resource_data)
        else:
            raise ValueError(f"Unknown technology: {tech_name}")
    
    def _calculate_wind_performance(self, 
                                   capacity: float, 
                                   resource_data: ResourceData) -> TechnologyPerformance:
        """Calculate wind turbine performance."""
        params = self.technology_params['wind']
        tech_config = self.config.technologies['wind']
        
        # Get wind speeds
        wind_speeds = resource_data.wind_speed
        
        # Apply height correction if needed
        technical_params = tech_config.technical_params if tech_config.technical_params is not None else {}
        hub_height = technical_params.get('hub_height', params['hub_height_default'])
        if hub_height != 10:  # Assuming data is at 10m
            wind_speeds = wind_speeds * (hub_height / 10) ** 0.143  # Wind shear law
        
        # Calculate power output for each timestep
        power_outputs = np.zeros_like(wind_speeds)
        
        for i, wind_speed in enumerate(wind_speeds):
            power_outputs[i] = self._wind_power_curve(wind_speed, params)
        
        # Apply wake losses
        power_outputs *= (1 - params['wake_loss'])
        
        # Calculate capacity factor
        average_power = np.mean(power_outputs)  # MW
        capacity_factor = average_power / capacity if capacity > 0 else 0.0
        
        # Calculate annual energy
        annual_energy = capacity_factor * capacity * 8760  # MWh/year
        
        # Apply availability factor
        technical_params = tech_config.technical_params if tech_config.technical_params is not None else {}
        availability = technical_params.get('availability', 0.95)
        annual_energy *= availability
        
        return TechnologyPerformance(
            capacity=capacity,
            capacity_factor=capacity_factor * availability,
            annual_energy=annual_energy,
            availability=availability,
            degradation_rate=0.002,  # 0.2% per year for wind
            space_requirement=capacity * params['area_per_mw'],
            load_requirement=capacity * params['load_per_mw']
        )
    
    def _wind_power_curve(self, wind_speed: float, params: Dict[str, float]) -> float:
        """Wind turbine power curve."""
        cut_in = params['cut_in_speed']
        rated = params['rated_speed']
        cut_out = params['cut_out_speed']
        
        if wind_speed < cut_in or wind_speed > cut_out:
            return 0.0
        elif wind_speed <= rated:
            # Cubic relationship between cut-in and rated
            return ((wind_speed - cut_in) / (rated - cut_in)) ** 3
        else:
            # Constant power at rated output
            return 1.0
    
    def _calculate_solar_performance(self, 
                                    capacity: float, 
                                    resource_data: ResourceData,
                                    design_vars: Optional[Dict[str, Any]] = None) -> TechnologyPerformance:
        """Calculate solar PV performance with deployment-specific enhancements."""
        params = self.technology_params['solar']
        tech_config = self.config.technologies['solar']
        
        # Determine deployment type and get performance modifiers
        deployment_type, deployment_config = self._determine_solar_deployment_type(design_vars)
        
        # Get solar irradiance and temperature
        irradiance = resource_data.solar_irradiance  # W/m²
        temperature = resource_data.temperature  # °C
        
        # Calculate seasonal factor for ice impact (Alaska-specific)
        seasonal_factor = self._calculate_seasonal_ice_factor(resource_data.timestamps, deployment_config)
        
        # Calculate power output for each timestep
        power_outputs = np.zeros_like(irradiance)
        
        for i, (irr, temp) in enumerate(zip(irradiance, temperature)):
            # Basic solar PV equation
            power_ratio = irr / params['standard_irradiance']
            
            # Temperature correction with enhanced cooling for floating
            if deployment_type == 'floating':
                # Water cooling reduces effective operating temperature
                cooling_benefit = deployment_config.get('additional_benefits', {}).get('water_cooling_effect', 0.0)
                effective_temp = temp - (cooling_benefit * 100 * 0.5)  # Approximate cooling effect
            else:
                effective_temp = temp
            
            temp_diff = effective_temp - params['standard_temperature']
            temp_factor = 1 + params['temperature_coefficient'] * temp_diff
            
            # Apply albedo reflection benefit for floating systems
            if deployment_type == 'floating':
                albedo_boost = deployment_config.get('additional_benefits', {}).get('albedo_reflection', 0.0)
                power_ratio *= (1 + albedo_boost)
            
            power_outputs[i] = power_ratio * temp_factor
        
        # Apply panel efficiency
        panel_efficiency = tech_config.technical_params.get('panel_efficiency', 0.20)
        power_outputs *= panel_efficiency / 0.20  # Normalize to 20% reference
        
        # Apply tracking gain if applicable
        tracking = tech_config.technical_params.get('tracking', False)
        if tracking:
            power_outputs *= params['tracking_gain']
        
        # Apply deployment-specific capacity factor modifier
        cf_modifier = deployment_config.get('capacity_factor_modifier', 1.0)
        power_outputs *= cf_modifier
        
        # Apply reduced soiling benefit for floating systems
        if deployment_type == 'floating':
            soiling_reduction = deployment_config.get('additional_benefits', {}).get('reduced_soiling', 0.0)
            power_outputs *= (1 + soiling_reduction)
        
        # Apply seasonal ice impact
        power_outputs *= seasonal_factor
        
        # Clip to maximum capacity
        power_outputs = np.clip(power_outputs, 0, 1.0)
        
        # Calculate capacity factor
        capacity_factor = np.mean(power_outputs)
        
        # Calculate annual energy
        annual_energy = capacity_factor * capacity * 8760  # MWh/year
        
        # Apply availability factor
        availability = tech_config.technical_params.get('availability', 0.98)
        annual_energy *= availability
        
        # Get space and load requirements based on deployment type
        area_per_mw = deployment_config.get('area_per_mw', params['area_per_mw'])
        load_per_mw = params['load_per_mw']
        
        # Adjust load for floating platforms
        if deployment_type == 'floating':
            load_per_mw *= 1.2  # Additional load for floating structure
        
        return TechnologyPerformance(
            capacity=capacity,
            capacity_factor=capacity_factor * availability,
            annual_energy=annual_energy,
            availability=availability,
            degradation_rate=params['degradation_rate'],
            space_requirement=capacity * area_per_mw,
            load_requirement=capacity * load_per_mw
        )
    
    def _calculate_wave_performance(self, 
                                   capacity: float, 
                                   resource_data: ResourceData) -> TechnologyPerformance:
        """Calculate wave energy converter performance."""
        params = self.technology_params['wave']
        tech_config = self.config.technologies['wave']
        
        # Get wave data
        wave_heights = resource_data.wave_height  # m
        wave_periods = resource_data.wave_period  # s
        
        # Calculate wave power for each timestep
        power_outputs = np.zeros_like(wave_heights)
        
        for i, (height, period) in enumerate(zip(wave_heights, wave_periods)):
            # Wave power calculation (simplified)
            wave_power_density = self._calculate_wave_power_density(height, period)
            
            # Device performance curve
            device_efficiency = self._wave_device_efficiency(height, period, params)
            
            power_outputs[i] = wave_power_density * device_efficiency * params['power_conversion_efficiency']
        
        # Normalize to capacity
        max_power = np.max(power_outputs)
        if max_power > 0:
            power_outputs = power_outputs / max_power
        
        # Calculate capacity factor
        capacity_factor = np.mean(power_outputs)
        
        # Calculate annual energy
        annual_energy = capacity_factor * capacity * 8760  # MWh/year
        
        # Apply availability factor
        availability = params['availability_factor']
        annual_energy *= availability
        
        return TechnologyPerformance(
            capacity=capacity,
            capacity_factor=capacity_factor * availability,
            annual_energy=annual_energy,
            availability=availability,
            degradation_rate=0.01,  # 1% per year for wave (higher due to harsh environment)
            space_requirement=capacity * params['area_per_mw'],
            load_requirement=capacity * params['load_per_mw']
        )
    
    def _calculate_wave_power_density(self, height: float, period: float) -> float:
        """Calculate wave power density."""
        # Simplified wave power calculation
        # P = (ρg²/64π) * H² * T where ρ=1025 kg/m³, g=9.81 m/s²
        rho = 1025  # kg/m³ (seawater density)
        g = 9.81    # m/s²
        
        power_density = (rho * g**2 / (64 * math.pi)) * height**2 * period
        return power_density / 1000  # Convert to kW/m
    
    def _wave_device_efficiency(self, height: float, period: float, params: Dict[str, float]) -> float:
        """Calculate wave energy converter efficiency."""
        optimal_height = params['optimal_wave_height']
        optimal_period = params['optimal_wave_period']
        max_height = params['max_operational_height']
        
        # Device can't operate above maximum height
        if height > max_height:
            return 0.0
        
        # Efficiency curve based on distance from optimal conditions
        height_efficiency = 1.0 - abs(height - optimal_height) / optimal_height
        period_efficiency = 1.0 - abs(period - optimal_period) / optimal_period
        
        # Combined efficiency
        efficiency = max(0.0, height_efficiency * period_efficiency)
        
        return efficiency
    
    def _determine_solar_deployment_type(self, design_vars: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
        """Determine optimal solar deployment type and return configuration."""
        tech_config = self.config.technologies['solar']
        
        # Check if deployment options are available in technical_params
        if 'deployment_options' not in tech_config.technical_params:
            return 'land', {'capacity_factor_modifier': 1.0, 'area_per_mw': 4000}
        
        deployment_options = tech_config.technical_params['deployment_options']
        
        # Check if user specified deployment type in design_vars
        if design_vars and 'solar_deployment_type' in design_vars:
            specified_type = design_vars['solar_deployment_type']
            if specified_type in deployment_options and deployment_options[specified_type]['available']:
                return specified_type, deployment_options[specified_type]
        
        # Check if 'both' option is available and should be optimized
        if 'both' in deployment_options and deployment_options['both']['available']:
            # Implement automatic deployment type selection
            return self._optimize_solar_deployment_type(deployment_options)
        
        # Default to first available deployment type
        for deploy_type, config in deployment_options.items():
            if config.get('available', False) and deploy_type != 'both':
                return deploy_type, config
        
        # Fallback to land deployment
        return 'land', {'capacity_factor_modifier': 1.0, 'area_per_mw': 4000}
    
    def _optimize_solar_deployment_type(self, deployment_options: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Automatically select optimal solar deployment type based on performance and cost."""
        land_config = deployment_options.get('land', {})
        floating_config = deployment_options.get('floating', {})
        both_config = deployment_options.get('both', {})
        
        # Get optimization strategy
        strategy = both_config.get('optimization_strategy', 'minimize_lcoe')
        performance_weighting = both_config.get('performance_weighting', 'capacity_factor')
        
        # Simple decision logic based on capacity factor advantage
        if strategy == 'minimize_lcoe':
            # Calculate relative performance advantage
            land_cf_modifier = land_config.get('capacity_factor_modifier', 1.0)
            floating_cf_modifier = floating_config.get('capacity_factor_modifier', 1.0)
            
            # Calculate relative cost
            land_cost_multiplier = land_config.get('cost_multiplier', 1.0)
            floating_cost_multiplier = floating_config.get('cost_multiplier', 1.0)
            
            # Simple LCOE approximation: cost / performance
            land_lcoe_factor = land_cost_multiplier / land_cf_modifier
            floating_lcoe_factor = floating_cost_multiplier / floating_cf_modifier
            
            # Choose deployment type with better LCOE
            if floating_lcoe_factor <= land_lcoe_factor:
                return 'floating', floating_config
            else:
                return 'land', land_config
        
        # Default to floating if performance weighting favors it
        if performance_weighting == 'capacity_factor':
            floating_cf = floating_config.get('capacity_factor_modifier', 1.0)
            land_cf = land_config.get('capacity_factor_modifier', 1.0)
            
            if floating_cf > land_cf:
                return 'floating', floating_config
        
        # Default fallback to land
        return 'land', land_config
    
    def _calculate_seasonal_ice_factor(self, timestamps: np.ndarray, deployment_config: Dict[str, Any]) -> float:
        """Calculate seasonal ice impact factor for Arctic deployments."""
        # Check if this is a floating deployment with ice impact
        if 'seasonal_ice_impact' not in deployment_config:
            return 1.0  # No ice impact for land deployments
        
        ice_impact_factor = deployment_config['seasonal_ice_impact']
        
        # Simplified seasonal calculation
        # Assume winter months (Nov-Mar) have reduced performance
        # This would need actual timestamp analysis in a full implementation
        winter_fraction = 0.4  # Approximate fraction of year affected by ice
        
        # Calculate weighted average: normal performance most of year, reduced in winter
        seasonal_factor = (1.0 * (1 - winter_fraction)) + (ice_impact_factor * winter_fraction)
        
        return seasonal_factor
    
    def _calculate_hydro_performance(self, 
                                   tech_name: str,
                                   capacity: float, 
                                   resource_data: ResourceData) -> TechnologyPerformance:
        """Calculate hydro technology performance (river flow, wave, tidal)."""
        # Get hydro configuration
        hydro_config = self.config.technologies.get('hydro_river_flow', {})
        
        # Determine hydro subtype
        if 'river_flow' in tech_name:
            return self._calculate_river_flow_performance(capacity, resource_data, hydro_config)
        elif 'wave' in tech_name:
            return self._calculate_wave_performance(capacity, resource_data)
        elif 'tidal' in tech_name:
            return self._calculate_tidal_performance(capacity, resource_data, hydro_config)
        else:
            # Default hydro performance
            return TechnologyPerformance(
                capacity=capacity,
                capacity_factor=0.25,
                annual_energy=capacity * 0.25 * 8760,
                availability=0.90,
                degradation_rate=0.01,
                space_requirement=capacity * 500,
                load_requirement=capacity * 100
            )
    
    def _calculate_river_flow_performance(self, 
                                        capacity: float, 
                                        resource_data: ResourceData,
                                        hydro_config: Dict[str, Any]) -> TechnologyPerformance:
        """Calculate river flow turbine performance."""
        river_flow_config = hydro_config.get('hydro_river_flow', {})
        
        # Base capacity factor from config
        base_cf = river_flow_config.get('capacity_factor', 0.25)
        
        # Apply seasonal variation
        seasonal_variation = river_flow_config.get('seasonal_variation', False)
        if seasonal_variation:
            # Simplified seasonal flow modeling
            # Spring melt increases flow, winter decreases it
            seasonal_cf_modifier = 1.0  # Would need actual flow data for proper calculation
        else:
            seasonal_cf_modifier = 1.0
        
        capacity_factor = base_cf * seasonal_cf_modifier
        annual_energy = capacity_factor * capacity * 8760
        
        # Apply availability
        availability = 0.85  # Lower than solar/wind due to maintenance complexity
        annual_energy *= availability
        
        # Get technical parameters
        tech_params = river_flow_config.get('technical_params', {})
        area_per_mw = 100  # Small footprint for river turbines
        load_per_mw = 150  # Heavy underwater equipment
        
        return TechnologyPerformance(
            capacity=capacity,
            capacity_factor=capacity_factor * availability,
            annual_energy=annual_energy,
            availability=availability,
            degradation_rate=0.015,  # Higher due to underwater environment
            space_requirement=capacity * area_per_mw,
            load_requirement=capacity * load_per_mw
        )
    
    def _calculate_tidal_performance(self, 
                                   capacity: float, 
                                   resource_data: ResourceData,
                                   hydro_config: Dict[str, Any]) -> TechnologyPerformance:
        """Calculate tidal energy converter performance."""
        tidal_config = hydro_config.get('tidal_range', {})
        
        if not tidal_config.get('available', False):
            # Return minimal performance for unavailable tidal
            return TechnologyPerformance(
                capacity=capacity,
                capacity_factor=0.0,
                annual_energy=0.0,
                availability=0.0,
                degradation_rate=0.02,
                space_requirement=capacity * 500,
                load_requirement=capacity * 200
            )
        
        # Tidal-specific calculations would go here
        # For now, return basic performance
        capacity_factor = 0.35
        annual_energy = capacity_factor * capacity * 8760 * 0.90
        
        return TechnologyPerformance(
            capacity=capacity,
            capacity_factor=capacity_factor * 0.90,
            annual_energy=annual_energy,
            availability=0.90,
            degradation_rate=0.02,
            space_requirement=capacity * 500,
            load_requirement=capacity * 200
        )
    
    def get_technology_requirements(self, design_vars: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """
        Get space and load requirements for each technology.
        
        Args:
            design_vars: Design variables including technology capacities
            
        Returns:
            Dictionary with technology requirements
        """
        requirements = {}
        
        for tech_name in self.config.get_enabled_technologies():
            capacity = design_vars.get(f'{tech_name}_capacity', 0.0)
            
            if capacity > 0:
                params = self.technology_params[tech_name]
                requirements[tech_name] = {
                    'capacity': capacity,
                    'area_per_mw': params['area_per_mw'],
                    'load_per_mw': params['load_per_mw'],
                    'total_area': capacity * params['area_per_mw'],
                    'total_load': capacity * params['load_per_mw']
                }
        
        return requirements
    
    def calculate_synergies(self) -> Dict[str, float]:
        """Calculate synergies between different technologies."""
        if len(self.performance_data) < 2:
            return {'synergy_factor': 1.0}
        
        synergies = {}
        
        # Wind-Solar synergy (complementary generation patterns)
        if 'wind' in self.performance_data and 'solar' in self.performance_data:
            wind_cf = self.performance_data['wind'].capacity_factor
            solar_cf = self.performance_data['solar'].capacity_factor
            
            # Higher synergy when capacity factors are similar
            cf_difference = abs(wind_cf - solar_cf)
            wind_solar_synergy = 1.0 + (0.1 * (1.0 - cf_difference))
            synergies['wind_solar_synergy'] = wind_solar_synergy
        
        # Platform utilization synergy (better use of platform space)
        total_technologies = len(self.performance_data)
        if total_technologies > 1:
            utilization_synergy = 1.0 + (0.05 * (total_technologies - 1))
            synergies['utilization_synergy'] = utilization_synergy
        
        # Overall synergy factor
        synergy_factor = np.mean(list(synergies.values())) if synergies else 1.0
        synergies['synergy_factor'] = synergy_factor
        
        return synergies
    
    def calculate_technology_costs(self, design_vars: Dict[str, Any]) -> Dict[str, float]:
        """Calculate technology-specific costs."""
        costs = {}
        total_capex = 0.0
        total_opex = 0.0
        
        for tech_name in self.config.get_enabled_technologies():
            capacity = design_vars.get(f'{tech_name}_capacity', 0.0)
            
            if capacity > 0:
                tech_config = self.config.technologies[tech_name]
                
                # CAPEX calculation
                capex_per_mw = tech_config.cost_per_mw
                tech_capex = capacity * capex_per_mw
                
                # OPEX calculation (percentage of CAPEX)
                opex_rate = {
                    'wind': 0.03,    # 3% of CAPEX per year
                    'solar': 0.015,  # 1.5% of CAPEX per year
                    'wave': 0.05     # 5% of CAPEX per year (higher maintenance)
                }.get(tech_name, 0.03)
                
                tech_opex = tech_capex * opex_rate
                
                costs[f'{tech_name}_capex'] = tech_capex
                costs[f'{tech_name}_opex'] = tech_opex
                
                total_capex += tech_capex
                total_opex += tech_opex
        
        costs.update({
            'total_technology_capex': total_capex,
            'total_technology_opex': total_opex
        })
        
        return costs
    
    def validate_technology_integration(self, design_vars: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate that technologies can be integrated together."""
        issues = []
        
        # Get technology requirements
        requirements = self.get_technology_requirements(design_vars)
        
        # Check for technology conflicts
        enabled_techs = list(requirements.keys())
        
        # Wave-Wind interference check
        if 'wave' in enabled_techs and 'wind' in enabled_techs:
            wave_capacity = requirements['wave']['capacity']
            wind_capacity = requirements['wind']['capacity']
            
            # Large wave installations might interfere with wind
            if wave_capacity > wind_capacity * 0.5:
                issues.append("High wave capacity may interfere with wind generation")
        
        # Solar-Wind shading check
        if 'solar' in enabled_techs and 'wind' in enabled_techs:
            solar_area = requirements['solar']['total_area']
            wind_area = requirements['wind']['total_area']
            
            # Check if solar panels might create wind shadows
            if solar_area > wind_area * 0.3:
                issues.append("Large solar installation may create wind shadows")
        
        # Total capacity check
        total_capacity = sum(req['capacity'] for req in requirements.values())
        max_capacity = self.config.optimization.get('constraints', {}).get('max_total_capacity', 500)
        
        if total_capacity > max_capacity:
            issues.append(f"Total capacity {total_capacity:.0f} MW exceeds limit {max_capacity:.0f} MW")
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of technology performance."""
        if not self.performance_data:
            return {"error": "No performance data available"}
        
        summary = {}
        
        for tech_name, performance in self.performance_data.items():
            summary[tech_name] = {
                'capacity_mw': performance.capacity,
                'capacity_factor': performance.capacity_factor,
                'annual_energy_mwh': performance.annual_energy,
                'availability': performance.availability,
                'space_requirement_m2': performance.space_requirement,
                'load_requirement_tonnes': performance.load_requirement
            }
        
        # Add combined metrics
        total_capacity = sum(p.capacity for p in self.performance_data.values())
        total_energy = sum(p.annual_energy for p in self.performance_data.values())
        
        summary['combined'] = {
            'total_capacity_mw': total_capacity,
            'total_annual_energy_mwh': total_energy,
            'combined_capacity_factor': total_energy / (total_capacity * 8760) if total_capacity > 0 else 0.0,
            'technology_count': len(self.performance_data)
        }
        
        return summary
