"""
Sample environmental constraints for Alaska site
"""

constraints = {
    "marine_protected_areas": [
        {
            "name": "Pribilof Islands Marine Protected Area",
            "distance_km": 45,
            "protection_level": "high",
            "restrictions": ["seasonal_fishing_ban", "marine_mammal_protection"]
        }
    ],
    "fishing_grounds": {
        "primary_fisheries": ["pollock", "salmon", "crab"],
        "seasonal_restrictions": {
            "crab_season": {"start": "10-15", "end": "01-15"},
            "salmon_season": {"start": "05-01", "end": "09-30"}
        },
        "fishing_intensity": "high",
        "economic_value_usd": 15000000
    },
    "marine_mammals": {
        "species_present": ["bowhead_whale", "beluga_whale", "walrus", "seal"],
        "migration_periods": {
            "bowhead_whale": {"start": "04-01", "end": "06-30"},
            "beluga_whale": {"start": "05-15", "end": "09-15"}
        },
        "critical_habitat": false,
        "noise_sensitivity": "high"
    },
    "seabirds": {
        "species_present": ["puffin", "murre", "kittiwake", "cormorant"],
        "breeding_season": {"start": "05-01", "end": "08-31"},
        "flight_corridors": ["northeast_southwest"],
        "collision_risk": "medium"
    },
    "sea_ice": {
        "seasonal_presence": true,
        "ice_season": {"start": "11-01", "end": "04-30"},
        "max_thickness_m": 1.5,
        "impact_on_operations": "high"
    },
    "indigenous_use": {
        "subsistence_fishing": true,
        "subsistence_hunting": true,
        "cultural_sites": ["traditional_fishing_grounds"],
        "consultation_required": true
    }
}
