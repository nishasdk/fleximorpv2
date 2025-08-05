"""
Platform model for offshore renewable energy systems.

Handles platform design, structural analysis, and integration of multiple
renewable energy technologies on a single offshore platform.
"""

import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
import math

from ..config import SiteConfig


@dataclass
class PlatformSpecs:
    """Platform design specifications."""
    area: float  # m²
    water_depth: float  # meters
    distance_to_shore: float  # km
    platform_type: str = "semi_submersible"  # floating, fixed, semi_submersible
    max_load_capacity: float = 1000.0  # tonnes
    design_life: int = 25  # years


@dataclass
class PlatformPerformance:
    """Platform performance metrics."""
    structural_efficiency: float
    installation_complexity: float
    maintenance_accessibility: float
    environmental_impact: float
    total_footprint: float
    load_utilization: float


class PlatformModel:
    """
    Model for offshore renewable energy platform design and performance.
    
    Handles platform sizing, structural analysis, technology integration,
    and calculation of platform-level performance metrics.
    """
    
    def __init__(self, config: SiteConfig):
        """
        Initialize platform model.
        
        Args:
            config: Site configuration object
        """
        self.config = config
        self.platform_specs: Optional[PlatformSpecs] = None
        self.performance: Optional[PlatformPerformance] = None
        
        # Platform type parameters
        self.platform_types = {
            "fixed": {
                "max_depth": 50,  # meters
                "cost_factor": 1.0,
                "stability": 0.95,
                "maintenance_factor": 0.8
            },
            "floating": {
                "max_depth": 200,  # meters
                "cost_factor": 1.5,
                "stability": 0.85,
                "maintenance_factor": 0.6
            },
            "semi_submersible": {
                "max_depth": 150,  # meters
                "cost_factor": 1.3,
                "stability": 0.90,
                "maintenance_factor": 0.7
            }
        }
    
    def design_platform(self, 
                        design_vars: Dict[str, Any],
                        technology_requirements: Dict[str, Dict[str, float]]) -> PlatformSpecs:
        """
        Design platform based on technology requirements and site conditions.
        
        Args:
            design_vars: Design variables from optimization
            technology_requirements: Technology-specific space and load requirements
            
        Returns:
            PlatformSpecs object with platform design
        """
        # Extract design variables
        platform_area = design_vars.get('platform_area', 10000)  # m²
        water_depth = design_vars.get('water_depth', 50)  # meters
        distance_to_shore = design_vars.get('distance_to_shore', 20)  # km
        
        # Determine optimal platform type based on water depth
        platform_type = self._select_platform_type(water_depth)
        
        # Calculate required platform area based on technologies
        required_area = self._calculate_required_area(technology_requirements)
        
        # Ensure platform area meets requirements
        final_area = max(platform_area, required_area)
        
        # Calculate load capacity requirements
        required_load_capacity = self._calculate_load_requirements(technology_requirements)
        
        # Create platform specifications
        self.platform_specs = PlatformSpecs(
            area=final_area,
            water_depth=water_depth,
            distance_to_shore=distance_to_shore,
            platform_type=platform_type,
            max_load_capacity=required_load_capacity,
            design_life=self.config.economic.get('project_lifetime', 25)
        )
        
        return self.platform_specs
    
    def _select_platform_type(self, water_depth: float) -> str:
        """Select appropriate platform type based on water depth."""
        if water_depth <= 50:
            return "fixed"
        elif water_depth <= 100:
            return "semi_submersible"
        else:
            return "floating"
    
    def _calculate_required_area(self, technology_requirements: Dict[str, Dict[str, float]]) -> float:
        """Calculate minimum platform area required for technologies."""
        total_area = 0.0
        
        for tech_name, requirements in technology_requirements.items():
            tech_area = requirements.get('area_per_mw', 100) * requirements.get('capacity', 0)
            total_area += tech_area
        
        # Add 30% safety margin and common areas
        safety_factor = 1.3
        common_areas = 2000  # m² for control systems, maintenance, etc.
        
        return total_area * safety_factor + common_areas
    
    def _calculate_load_requirements(self, technology_requirements: Dict[str, Dict[str, float]]) -> float:
        """Calculate load capacity requirements for technologies."""
        total_load = 0.0
        
        for tech_name, requirements in technology_requirements.items():
            tech_load = requirements.get('load_per_mw', 50) * requirements.get('capacity', 0)
            total_load += tech_load
        
        # Add safety factor
        return total_load * 1.2
    
    def calculate_performance(self, design_vars: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate platform performance metrics.
        
        Args:
            design_vars: Platform design variables
            
        Returns:
            Dictionary with platform performance metrics
        """
        if self.platform_specs is None:
            raise ValueError("Platform must be designed before calculating performance")
        
        # Calculate individual performance metrics
        structural_efficiency = self._calculate_structural_efficiency()
        installation_complexity = self._calculate_installation_complexity()
        maintenance_accessibility = self._calculate_maintenance_accessibility()
        environmental_impact = self._calculate_environmental_impact()
        
        # Store performance
        self.performance = PlatformPerformance(
            structural_efficiency=structural_efficiency,
            installation_complexity=installation_complexity,
            maintenance_accessibility=maintenance_accessibility,
            environmental_impact=environmental_impact,
            total_footprint=self.platform_specs.area,
            load_utilization=0.8  # Placeholder
        )
        
        return {
            'platform_structural_efficiency': structural_efficiency,
            'platform_installation_complexity': installation_complexity,
            'platform_maintenance_accessibility': maintenance_accessibility,
            'platform_environmental_impact': environmental_impact,
            'platform_footprint': self.platform_specs.area,
            'platform_cost_factor': self._get_platform_cost_factor()
        }
    
    def _calculate_structural_efficiency(self) -> float:
        """Calculate structural efficiency metric (0-1)."""
        if self.platform_specs is None:
            raise ValueError("Platform must be designed before calculating structural efficiency")
        if self.platform_specs is None:
            raise ValueError("Platform must be designed before calculating structural efficiency")
        if self.platform_specs is None:
            raise ValueError("Platform must be designed before calculating structural efficiency")
        if self.platform_specs is None:
            raise ValueError("Platform must be designed before calculating structural efficiency")
        platform_type = self.platform_specs.platform_type
        base_efficiency = self.platform_types[platform_type]["stability"]
        
        # Adjust based on water depth (deeper = more challenging)
        depth_factor = 1.0 - (self.platform_specs.water_depth / 200) * 0.1
        
        # Adjust based on platform utilization
        utilization = min(1.0, self.platform_specs.max_load_capacity / 1000)
        utilization_factor = 0.8 + 0.2 * utilization
        
        return base_efficiency * depth_factor * utilization_factor
    
    def _calculate_installation_complexity(self) -> float:
        """Calculate installation complexity metric (0-1, lower is better)."""
        if self.platform_specs is None:
            raise ValueError("Platform must be designed before calculating installation complexity")
        platform_type = self.platform_specs.platform_type
        
        # Base complexity by platform type
        base_complexity = {
            "fixed": 0.3,
            "semi_submersible": 0.6,
            "floating": 0.8
        }[platform_type]
        
        # Adjust based on distance to shore
        distance_factor = min(1.0, self.platform_specs.distance_to_shore / 50)
        
        # Adjust based on water depth
        depth_factor = min(1.0, self.platform_specs.water_depth / 150)
        
        return base_complexity * (0.5 + 0.5 * distance_factor) * (0.7 + 0.3 * depth_factor)
    
    def _calculate_maintenance_accessibility(self) -> float:
        """Calculate maintenance accessibility metric (0-1, higher is better)."""
        if self.platform_specs is None:
            raise ValueError("Platform must be designed before calculating maintenance accessibility")
        platform_type = self.platform_specs.platform_type
        base_accessibility = self.platform_types[platform_type]["maintenance_factor"]
        
        # Adjust based on distance to shore (closer = more accessible)
        distance_factor = max(0.5, 1.0 - self.platform_specs.distance_to_shore / 100)
        
        # Adjust based on platform stability
        stability_factor = self.platform_types[platform_type]["stability"]
        
        return base_accessibility * distance_factor * stability_factor
    
    def _calculate_environmental_impact(self) -> float:
        """Calculate environmental impact metric (0-1, lower is better)."""
        if self.platform_specs is None:
            raise ValueError("Platform must be designed before calculating environmental impact")
        # Base impact by platform type
        base_impact = {
            "fixed": 0.7,  # Higher seafloor impact
            "semi_submersible": 0.4,
            "floating": 0.2  # Minimal seafloor impact
        }[self.platform_specs.platform_type]
        
        # Adjust based on platform size
        size_factor = min(1.0, self.platform_specs.area / 50000)
        
        # Adjust based on water depth (deeper generally less impact on seafloor)
        depth_factor = max(0.5, 1.0 - self.platform_specs.water_depth / 200)
        
        return base_impact * (0.6 + 0.4 * size_factor) * depth_factor
    
    def _get_platform_cost_factor(self) -> float:
        """Get platform cost multiplication factor."""
        platform_type = self.platform_specs.platform_type
        base_factor = self.platform_types[platform_type]["cost_factor"]
        
        # Adjust based on complexity factors
        if self.performance is not None:
            complexity_adjustment = 1.0 + self.performance.installation_complexity * 0.3
        else:
            complexity_adjustment = 1.0  # Default adjustment if performance is not set
        
        return base_factor * complexity_adjustment
    
    def calculate_foundation_costs(self) -> Dict[str, float]:
        """Calculate platform foundation and structural costs."""
        if self.platform_specs is None:
            raise ValueError("Platform must be designed before calculating costs")
        
        # Ensure performance metrics are calculated
        if self.performance is None:
            # Use current platform_specs to calculate performance
            self.calculate_performance({
                'platform_area': self.platform_specs.area,
                'water_depth': self.platform_specs.water_depth,
                'distance_to_shore': self.platform_specs.distance_to_shore
            })

        # Ensure self.performance is set after calculation
        if self.performance is None:
            raise ValueError("Platform performance could not be calculated.")

        # Base costs per m² by platform type (GBP)
        base_costs = {
            "fixed": 15000,  # GBP/m²
            "semi_submersible": 25000,
            "floating": 35000
        }
        
        base_cost_per_m2 = base_costs[self.platform_specs.platform_type]
        
        # Calculate structural costs
        structural_cost = self.platform_specs.area * base_cost_per_m2
        
        # Installation costs (function of complexity)
        installation_cost = structural_cost * 0.3 * (1.0 + self.performance.installation_complexity)
        
        # Mooring and anchoring (for floating platforms)
        if self.platform_specs.platform_type in ["floating", "semi_submersible"]:
            mooring_cost = structural_cost * 0.2
        else:
            mooring_cost = structural_cost * 0.1
        
        # Distance-dependent costs (transport, cables)
        distance_cost = self.platform_specs.distance_to_shore * 50000  # GBP/km
        
        return {
            'structural_cost': structural_cost,
            'installation_cost': installation_cost,
            'mooring_cost': mooring_cost,
            'distance_cost': distance_cost,
            'total_platform_cost': structural_cost + installation_cost + mooring_cost + distance_cost
        }
    
    def get_technology_integration_constraints(self) -> Dict[str, Dict[str, float]]:
        """Get constraints for technology integration on the platform."""
        if self.platform_specs is None:
            raise ValueError("Platform must be designed first")
        
        # Available space and load capacity for technologies
        total_area = self.platform_specs.area
        total_load_capacity = self.platform_specs.max_load_capacity
        
        # Reserve space for common areas
        available_area = total_area * 0.8  # 20% for common areas
        available_load = total_load_capacity * 0.9  # 10% safety margin
        
        return {
            'spatial_constraints': {
                'available_area': available_area,  # m²
                'max_technology_spacing': math.sqrt(available_area) * 0.1,  # minimum spacing
            },
            'structural_constraints': {
                'max_load_capacity': available_load,  # tonnes
                'max_point_load': available_load * 0.3,  # max load per technology
            },
            'operational_constraints': {
                'max_maintenance_downtime': 0.05,  # 5% of time
                'accessibility_requirement': self.performance.maintenance_accessibility if self.performance is not None else 0.0
            }
        }
    
    def validate_design(self, technology_requirements: Dict[str, Dict[str, float]]) -> Tuple[bool, List[str]]:
        """
        Validate platform design against technology requirements.
        
        Args:
            technology_requirements: Requirements from all technologies
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        if self.platform_specs is None:
            return False, ["Platform not designed"]
        
        issues = []
        
        # Check area requirements
        required_area = self._calculate_required_area(technology_requirements)
        if self.platform_specs.area < required_area:
            issues.append(f"Insufficient platform area: {self.platform_specs.area:.0f} < {required_area:.0f} m²")
        
        # Check load requirements
        required_load = self._calculate_load_requirements(technology_requirements)
        if self.platform_specs.max_load_capacity < required_load:
            issues.append(f"Insufficient load capacity: {self.platform_specs.max_load_capacity:.0f} < {required_load:.0f} tonnes")
        
        # Check platform type vs water depth
        if self.platform_specs is not None:
            platform_type = self.platform_specs.platform_type
            max_depth = self.platform_types[platform_type]["max_depth"]
            if self.platform_specs.water_depth > max_depth:
                issues.append(f"Water depth {self.platform_specs.water_depth:.0f}m exceeds limit for {platform_type} platform ({max_depth}m)")
        
        # Check minimum distances
        if self.platform_specs.distance_to_shore < 5:
            issues.append("Platform too close to shore (minimum 5km)")
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    def get_specifications_summary(self) -> Dict[str, Any]:
        """Get summary of platform specifications and performance."""
        if self.platform_specs is None:
            return {"error": "Platform not designed"}
        
        summary = {
            "platform_type": self.platform_specs.platform_type,
            "area_m2": self.platform_specs.area,
            "water_depth_m": self.platform_specs.water_depth,
            "distance_to_shore_km": self.platform_specs.distance_to_shore,
            "load_capacity_tonnes": self.platform_specs.max_load_capacity,
            "design_life_years": self.platform_specs.design_life
        }
        
        if self.performance is not None:
            summary.update({
                "structural_efficiency": self.performance.structural_efficiency,
                "installation_complexity": self.performance.installation_complexity,
                "maintenance_accessibility": self.performance.maintenance_accessibility,
                "environmental_impact": self.performance.environmental_impact
            })
        
        return summary
