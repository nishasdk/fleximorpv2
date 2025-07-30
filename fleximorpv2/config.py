"""
Configuration management for FlexiMORPv2.

Handles loading and validation of site-specific configuration files,
API connections, and parameter management across all analysis modules.
"""

import yaml
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import requests
from pathlib import Path


@dataclass
class TechnologyConfig:
    """Configuration for a specific technology (wind, solar, wave)."""
    enabled: bool
    api_endpoint: Optional[str] = None
    cost_per_mw: float = 0.0
    capacity_factor: float = 0.0
    technical_params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.technical_params is None:
            self.technical_params = {}


@dataclass 
class SiteConfig:
    """Complete configuration for a site analysis."""
    name: str
    coordinates: List[float]
    technologies: Dict[str, TechnologyConfig]
    optimization: Dict[str, Any]
    uncertainty: Dict[str, Any]
    flexibility: Dict[str, Any]
    economic: Dict[str, Any]
    
    def get_enabled_technologies(self) -> List[str]:
        """Return list of enabled technology names."""
        return [name for name, config in self.technologies.items() if config.enabled]
    
    def get_api_endpoints(self) -> Dict[str, str]:
        """Return mapping of technology names to API endpoints."""
        return {
            name: config.api_endpoint 
            for name, config in self.technologies.items() 
            if config.enabled and config.api_endpoint
        }


def load_config(site_name: str, config_dir: str = None) -> SiteConfig:
    """
    Load configuration for a specific site.
    
    Args:
        site_name: Name of the site (e.g., 'blyth', 'alaska', 'eastport')
        config_dir: Optional path to config directory. Defaults to data/{site_name}/
        
    Returns:
        SiteConfig object with validated configuration
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If configuration is invalid
    """
    if config_dir is None:
        # Default to data/{site_name}/ relative to package root
        package_root = Path(__file__).parent.parent
        config_dir = package_root / "data" / site_name
    
    config_path = Path(config_dir) / "config.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        raw_config = yaml.safe_load(f)
    
    # Validate and parse configuration
    return _parse_config(raw_config)


def _parse_config(raw_config: Dict[str, Any]) -> SiteConfig:
    """Parse raw YAML configuration into SiteConfig object."""
    
    # Parse technologies
    technologies = {}
    for tech_name, tech_data in raw_config.get('technologies', {}).items():
        technologies[tech_name] = TechnologyConfig(
            enabled=tech_data.get('enabled', False),
            api_endpoint=tech_data.get('api_endpoint'),
            cost_per_mw=tech_data.get('cost_per_mw', 0.0),
            capacity_factor=tech_data.get('capacity_factor', 0.0),
            technical_params=tech_data.get('technical_params', {})
        )
    
    return SiteConfig(
        name=raw_config['site']['name'],
        coordinates=raw_config['site']['coordinates'],
        technologies=technologies,
        optimization=raw_config.get('optimization', {}),
        uncertainty=raw_config.get('uncertainty', {}),
        flexibility=raw_config.get('flexibility', {}),
        economic=raw_config.get('economic', {})
    )


def validate_config(config: SiteConfig) -> bool:
    """
    Validate configuration parameters.
    
    Args:
        config: SiteConfig object to validate
        
    Returns:
        True if valid, raises ValueError if invalid
    """
    # Check basic site info
    if not config.name:
        raise ValueError("Site name is required")
    
    if len(config.coordinates) != 2:
        raise ValueError("Coordinates must be [latitude, longitude]")
    
    # Check at least one technology is enabled
    enabled_techs = config.get_enabled_technologies()
    if not enabled_techs:
        raise ValueError("At least one technology must be enabled")
    
    # Validate technology configurations
    for tech_name, tech_config in config.technologies.items():
        if tech_config.enabled:
            if tech_config.cost_per_mw <= 0:
                raise ValueError(f"Technology {tech_name} must have positive cost_per_mw")
    
    return True


def test_api_connections(config: SiteConfig) -> Dict[str, bool]:
    """
    Test API connections for enabled technologies.
    
    Args:
        config: SiteConfig object
        
    Returns:
        Dictionary mapping technology names to connection status
    """
    results = {}
    
    for tech_name, tech_config in config.technologies.items():
        if tech_config.enabled and tech_config.api_endpoint:
            try:
                response = requests.head(tech_config.api_endpoint, timeout=5)
                results[tech_name] = response.status_code == 200
            except requests.RequestException:
                results[tech_name] = False
        else:
            results[tech_name] = None  # No API endpoint configured
    
    return results


def create_default_config(site_name: str, coordinates: List[float]) -> Dict[str, Any]:
    """
    Create a default configuration template for a new site.
    
    Args:
        site_name: Name of the new site
        coordinates: [latitude, longitude]
        
    Returns:
        Dictionary with default configuration structure
    """
    return {
        'site': {
            'name': site_name,
            'coordinates': coordinates
        },
        'technologies': {
            'wind': {
                'enabled': True,
                'api_endpoint': None,
                'cost_per_mw': 1500000,
                'capacity_factor': 0.45,
                'technical_params': {
                    'turbine_rating': 8.0,  # MW
                    'hub_height': 100,      # meters
                    'rotor_diameter': 164   # meters
                }
            },
            'solar': {
                'enabled': True,
                'api_endpoint': None,
                'cost_per_mw': 1200000,
                'capacity_factor': 0.22,
                'technical_params': {
                    'panel_efficiency': 0.20,
                    'degradation_rate': 0.005
                }
            },
            'wave': {
                'enabled': False,
                'api_endpoint': None,
                'cost_per_mw': 2500000,
                'capacity_factor': 0.35,
                'technical_params': {
                    'device_rating': 1.0,
                    'availability': 0.90
                }
            }
        },
        'optimization': {
            'objective': 'minimize_lcoe',
            'constraints': {
                'max_investment': 100000000,  # £100M
                'min_capacity_factor': 0.30,
                'max_total_capacity': 500     # MW
            }
        },
        'uncertainty': {
            'monte_carlo_runs': 10000,
            'variables': {
                'weather': 'stochastic',
                'electricity_price': 'scenario_based',
                'capex': 'normal_distribution',
                'opex': 'normal_distribution'
            }
        },
        'flexibility': {
            'decision_points': [2, 5, 10],        # years
            'expansion_options': [25, 50, 100],   # MW increments
            'abandonment_option': True,
            'technology_switching': True
        },
        'economic': {
            'discount_rate': 0.08,
            'project_lifetime': 25,  # years
            'electricity_price': 0.10,  # £/kWh
            'inflation_rate': 0.02,
            'tax_rate': 0.25
        }
    }
