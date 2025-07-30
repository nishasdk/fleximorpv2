"""
Interactive Configuration Builder for FlexiMORP v2

Guides users through design variable selection and generates appropriate
configuration files for adaptive optimization.
"""

import yaml
import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ConfigurationBuilder:
    """
    Interactive configuration builder for FlexiMORP v2
    """
    
    def __init__(self):
        """Initialize configuration builder"""
        self.config = {}
        self.site_templates = self._load_site_templates()
        
        logger.info("Initialized Configuration Builder")
    
    def _load_site_templates(self) -> Dict[str, Dict]:
        """Load existing site configuration templates"""
        templates = {}
        
        # Define built-in templates
        templates['custom'] = {
            'name': 'Custom Location',
            'description': 'User-defined location and parameters',
            'environment_type': 'unknown'
        }
        
        templates['offshore'] = {
            'name': 'Generic Offshore',
            'description': 'Offshore marine environment',
            'environment_type': 'offshore',
            'water_depth': 30,
            'distance_to_shore': 5.0
        }
        
        templates['nearshore'] = {
            'name': 'Generic Nearshore',
            'description': 'Nearshore coastal environment',
            'environment_type': 'nearshore', 
            'water_depth': 20,
            'distance_to_shore': 2.0
        }
        
        templates['community'] = {
            'name': 'Remote Community',
            'description': 'Small remote community energy system',
            'environment_type': 'community',
            'capacity_range': [0.1, 5.0]
        }
        
        return templates
    
    def build_interactive_config(self) -> Dict[str, Any]:
        """
        Guide user through interactive configuration building
        
        Returns:
            Complete configuration dictionary
        """
        print("=" * 60)
        print("FlexiMORP v2 Configuration Builder")
        print("=" * 60)
        print("This tool will guide you through setting up your offshore renewable energy analysis.")
        print("You can specify what you know and what you want the system to optimize.\n")
        
        # Step 1: Site selection
        site_config = self._configure_site()
        
        # Step 2: Design variables configuration
        design_vars = self._configure_design_variables()
        
        # Step 3: Technology specifications
        tech_config = self._configure_technologies()
        
        # Step 4: Economic parameters
        economic_config = self._configure_economics()
        
        # Step 5: Stakeholder considerations
        stakeholder_config = self._configure_stakeholders()
        
        # Step 6: Analysis options
        analysis_config = self._configure_analysis_options()
        
        # Combine all configurations
        self.config = {
            'site': site_config,
            'design_variables': design_vars,
            'technologies': tech_config,
            'economic': economic_config,
            'stakeholders': stakeholder_config,
            'optimization': analysis_config['optimization'],
            'uncertainty': analysis_config['uncertainty'],
            'flexibility': analysis_config['flexibility']
        }
        
        # Add data sources configuration
        self.config['data_sources'] = self._configure_data_sources()
        
        print("\n" + "=" * 60)
        print("Configuration Complete!")
        print("=" * 60)
        
        return self.config
    
    def _configure_site(self) -> Dict[str, Any]:
        """Configure site information"""
        print("\n📍 STEP 1: Site Configuration")
        print("-" * 30)
        
        # Site template selection
        print("Choose a site template:")
        for i, (key, template) in enumerate(self.site_templates.items(), 1):
            print(f"  {i}. {template['name']} - {template['description']}")
        
        while True:
            try:
                choice = int(input(f"\nSelect template (1-{len(self.site_templates)}): "))
                if 1 <= choice <= len(self.site_templates):
                    template_key = list(self.site_templates.keys())[choice - 1]
                    break
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a number.")
        
        template = self.site_templates[template_key].copy()
        
        # Site-specific inputs
        site_name = input("Enter site name: ").strip()
        template['name'] = site_name
        
        # Coordinates
        print("\nEnter site coordinates:")
        while True:
            try:
                lat = float(input("Latitude (decimal degrees): "))
                if -90 <= lat <= 90:
                    break
                else:
                    print("Latitude must be between -90 and 90.")
            except ValueError:
                print("Please enter a valid number.")
        
        while True:
            try:
                lon = float(input("Longitude (decimal degrees): "))
                if -180 <= lon <= 180:
                    break
                else:
                    print("Longitude must be between -180 and 180.")
            except ValueError:
                print("Please enter a valid number.")
        
        template['coordinates'] = [lat, lon]
        
        # Optional site description
        description = input("Site description (optional): ").strip()
        if description:
            template['description'] = description
        
        return template
    
    def _configure_design_variables(self) -> Dict[str, Any]:
        """Configure design variables and their status"""
        print("\n🎯 STEP 2: Design Variables")
        print("-" * 30)
        print("For each design variable, specify whether it's:")
        print("  • Known: You have a specific value/choice")
        print("  • Unknown: You want the system to optimize it")
        print("  • Constrained: You want to optimize within specific limits\n")
        
        design_vars = {}
        
        # Technology mix
        design_vars['technology_mix'] = self._configure_technology_mix()
        
        # Location
        design_vars['location'] = self._configure_location()
        
        # Capacity
        design_vars['capacity'] = self._configure_capacity()
        
        return design_vars
    
    def _configure_technology_mix(self) -> Dict[str, Any]:
        """Configure technology mix design variable"""
        print("🔧 Technology Mix:")
        print("Which renewable energy technologies to include?")
        
        status = self._get_variable_status("technology mix")
        
        tech_config = {'status': status}
        
        if status == 'known':
            print("Select specific technologies:")
            tech_config['value'] = {}
            for tech in ['wind', 'solar', 'wave']:
                include = input(f"Include {tech}? (y/n): ").lower().startswith('y')
                tech_config['value'][tech] = include
        
        elif status == 'constrained':
            print("Configure technology constraints:")
            tech_config['constraints'] = {}
            
            # Allowed technologies
            print("Which technologies are allowed? (space-separated)")
            allowed_input = input("Technologies (wind solar wave): ").strip()
            if allowed_input:
                tech_config['constraints']['allowed_technologies'] = allowed_input.split()
            else:
                tech_config['constraints']['allowed_technologies'] = ['wind', 'solar', 'wave']
            
            # Environmental restrictions
            restrictions = {}
            for tech in tech_config['constraints']['allowed_technologies']:
                restriction = input(f"Environmental restriction for {tech} (optional): ").strip()
                if restriction:
                    restrictions[tech] = restriction
            
            if restrictions:
                tech_config['constraints']['environmental_restrictions'] = restrictions
        
        return tech_config
    
    def _configure_location(self) -> Dict[str, Any]:
        """Configure location design variable"""
        print("\n📍 Location:")
        print("Site location and placement optimization?")
        
        status = self._get_variable_status("location")
        
        location_config = {'status': status}
        
        if status == 'known':
            # Location already set in site config
            print("Using coordinates from site configuration.")
            location_config['value'] = {
                'coordinates': self.config.get('site', {}).get('coordinates', [0, 0])
            }
        
        elif status == 'constrained':
            print("Configure location search constraints:")
            constraints = {}
            
            # Search area bounds
            print("Define search area (decimal degrees):")
            try:
                min_lat = float(input("Minimum latitude: "))
                max_lat = float(input("Maximum latitude: "))
                min_lon = float(input("Minimum longitude: "))
                max_lon = float(input("Maximum longitude: "))
                
                constraints['search_area'] = {
                    'bounds': [[min_lat, min_lon], [max_lat, max_lon]]
                }
            except ValueError:
                print("Invalid coordinates, using default search area.")
                constraints['search_area'] = {
                    'bounds': [[-90, -180], [90, 180]]
                }
            
            # Depth and distance ranges
            try:
                min_depth = float(input("Minimum water depth (m): "))
                max_depth = float(input("Maximum water depth (m): "))
                constraints['depth_range'] = [min_depth, max_depth]
            except ValueError:
                constraints['depth_range'] = [10, 100]
            
            try:
                min_dist = float(input("Minimum distance to shore (km): "))
                max_dist = float(input("Maximum distance to shore (km): "))
                constraints['shore_distance_range'] = [min_dist, max_dist]
            except ValueError:
                constraints['shore_distance_range'] = [1, 20]
            
            location_config['constraints'] = constraints
        
        return location_config
    
    def _configure_capacity(self) -> Dict[str, Any]:
        """Configure capacity design variable"""
        print("\n⚡ Capacity:")
        print("System capacity and sizing?")
        
        status = self._get_variable_status("capacity")
        
        capacity_config = {'status': status}
        
        if status == 'known':
            print("Enter specific capacities (MW):")
            capacity_config['value'] = {}
            
            try:
                total_mw = float(input("Total capacity (MW): "))
                capacity_config['value']['total_mw'] = total_mw
                
                # Ask for technology split if multiple technologies
                if self.config.get('design_variables', {}).get('technology_mix', {}).get('status') == 'known':
                    tech_split = {}
                    remaining = total_mw
                    techs = [t for t, enabled in capacity_config['value'].items() if enabled]
                    
                    for i, tech in enumerate(techs):
                        if i == len(techs) - 1:  # Last technology gets remaining
                            tech_split[tech] = remaining
                        else:
                            try:
                                mw = float(input(f"{tech.capitalize()} capacity (MW, {remaining:.1f} remaining): "))
                                tech_split[tech] = min(mw, remaining)
                                remaining -= tech_split[tech]
                            except ValueError:
                                tech_split[tech] = remaining / (len(techs) - i)
                                remaining -= tech_split[tech]
                    
                    capacity_config['value']['technology_split'] = tech_split
                
            except ValueError:
                print("Invalid capacity, using default.")
                capacity_config['value']['total_mw'] = 50
        
        elif status == 'constrained':
            print("Configure capacity constraints:")
            constraints = {}
            
            try:
                min_mw = float(input("Minimum total capacity (MW): "))
                max_mw = float(input("Maximum total capacity (MW): "))
                constraints['total_range'] = [min_mw, max_mw]
            except ValueError:
                constraints['total_range'] = [10, 500]
            
            capacity_config['constraints'] = constraints
        
        return capacity_config
    
    def _get_variable_status(self, variable_name: str) -> str:
        """Get status choice for a design variable"""
        print(f"\nHow do you want to handle {variable_name}?")
        print("  1. Known - I have specific values")
        print("  2. Unknown - Optimize for me")
        print("  3. Constrained - Optimize within limits")
        
        while True:
            try:
                choice = int(input("Choice (1-3): "))
                if choice == 1:
                    return 'known'
                elif choice == 2:
                    return 'unknown'
                elif choice == 3:
                    return 'constrained'
                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")
            except ValueError:
                print("Please enter a number.")
    
    def _configure_technologies(self) -> Dict[str, Any]:
        """Configure technology specifications"""
        print("\n🔧 STEP 3: Technology Specifications")
        print("-" * 30)
        
        technologies = {}
        
        # Get available technologies from design variables
        design_vars = self.config.get('design_variables', {})
        tech_mix = design_vars.get('technology_mix', {})
        
        if tech_mix.get('status') == 'known':
            available_techs = [t for t, enabled in tech_mix['value'].items() if enabled]
        elif tech_mix.get('status') == 'constrained':
            available_techs = tech_mix['constraints'].get('allowed_technologies', ['wind', 'solar', 'wave'])
        else:
            available_techs = ['wind', 'solar', 'wave']
        
        print(f"Configuring specifications for: {', '.join(available_techs)}")
        
        for tech in available_techs:
            print(f"\n{tech.upper()} Configuration:")
            
            tech_config = {
                'available': True,
                'environmental_impact': self._get_choice(
                    f"{tech} environmental impact level",
                    ['low', 'medium', 'high']
                )
            }
            
            # Cost per MW (simplified input)
            try:
                cost = float(input(f"{tech} cost per MW (USD, default varies by tech): ") or "0")
                if cost > 0:
                    tech_config['cost_per_mw'] = cost
            except ValueError:
                pass
            
            # Capacity factor estimate
            try:
                cf = float(input(f"{tech} expected capacity factor (0-1, optional): ") or "0")
                if 0 < cf <= 1:
                    tech_config['capacity_factor'] = cf
            except ValueError:
                pass
            
            technologies[tech] = tech_config
        
        return technologies
    
    def _configure_economics(self) -> Dict[str, Any]:
        """Configure economic parameters"""
        print("\n💰 STEP 4: Economic Parameters")
        print("-" * 30)
        
        economic = {}
        
        # Key economic parameters
        try:
            economic['discount_rate'] = float(input("Discount rate (decimal, e.g., 0.08 for 8%): ") or "0.08")
        except ValueError:
            economic['discount_rate'] = 0.08
        
        try:
            economic['project_lifetime'] = int(input("Project lifetime (years): ") or "25")
        except ValueError:
            economic['project_lifetime'] = 25
        
        try:
            economic['electricity_price'] = float(input("Electricity price ($/kWh): ") or "0.15")
        except ValueError:
            economic['electricity_price'] = 0.15
        
        # Optional parameters
        try:
            inflation = float(input("Inflation rate (decimal, optional): ") or "0")
            if inflation > 0:
                economic['inflation_rate'] = inflation
        except ValueError:
            pass
        
        return economic
    
    def _configure_stakeholders(self) -> Dict[str, Any]:
        """Configure stakeholder considerations"""
        print("\n👥 STEP 5: Stakeholder Considerations")
        print("-" * 30)
        
        stakeholders = {}
        
        # Key stakeholder groups
        stakeholder_groups = [
            'community_ownership',
            'environmental_groups', 
            'fishing_industry',
            'tourism_industry'
        ]
        
        for group in stakeholder_groups:
            include = input(f"Include {group.replace('_', ' ')}? (y/n): ").lower().startswith('y')
            stakeholders[group] = include
        
        # Decision criteria weights
        print("\nDecision criteria weights (must sum to 1.0):")
        
        weights = {}
        remaining = 1.0
        criteria = ['economic_weight', 'environmental_weight', 'social_weight']
        
        for i, criterion in enumerate(criteria):
            if i == len(criteria) - 1:  # Last weight gets remaining
                weights[criterion] = remaining
                print(f"{criterion}: {remaining:.2f}")
            else:
                try:
                    weight = float(input(f"{criterion} ({remaining:.2f} remaining): ") or str(remaining/2))
                    weight = min(weight, remaining)
                    weights[criterion] = weight
                    remaining -= weight
                except ValueError:
                    weight = remaining / (len(criteria) - i)
                    weights[criterion] = weight
                    remaining -= weight
        
        stakeholders['decision_criteria'] = weights
        
        return stakeholders
    
    def _configure_analysis_options(self) -> Dict[str, Any]:
        """Configure analysis and optimization options"""
        print("\n⚙️ STEP 6: Analysis Options")
        print("-" * 30)
        
        # Optimization objective
        print("Primary optimization objective:")
        objective = self._get_choice(
            "objective",
            ['minimize_lcoe', 'maximize_npv', 'minimize_environmental_impact']
        )
        
        optimization = {
            'objective': objective,
            'constraints': {
                'max_investment': self._get_float_input("Maximum investment ($)", 10000000),
                'min_capacity_factor': self._get_float_input("Minimum capacity factor", 0.2)
            }
        }
        
        # Uncertainty analysis
        uncertainty = {
            'monte_carlo_runs': self._get_int_input("Monte Carlo runs", 1000),
            'variables': {
                'weather': 'stochastic',
                'electricity_price': 'scenario_based',
                'capex': 'normal_distribution',
                'opex': 'normal_distribution'
            }
        }
        
        # Flexibility options
        print("\nFlexibility options:")
        flexibility = {
            'expansion_options': [10, 25, 50],  # Default MW increments
            'abandonment_option': input("Include abandonment option? (y/n): ").lower().startswith('y'),
            'technology_switching': input("Allow technology switching? (y/n): ").lower().startswith('y'),
            'adaptive_deployment': input("Enable adaptive deployment? (y/n): ").lower().startswith('y')
        }
        
        return {
            'optimization': optimization,
            'uncertainty': uncertainty,
            'flexibility': flexibility
        }
    
    def _configure_data_sources(self) -> Dict[str, Any]:
        """Configure API data sources"""
        print("\n🌐 Data Sources Configuration")
        print("-" * 30)
        
        data_sources = {
            'weather': {
                'primary': 'nasa_power',
                'secondary': 'openweather',
                'cache_duration': 24
            },
            'wind_resource': {
                'source': 'nrel',
                'cache_duration': 168  # 1 week
            },
            'solar_resource': {
                'source': 'nrel', 
                'cache_duration': 168
            }
        }
        
        # Add wave resource if applicable
        design_vars = self.config.get('design_variables', {})
        tech_mix = design_vars.get('technology_mix', {})
        
        if 'wave' in str(tech_mix):
            data_sources['wave_resource'] = {
                'source': 'copernicus',
                'cache_duration': 24
            }
        
        return data_sources
    
    def _get_choice(self, prompt: str, choices: List[str]) -> str:
        """Get user choice from a list of options"""
        print(f"\n{prompt}:")
        for i, choice in enumerate(choices, 1):
            print(f"  {i}. {choice}")
        
        while True:
            try:
                selection = int(input(f"Choice (1-{len(choices)}): "))
                if 1 <= selection <= len(choices):
                    return choices[selection - 1]
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a number.")
    
    def _get_float_input(self, prompt: str, default: float) -> float:
        """Get float input with default"""
        try:
            return float(input(f"{prompt} (default {default}): ") or str(default))
        except ValueError:
            return default
    
    def _get_int_input(self, prompt: str, default: int) -> int:
        """Get integer input with default"""
        try:
            return int(input(f"{prompt} (default {default}): ") or str(default))
        except ValueError:
            return default
    
    def save_config(self, filepath: str) -> bool:
        """
        Save configuration to YAML file
        
        Args:
            filepath: Path to save configuration file
            
        Returns:
            True if successful
        """
        try:
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
            
            print(f"\n✅ Configuration saved to: {filepath}")
            return True
            
        except Exception as e:
            print(f"\n❌ Error saving configuration: {e}")
            return False
    
    def load_config(self, filepath: str) -> Optional[Dict[str, Any]]:
        """
        Load configuration from YAML file
        
        Args:
            filepath: Path to configuration file
            
        Returns:
            Configuration dictionary or None if failed
        """
        try:
            with open(filepath, 'r') as f:
                self.config = yaml.safe_load(f)
            
            print(f"✅ Configuration loaded from: {filepath}")
            return self.config
            
        except Exception as e:
            print(f"❌ Error loading configuration: {e}")
            return None
    
    def validate_config(self, config: Dict[str, Any] = None) -> Tuple[bool, List[str]]:
        """
        Validate configuration completeness and consistency
        
        Args:
            config: Configuration to validate (uses self.config if None)
            
        Returns:
            (is_valid, list_of_errors)
        """
        if config is None:
            config = self.config
        
        errors = []
        
        # Required sections
        required_sections = ['site', 'design_variables', 'technologies', 'economic']
        for section in required_sections:
            if section not in config:
                errors.append(f"Missing required section: {section}")
        
        # Site validation
        if 'site' in config:
            site = config['site']
            if 'coordinates' not in site:
                errors.append("Site coordinates are required")
            elif len(site['coordinates']) != 2:
                errors.append("Site coordinates must be [latitude, longitude]")
        
        # Design variables validation
        if 'design_variables' in config:
            for var_name, var_config in config['design_variables'].items():
                if 'status' not in var_config:
                    errors.append(f"Design variable '{var_name}' missing status")
                elif var_config['status'] not in ['known', 'unknown', 'constrained']:
                    errors.append(f"Invalid status for '{var_name}': {var_config['status']}")
        
        # Economic validation
        if 'economic' in config:
            economic = config['economic']
            if 'discount_rate' not in economic:
                errors.append("Discount rate is required in economic section")
            elif not (0 < economic['discount_rate'] < 1):
                errors.append("Discount rate should be between 0 and 1")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            print("✅ Configuration validation passed")
        else:
            print("❌ Configuration validation failed:")
            for error in errors:
                print(f"  • {error}")
        
        return is_valid, errors
    
    def get_config_summary(self) -> str:
        """
        Get a human-readable summary of the configuration
        
        Returns:
            Formatted configuration summary
        """
        if not self.config:
            return "No configuration loaded."
        
        summary = []
        summary.append("Configuration Summary")
        summary.append("=" * 50)
        
        # Site info
        if 'site' in self.config:
            site = self.config['site']
            summary.append(f"Site: {site.get('name', 'Unknown')}")
            if 'coordinates' in site:
                lat, lon = site['coordinates']
                summary.append(f"Location: {lat:.2f}°, {lon:.2f}°")
        
        # Design variables
        if 'design_variables' in self.config:
            summary.append("\nDesign Variables:")
            for var_name, var_config in self.config['design_variables'].items():
                status = var_config.get('status', 'unknown')
                summary.append(f"  • {var_name.replace('_', ' ').title()}: {status}")
        
        # Technologies
        if 'technologies' in self.config:
            tech_names = list(self.config['technologies'].keys())
            summary.append(f"\nTechnologies: {', '.join(tech_names)}")
        
        # Economic
        if 'economic' in self.config:
            economic = self.config['economic']
            summary.append(f"\nEconomic:")
            summary.append(f"  • Discount rate: {economic.get('discount_rate', 0)*100:.1f}%")
            summary.append(f"  • Project lifetime: {economic.get('project_lifetime', 25)} years")
            summary.append(f"  • Electricity price: ${economic.get('electricity_price', 0.15):.3f}/kWh")
        
        return "\n".join(summary)


def main():
    """Main function for interactive configuration building"""
    builder = ConfigurationBuilder()
    
    try:
        # Build configuration interactively
        config = builder.build_interactive_config()
        
        # Validate configuration
        is_valid, errors = builder.validate_config(config)
        
        if is_valid:
            # Show summary
            print("\n" + builder.get_config_summary())
            
            # Offer to save
            save_choice = input("\nSave configuration to file? (y/n): ").lower().startswith('y')
            if save_choice:
                filename = input("Enter filename (without extension): ").strip()
                if not filename:
                    filename = "custom_config"
                
                filepath = f"data/{filename}/config.yaml"
                builder.save_config(filepath)
        
        return config
        
    except KeyboardInterrupt:
        print("\n\nConfiguration cancelled by user.")
        return None
    except Exception as e:
        print(f"\nError during configuration: {e}")
        return None


if __name__ == "__main__":
    main()
