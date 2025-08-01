#!/usr/bin/env python3
"""
Test script for enhanced Alaska configuration structure
"""

import yaml
import sys
from pathlib import Path

# Add the project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def test_config_loading():
    """Test that the enhanced config loads correctly"""
    
    print("🧪 Testing Enhanced Alaska Configuration")
    print("=" * 50)
    
    # Load the config file
    config_path = project_root / "data" / "alaska" / "config.yaml"
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        print("✅ Config file loaded successfully")
        
        # Test basic site info
        assert config['site']['name'] == "Igiugig, Alaska"
        print(f"   Site: {config['site']['name']}")
        
        # Test enhanced design variables
        design_vars = config['design_variables']
        assert design_vars['tech_mix_known'] == True
        assert 'hydro_tidal' in design_vars['technology_selection']
        print(f"   Tech mix known: {design_vars['tech_mix_known']}")
        print(f"   Selected technologies: {design_vars['technology_selection']}")
        
        # Test location zones
        location = design_vars['location']
        assert location['approach'] == "bounded_with_zones"
        exclusion_zones = location['constraints']['exclusion_zones']
        preferred_zones = location['constraints']['preferred_zones']
        
        print(f"   Exclusion zones: {len(exclusion_zones)}")
        print(f"   Preferred zones: {len(preferred_zones)}")
        
        # Test zone structure
        for zone in exclusion_zones:
            assert 'name' in zone
            assert 'type' in zone
            assert 'priority' in zone
            assert 'geometry' in zone
        
        high_priority_zones = [z for z in exclusion_zones if z['priority'] == 'high']
        medium_priority_zones = [z for z in exclusion_zones if z['priority'] == 'medium']
        
        print(f"   High priority (complete exclusion): {len(high_priority_zones)}")
        print(f"   Medium priority (cost penalty): {len(medium_priority_zones)}")
        
        # Test enhanced solar options
        solar = config['technologies']['solar']
        assert 'deployment_options' in solar
        deployment_options = solar['deployment_options']
        
        assert 'land' in deployment_options
        assert 'floating' in deployment_options
        assert 'both' in deployment_options
        
        print(f"   Solar deployment options: {list(deployment_options.keys())}")
        print(f"   Land cost multiplier: {deployment_options['land']['cost_multiplier']}")
        print(f"   Floating cost multiplier: {deployment_options['floating']['cost_multiplier']}")
        
        # Test hydro category
        hydro = config['technologies']['hydro']
        assert hydro['available'] == True
        assert hydro['tidal_range']['available'] == False
        assert hydro['tidal_current']['available'] == True
        
        tidal_current = hydro['tidal_current']
        assert tidal_current['resource_type'] == "river_flow"
        assert tidal_current['seasonal_variation'] == True
        
        print(f"   Hydro available: {hydro['available']}")
        print(f"   Tidal current available: {tidal_current['available']}")
        print(f"   Tidal current cost/MW: ${tidal_current['cost_per_mw']:,}")
        print(f"   Seasonal variation: {tidal_current['seasonal_variation']}")
        
        # Test hydro resource data source
        data_sources = config['data_sources']
        assert 'hydro_resource' in data_sources
        hydro_resource = data_sources['hydro_resource']['tidal_current']
        
        assert hydro_resource['source'] == "usgs_river_flow"
        assert hydro_resource['parameters']['seasonal_analysis'] == True
        
        print(f"   Hydro resource source: {hydro_resource['source']}")
        print(f"   River station: {hydro_resource['parameters']['flow_measurement_station']}")
        
        # Test capacity constraints updated for hydro
        capacity = design_vars['capacity']['constraints']['individual_tech_limits']
        assert 'hydro_tidal' in capacity
        assert capacity['hydro_tidal'] == [0.02, 0.5]
        
        print(f"   Hydro tidal capacity range: {capacity['hydro_tidal']} MW")
        
        print("\n✅ All enhanced configuration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_backwards_compatibility():
    """Test that existing modules can still access the config"""
    
    print("\n🔄 Testing Backwards Compatibility")
    print("=" * 40)
    
    try:
        # Try importing the config module
        from fleximorpv2.config import load_config
        
        # This will use the old parsing logic - should handle gracefully
        try:
            config = load_config("alaska")
            print("⚠️  Old config loader worked but may miss new features")
            
            # Check what technologies it found
            enabled_techs = config.get_enabled_technologies()
            print(f"   Enabled technologies found: {enabled_techs}")
            
            return True
            
        except Exception as e:
            print(f"❌ Old config loader failed: {e}")
            print("   → Need to update config.py to handle new structure")
            return False
            
    except ImportError as e:
        print(f"❌ Could not import config module: {e}")
        return False

if __name__ == "__main__":
    print("🚀 FlexiMORP v2 Enhanced Configuration Test Suite")
    print("=" * 55)
    
    success = True
    
    # Test 1: Enhanced config loading
    success &= test_config_loading()
    
    # Test 2: Backwards compatibility 
    success &= test_backwards_compatibility()
    
    print("\n" + "=" * 55)
    if success:
        print("🎉 All tests passed! Enhanced configuration is working.")
    else:
        print("⚠️  Some tests failed. Check output above for details.")
        sys.exit(1)
