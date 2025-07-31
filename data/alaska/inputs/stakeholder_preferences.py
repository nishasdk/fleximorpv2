"""
Stakeholder preferences for Alaska community-focused project
"""

stakeholder_preferences = {
    "community_priorities": {
        "energy_independence": 0.9,  # Very high priority
        "cost_reduction": 0.8,       # High priority
        "job_creation": 0.7,         # High priority
        "environmental_protection": 0.8,  # High priority
        "cultural_preservation": 0.9     # Very high priority
    },
    "fishing_community": {
        "fishing_ground_access": {
            "priority": 0.9,
            "acceptable_exclusion_zones": 2.0,  # km radius
            "compensation_expected": true,
            "seasonal_flexibility": true
        },
        "navigation_concerns": {
            "shipping_lanes": ["traditional_route_1", "traditional_route_2"],
            "safety_requirements": ["navigation_lights", "radar_reflectors"],
            "weather_monitoring": true
        }
    },
    "indigenous_groups": {
        "consultation_requirements": {
            "formal_consultation": true,
            "ongoing_engagement": true,
            "benefit_sharing": true
        },
        "cultural_considerations": {
            "subsistence_activities": {
                "fishing": {"months": [5, 6, 7, 8, 9], "importance": 0.9},
                "hunting": {"months": [4, 5, 9, 10], "importance": 0.8},
                "gathering": {"months": [6, 7, 8], "importance": 0.6}
            },
            "sacred_sites": {
                "buffer_zones_required": true,
                "minimum_distance_km": 5
            }
        }
    },
    "local_government": {
        "economic_development": {
            "local_employment_target": 0.6,  # 60% local hiring
            "local_procurement_target": 0.4,  # 40% local purchasing
            "training_programs_required": true
        },
        "infrastructure_benefits": {
            "grid_connection_priority": 0.9,
            "backup_power_capability": 0.8,
            "telecommunications_infrastructure": 0.6
        }
    },
    "environmental_groups": {
        "marine_protection": {
            "mammal_protection_measures": 0.9,
            "bird_protection_measures": 0.8,
            "habitat_restoration": 0.7
        },
        "monitoring_requirements": {
            "continuous_environmental_monitoring": 0.9,
            "third_party_verification": 0.8,
            "public_reporting": 0.7
        }
    },
    "project_constraints": {
        "acceptable_technologies": ["wind", "solar"],  # No wave energy due to ice
        "maximum_project_size_mw": 50,
        "preferred_distance_from_shore_km": {"min": 3, "max": 15},
        "construction_season": {"start": "05-01", "end": "10-31"},
        "maintenance_accessibility": "high_priority"
    },
    "success_metrics": {
        "community_acceptance": 0.9,
        "environmental_compliance": 0.9,
        "economic_viability": 0.8,
        "energy_security": 0.9,
        "cultural_compatibility": 0.9
    }
}
