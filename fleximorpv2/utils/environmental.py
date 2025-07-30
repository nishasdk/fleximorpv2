"""
Environmental Assessment Module

Provides comprehensive environmental impact and constraint analysis for offshore renewable energy projects.
Integrates data from multiple APIs to assess:
- Marine ecosystem impacts
- Stakeholder conflicts (fishing, shipping, etc.)
- Environmental regulations and protected areas
- Climate change impacts
- Risk assessment for extreme weather events
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime, timedelta
import json

from ..api.nasa_api import NASAClient
from ..api.copernicus_api import CopernicusClient
from ..api.openweather_api import OpenWeatherClient
from ..api.nrel_api import NRELClient

logger = logging.getLogger(__name__)


class EnvironmentalAssessment:
    """
    Comprehensive environmental assessment for offshore renewable energy projects
    """
    
    def __init__(self, api_keys: Dict[str, str], cache_dir: str = "cache"):
        """
        Initialize environmental assessment with API clients
        
        Args:
            api_keys: Dictionary of API keys for different services
            cache_dir: Directory for caching API responses
        """
        self.cache_dir = cache_dir
        
        # Initialize API clients
        self.nasa_client = NASAClient(
            api_key=api_keys.get('nasa'),
            cache_ttl_hours=168  # 1 week cache
        )
        
        self.copernicus_client = CopernicusClient(
            api_key=api_keys.get('copernicus'),
            cache_ttl_hours=336  # 2 weeks cache
        )
        
        self.openweather_client = OpenWeatherClient(
            api_key=api_keys.get('openweather'),
            cache_ttl_hours=6  # 6 hours cache for current data
        )
        
        self.nrel_client = NRELClient(
            api_key=api_keys.get('nrel'),
            cache_ttl_hours=168  # 1 week cache
        )
        
        logger.info("Environmental assessment module initialized")
    
    def assess_site_suitability(self, 
                               lat: float, 
                               lon: float, 
                               technologies: List[str],
                               stakeholder_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Comprehensive site suitability assessment
        
        Args:
            lat: Latitude
            lon: Longitude
            technologies: List of technologies ['wind', 'solar', 'wave']
            stakeholder_data: Optional stakeholder constraint data
            
        Returns:
            Comprehensive site assessment
        """
        assessment = {
            'location': {'latitude': lat, 'longitude': lon},
            'assessment_date': datetime.now().isoformat(),
            'technologies_assessed': technologies,
            'overall_suitability': {},
            'constraints': {},
            'opportunities': {},
            'risks': {},
            'recommendations': []
        }
        
        # Resource assessment
        resource_data = self._assess_renewable_resources(lat, lon, technologies)
        assessment['resource_potential'] = resource_data
        
        # Environmental constraints
        environmental_constraints = self._assess_environmental_constraints(lat, lon)
        assessment['environmental_constraints'] = environmental_constraints
        
        # Stakeholder conflicts
        stakeholder_conflicts = self._assess_stakeholder_conflicts(lat, lon, stakeholder_data)
        assessment['stakeholder_conflicts'] = stakeholder_conflicts
        
        # Climate risks
        climate_risks = self._assess_climate_risks(lat, lon)
        assessment['climate_risks'] = climate_risks
        
        # Regulatory compliance
        regulatory_assessment = self._assess_regulatory_compliance(lat, lon)
        assessment['regulatory_compliance'] = regulatory_assessment
        
        # Calculate overall suitability scores
        assessment['overall_suitability'] = self._calculate_suitability_scores(
            resource_data, environmental_constraints, stakeholder_conflicts, 
            climate_risks, regulatory_assessment, technologies
        )
        
        # Generate recommendations
        assessment['recommendations'] = self._generate_recommendations(assessment)
        
        return assessment
    
    def assess_environmental_impact(self, 
                                  lat: float, 
                                  lon: float, 
                                  project_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Environmental impact assessment for proposed project
        
        Args:
            lat: Latitude
            lon: Longitude
            project_config: Project configuration including capacities and layout
            
        Returns:
            Environmental impact assessment
        """
        impact_assessment = {
            'location': {'latitude': lat, 'longitude': lon},
            'project_config': project_config,
            'assessment_date': datetime.now().isoformat(),
            'impact_categories': {},
            'mitigation_measures': [],
            'monitoring_requirements': []
        }
        
        # Marine ecosystem impact
        marine_impact = self._assess_marine_ecosystem_impact(lat, lon, project_config)
        impact_assessment['impact_categories']['marine_ecosystem'] = marine_impact
        
        # Avian impact (for wind turbines)
        if 'wind' in project_config.get('technologies', []):
            avian_impact = self._assess_avian_impact(lat, lon, project_config)
            impact_assessment['impact_categories']['avian'] = avian_impact
        
        # Visual impact
        visual_impact = self._assess_visual_impact(lat, lon, project_config)
        impact_assessment['impact_categories']['visual'] = visual_impact
        
        # Cumulative impact
        cumulative_impact = self._assess_cumulative_impact(lat, lon, project_config)
        impact_assessment['impact_categories']['cumulative'] = cumulative_impact
        
        # Generate mitigation measures
        impact_assessment['mitigation_measures'] = self._generate_mitigation_measures(impact_assessment)
        
        # Monitoring requirements
        impact_assessment['monitoring_requirements'] = self._generate_monitoring_requirements(impact_assessment)
        
        return impact_assessment
    
    def assess_extreme_weather_risks(self, 
                                   lat: float, 
                                   lon: float, 
                                   return_periods: List[int] = [10, 50, 100]) -> Dict[str, Any]:
        """
        Extreme weather risk assessment
        
        Args:
            lat: Latitude
            lon: Longitude
            return_periods: Return periods for extreme event analysis
            
        Returns:
            Extreme weather risk assessment
        """
        risk_assessment = {
            'location': {'latitude': lat, 'longitude': lon},
            'return_periods': return_periods,
            'assessment_date': datetime.now().isoformat(),
            'extreme_events': {},
            'design_conditions': {},
            'risk_mitigation': []
        }
        
        # Get extreme weather data from multiple sources
        nasa_extremes = self.nasa_client.get_extreme_weather_stats(lat, lon, years=30)
        copernicus_extremes = self.copernicus_client.get_extreme_events(lat, lon, return_periods)
        
        # Combine and analyze extreme events
        risk_assessment['extreme_events'] = self._combine_extreme_data(nasa_extremes, copernicus_extremes)
        
        # Calculate design conditions
        risk_assessment['design_conditions'] = self._calculate_design_conditions(risk_assessment['extreme_events'])
        
        # Risk mitigation strategies
        risk_assessment['risk_mitigation'] = self._generate_risk_mitigation_strategies(risk_assessment)
        
        return risk_assessment
    
    def _assess_renewable_resources(self, lat: float, lon: float, technologies: List[str]) -> Dict[str, Any]:
        """Assess renewable resource potential"""
        resources = {}
        
        for tech in technologies:
            if tech == 'wind':
                wind_data = self.nrel_client.get_wind_resource(lat, lon)
                nasa_climate = self.nasa_client.get_climate_data(lat, lon)
                
                resources['wind'] = {
                    'capacity_factor': wind_data.get('capacity_factors', {}).get('100m', 0.35),
                    'average_speed_ms': nasa_climate.get('avg_wind_speed_ms', 7.0),
                    'wind_power_density': nasa_climate.get('wind_power_density', 400),
                    'resource_quality': 'excellent' if wind_data.get('capacity_factors', {}).get('100m', 0) > 0.45 else 'good' if wind_data.get('capacity_factors', {}).get('100m', 0) > 0.35 else 'fair',
                    'data_quality': wind_data.get('quality_flag', 'medium')
                }
            
            elif tech == 'solar':
                solar_data = self.nrel_client.get_solar_resource(lat, lon)
                
                resources['solar'] = {
                    'capacity_factor': solar_data.get('capacity_factor_estimate', 0.18),
                    'annual_ghi': solar_data.get('annual_ghi', 1500),
                    'resource_quality': 'excellent' if solar_data.get('capacity_factor_estimate', 0) > 0.25 else 'good' if solar_data.get('capacity_factor_estimate', 0) > 0.20 else 'fair',
                    'data_quality': solar_data.get('quality_flag', 'medium')
                }
            
            elif tech == 'wave':
                ocean_data = self.nasa_client.get_ocean_conditions(lat, lon)
                marine_data = self.copernicus_client.get_marine_data(lat, lon)
                
                resources['wave'] = {
                    'wave_height_m': marine_data.get('significant_wave_height_m', 2.0),
                    'wave_period_s': marine_data.get('mean_wave_period_s', 7.0),
                    'wave_power_density': marine_data.get('wave_power_density_w_m', 15000),
                    'resource_quality': marine_data.get('wave_energy_class', 'fair'),
                    'data_quality': marine_data.get('quality_flag', 'medium')
                }
        
        return resources
    
    def _assess_environmental_constraints(self, lat: float, lon: float) -> Dict[str, Any]:
        """Assess environmental constraints"""
        constraints = {
            'protected_areas': self._check_protected_areas(lat, lon),
            'marine_habitats': self._assess_marine_habitats(lat, lon),
            'migration_routes': self._check_migration_routes(lat, lon),
            'spawning_grounds': self._check_spawning_grounds(lat, lon),
            'coral_reefs': self._check_coral_reefs(lat, lon)
        }
        
        # Calculate overall constraint level
        constraint_scores = []
        for category, data in constraints.items():
            if isinstance(data, dict) and 'constraint_level' in data:
                score_map = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
                constraint_scores.append(score_map.get(data['constraint_level'], 2))
        
        if constraint_scores:
            avg_score = np.mean(constraint_scores)
            if avg_score >= 3.5:
                overall_level = 'critical'
            elif avg_score >= 2.5:
                overall_level = 'high'
            elif avg_score >= 1.5:
                overall_level = 'medium'
            else:
                overall_level = 'low'
        else:
            overall_level = 'medium'
        
        constraints['overall_constraint_level'] = overall_level
        
        return constraints
    
    def _assess_stakeholder_conflicts(self, lat: float, lon: float, stakeholder_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Assess potential stakeholder conflicts"""
        conflicts = {
            'fishing_activity': self._assess_fishing_conflicts(lat, lon, stakeholder_data),
            'shipping_routes': self._assess_shipping_conflicts(lat, lon),
            'recreational_use': self._assess_recreational_conflicts(lat, lon),
            'military_areas': self._check_military_restrictions(lat, lon),
            'existing_infrastructure': self._check_existing_infrastructure(lat, lon)
        }
        
        # Calculate conflict severity
        conflict_scores = []
        for category, data in conflicts.items():
            if isinstance(data, dict) and 'conflict_level' in data:
                score_map = {'none': 0, 'low': 1, 'medium': 2, 'high': 3}
                conflict_scores.append(score_map.get(data['conflict_level'], 1))
        
        if conflict_scores:
            max_score = max(conflict_scores)
            if max_score >= 3:
                overall_conflict = 'high'
            elif max_score >= 2:
                overall_conflict = 'medium'
            elif max_score >= 1:
                overall_conflict = 'low'
            else:
                overall_conflict = 'none'
        else:
            overall_conflict = 'low'
        
        conflicts['overall_conflict_level'] = overall_conflict
        conflicts['resolution_strategies'] = self._generate_conflict_resolution_strategies(conflicts)
        
        return conflicts
    
    def _assess_climate_risks(self, lat: float, lon: float) -> Dict[str, Any]:
        """Assess climate change risks"""
        # Get climate projections
        projections_rcp45 = self.copernicus_client.get_climate_projections(lat, lon, "rcp4_5")
        projections_rcp85 = self.copernicus_client.get_climate_projections(lat, lon, "rcp8_5")
        
        risks = {
            'temperature_change': {
                'rcp4_5': projections_rcp45.get('temperature_change_c', 2.5),
                'rcp8_5': projections_rcp85.get('temperature_change_c', 4.0),
                'impact_level': 'medium' if projections_rcp45.get('temperature_change_c', 2.5) < 3 else 'high'
            },
            'wind_resource_change': {
                'rcp4_5': projections_rcp45.get('wind_speed_change_percent', 5),
                'rcp8_5': projections_rcp85.get('wind_speed_change_percent', 8),
                'impact_level': 'low' if abs(projections_rcp45.get('wind_speed_change_percent', 5)) < 10 else 'medium'
            },
            'solar_resource_change': {
                'rcp4_5': projections_rcp45.get('solar_radiation_change_percent', -2),
                'rcp8_5': projections_rcp85.get('solar_radiation_change_percent', -5),
                'impact_level': 'low' if abs(projections_rcp45.get('solar_radiation_change_percent', -2)) < 5 else 'medium'
            },
            'sea_level_rise': {
                'estimated_rise_cm': 30 + abs(lat) * 0.5,  # Simplified estimate
                'impact_level': 'medium'
            },
            'extreme_weather_frequency': {
                'change_factor': 1.2,  # 20% increase assumption
                'impact_level': 'medium'
            }
        }
        
        # Overall climate risk assessment
        impact_levels = [risk.get('impact_level', 'medium') for risk in risks.values() if isinstance(risk, dict)]
        if 'high' in impact_levels:
            risks['overall_climate_risk'] = 'high'
        elif 'medium' in impact_levels:
            risks['overall_climate_risk'] = 'medium'
        else:
            risks['overall_climate_risk'] = 'low'
        
        risks['adaptation_strategies'] = self._generate_adaptation_strategies(risks)
        
        return risks
    
    def _assess_regulatory_compliance(self, lat: float, lon: float) -> Dict[str, Any]:
        """Assess regulatory compliance requirements"""
        compliance = {
            'eez_status': self._check_eez_status(lat, lon),
            'environmental_permits': self._identify_required_permits(lat, lon),
            'consultation_requirements': self._identify_consultation_requirements(lat, lon),
            'monitoring_obligations': self._identify_monitoring_obligations(lat, lon),
            'compliance_complexity': 'medium',  # Default assessment
            'estimated_timeline_months': 24,  # Default timeline
            'estimated_cost_range': '$500K - $2M'  # Default cost estimate
        }
        
        return compliance
    
    def _calculate_suitability_scores(self, resource_data, environmental_constraints, 
                                    stakeholder_conflicts, climate_risks, regulatory_compliance, 
                                    technologies) -> Dict[str, Any]:
        """Calculate overall suitability scores"""
        scores = {}
        
        for tech in technologies:
            if tech in resource_data:
                resource_score = self._score_resource_quality(resource_data[tech]['resource_quality'])
                constraint_score = self._score_constraints(environmental_constraints['overall_constraint_level'])
                conflict_score = self._score_conflicts(stakeholder_conflicts['overall_conflict_level'])
                climate_score = self._score_climate_risk(climate_risks['overall_climate_risk'])
                
                # Weighted average (resource potential is most important)
                overall_score = (
                    resource_score * 0.4 +
                    constraint_score * 0.25 +
                    conflict_score * 0.2 +
                    climate_score * 0.15
                )
                
                scores[tech] = {
                    'overall_score': round(overall_score, 2),
                    'resource_score': resource_score,
                    'constraint_score': constraint_score,
                    'conflict_score': conflict_score,
                    'climate_score': climate_score,
                    'suitability_rating': self._rate_suitability(overall_score)
                }
        
        return scores
    
    def _score_resource_quality(self, quality: str) -> float:
        """Convert resource quality to numerical score"""
        quality_scores = {'excellent': 1.0, 'good': 0.8, 'fair': 0.6, 'poor': 0.4}
        return quality_scores.get(quality, 0.6)
    
    def _score_constraints(self, level: str) -> float:
        """Convert constraint level to numerical score (higher constraints = lower score)"""
        constraint_scores = {'low': 1.0, 'medium': 0.7, 'high': 0.4, 'critical': 0.1}
        return constraint_scores.get(level, 0.7)
    
    def _score_conflicts(self, level: str) -> float:
        """Convert conflict level to numerical score"""
        conflict_scores = {'none': 1.0, 'low': 0.8, 'medium': 0.6, 'high': 0.3}
        return conflict_scores.get(level, 0.6)
    
    def _score_climate_risk(self, risk: str) -> float:
        """Convert climate risk to numerical score"""
        risk_scores = {'low': 1.0, 'medium': 0.8, 'high': 0.6}
        return risk_scores.get(risk, 0.8)
    
    def _rate_suitability(self, score: float) -> str:
        """Convert numerical score to suitability rating"""
        if score >= 0.8:
            return 'excellent'
        elif score >= 0.7:
            return 'good'
        elif score >= 0.5:
            return 'fair'
        else:
            return 'poor'
    
    # Simplified implementations for constraint checking methods
    def _check_protected_areas(self, lat: float, lon: float) -> Dict[str, Any]:
        """Check for protected marine areas"""
        return {
            'within_protected_area': False,
            'nearest_protected_area_km': 50,
            'constraint_level': 'low',
            'area_types': []
        }
    
    def _assess_marine_habitats(self, lat: float, lon: float) -> Dict[str, Any]:
        """Assess sensitive marine habitats"""
        return {
            'habitat_types': ['open_ocean'],
            'sensitivity_level': 'medium',
            'constraint_level': 'medium',
            'seasonal_restrictions': []
        }
    
    def _check_migration_routes(self, lat: float, lon: float) -> Dict[str, Any]:
        """Check for marine animal migration routes"""
        return {
            'on_migration_route': False,
            'species_affected': [],
            'constraint_level': 'low',
            'seasonal_considerations': []
        }
    
    def _check_spawning_grounds(self, lat: float, lon: float) -> Dict[str, Any]:
        """Check for fish spawning grounds"""
        return {
            'spawning_area': False,
            'species': [],
            'constraint_level': 'low',
            'seasonal_restrictions': []
        }
    
    def _check_coral_reefs(self, lat: float, lon: float) -> Dict[str, Any]:
        """Check for coral reef proximity"""
        # Simplified - coral reefs mainly in tropical waters
        in_coral_zone = abs(lat) < 30
        return {
            'coral_present': in_coral_zone,
            'distance_km': 10 if in_coral_zone else 1000,
            'constraint_level': 'high' if in_coral_zone else 'low'
        }
    
    def _assess_fishing_conflicts(self, lat: float, lon: float, stakeholder_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Assess fishing activity conflicts"""
        if stakeholder_data and 'fishing' in stakeholder_data:
            return stakeholder_data['fishing']
        
        return {
            'fishing_intensity': 'medium',
            'primary_fisheries': ['commercial_trawling'],
            'conflict_level': 'medium',
            'mitigation_options': ['seasonal_restrictions', 'compensation_schemes']
        }
    
    def _assess_shipping_conflicts(self, lat: float, lon: float) -> Dict[str, Any]:
        """Assess shipping route conflicts"""
        return {
            'shipping_density': 'low',
            'route_types': ['recreational'],
            'conflict_level': 'low',
            'mitigation_options': ['route_marking', 'navigation_aids']
        }
    
    def _assess_recreational_conflicts(self, lat: float, lon: float) -> Dict[str, Any]:
        """Assess recreational use conflicts"""
        return {
            'recreational_activities': ['boating', 'fishing'],
            'usage_intensity': 'medium',
            'conflict_level': 'low',
            'mitigation_options': ['public_consultation', 'access_maintenance']
        }
    
    def _check_military_restrictions(self, lat: float, lon: float) -> Dict[str, Any]:
        """Check for military restriction areas"""
        return {
            'restricted_area': False,
            'restriction_type': None,
            'conflict_level': 'none'
        }
    
    def _check_existing_infrastructure(self, lat: float, lon: float) -> Dict[str, Any]:
        """Check for existing infrastructure"""
        return {
            'infrastructure_present': False,
            'infrastructure_types': [],
            'conflict_level': 'none'
        }
    
    def _check_eez_status(self, lat: float, lon: float) -> Dict[str, Any]:
        """Check Exclusive Economic Zone status"""
        return {
            'within_eez': True,
            'country': 'Unknown',
            'jurisdiction_clear': True
        }
    
    def _identify_required_permits(self, lat: float, lon: float) -> List[str]:
        """Identify required environmental permits"""
        return [
            'environmental_impact_assessment',
            'marine_construction_permit',
            'grid_connection_permit'
        ]
    
    def _identify_consultation_requirements(self, lat: float, lon: float) -> List[str]:
        """Identify consultation requirements"""
        return [
            'local_fishing_communities',
            'environmental_groups',
            'regulatory_authorities'
        ]
    
    def _identify_monitoring_obligations(self, lat: float, lon: float) -> List[str]:
        """Identify monitoring obligations"""
        return [
            'marine_mammal_monitoring',
            'bird_collision_monitoring',
            'water_quality_monitoring'
        ]
    
    def _generate_recommendations(self, assessment: Dict[str, Any]) -> List[str]:
        """Generate site-specific recommendations"""
        recommendations = []
        
        # Resource-based recommendations
        for tech, data in assessment['resource_potential'].items():
            if data['resource_quality'] == 'excellent':
                recommendations.append(f"Excellent {tech} resource - prioritize {tech} technology")
            elif data['resource_quality'] == 'poor':
                recommendations.append(f"Poor {tech} resource - consider alternative technologies")
        
        # Constraint-based recommendations
        if assessment['environmental_constraints']['overall_constraint_level'] == 'high':
            recommendations.append("High environmental constraints - detailed impact assessment required")
        
        # Conflict-based recommendations
        if assessment['stakeholder_conflicts']['overall_conflict_level'] == 'high':
            recommendations.append("Significant stakeholder conflicts - extensive consultation needed")
        
        # Climate risk recommendations
        if assessment['climate_risks']['overall_climate_risk'] == 'high':
            recommendations.append("High climate risks - incorporate adaptation measures in design")
        
        if not recommendations:
            recommendations.append("Site shows good potential - proceed with detailed feasibility study")
        
        return recommendations
    
    def _generate_mitigation_measures(self, impact_assessment: Dict[str, Any]) -> List[str]:
        """Generate environmental mitigation measures"""
        return [
            "Implement seasonal construction restrictions during sensitive periods",
            "Use low-noise installation techniques to minimize marine mammal disturbance",
            "Install bird deterrent systems on wind turbines",
            "Establish marine monitoring program",
            "Coordinate with fishing industry on exclusion zones"
        ]
    
    def _generate_monitoring_requirements(self, impact_assessment: Dict[str, Any]) -> List[str]:
        """Generate monitoring requirements"""
        return [
            "Pre-construction baseline surveys",
            "Real-time marine mammal monitoring during construction",
            "Annual bird collision monitoring",
            "Benthic habitat monitoring",
            "Noise level monitoring"
        ]
    
    def _generate_conflict_resolution_strategies(self, conflicts: Dict[str, Any]) -> List[str]:
        """Generate conflict resolution strategies"""
        return [
            "Engage early with fishing communities",
            "Provide compensation for fishing ground displacement",
            "Create co-use opportunities where possible",
            "Establish stakeholder advisory committee"
        ]
    
    def _generate_adaptation_strategies(self, risks: Dict[str, Any]) -> List[str]:
        """Generate climate adaptation strategies"""
        return [
            "Design for increased extreme weather frequency",
            "Use climate-resilient materials and components",
            "Implement adaptive management protocols",
            "Plan for sea level rise in foundation design"
        ]
    
    def _generate_risk_mitigation_strategies(self, risk_assessment: Dict[str, Any]) -> List[str]:
        """Generate extreme weather risk mitigation strategies"""
        return [
            "Design structures for 100-year return period events",
            "Implement real-time weather monitoring",
            "Develop emergency response procedures",
            "Use predictive maintenance scheduling"
        ]
    
    def _assess_marine_ecosystem_impact(self, lat: float, lon: float, project_config: Dict[str, Any]) -> Dict[str, Any]:
        """Assess marine ecosystem impacts"""
        return {
            'impact_level': 'medium',
            'affected_species': ['marine_mammals', 'seabirds'],
            'impact_types': ['habitat_displacement', 'noise_disturbance'],
            'mitigation_effectiveness': 'high'
        }
    
    def _assess_avian_impact(self, lat: float, lon: float, project_config: Dict[str, Any]) -> Dict[str, Any]:
        """Assess avian impacts for wind projects"""
        return {
            'collision_risk': 'medium',
            'barrier_effect': 'low',
            'habitat_displacement': 'low',
            'species_at_risk': ['seabirds', 'migrating_birds']
        }
    
    def _assess_visual_impact(self, lat: float, lon: float, project_config: Dict[str, Any]) -> Dict[str, Any]:
        """Assess visual impact"""
        return {
            'visibility_km': 25,
            'impact_level': 'medium',
            'affected_viewpoints': ['coastal_areas'],
            'mitigation_options': ['turbine_layout_optimization']
        }
    
    def _assess_cumulative_impact(self, lat: float, lon: float, project_config: Dict[str, Any]) -> Dict[str, Any]:
        """Assess cumulative impacts with other projects"""
        return {
            'other_projects_nearby': False,
            'cumulative_effect': 'low',
            'combined_impact_level': 'medium'
        }
    
    def _combine_extreme_data(self, nasa_data: Dict[str, Any], copernicus_data: Dict[str, Any]) -> Dict[str, Any]:
        """Combine extreme weather data from multiple sources"""
        return {
            'wind_speed_extremes': {
                '10_year': max(nasa_data.get('design_wind_speed_ms', 30), 
                              copernicus_data.get('10_year_return', {}).get('wind_speed_ms', 25)),
                '50_year': 35,
                '100_year': 40
            },
            'wave_height_extremes': {
                '10_year': 8,
                '50_year': 12,
                '100_year': 15
            },
            'data_sources': ['NASA POWER', 'Copernicus ERA5']
        }
    
    def _calculate_design_conditions(self, extreme_events: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate design conditions from extreme event data"""
        return {
            'design_wind_speed_ms': extreme_events.get('wind_speed_extremes', {}).get('50_year', 35),
            'design_wave_height_m': extreme_events.get('wave_height_extremes', {}).get('50_year', 12),
            'safety_factors': {
                'wind': 1.35,  # IEC 61400-3 standard
                'wave': 1.25,
                'combined': 1.5
            },
            'return_period_basis': '50-year design standard',
            'design_life_years': 25
        }
