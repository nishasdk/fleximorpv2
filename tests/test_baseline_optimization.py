"""
Test suite for baseline optimization module.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from fleximorpv2.baseline_optimization import BaselineOptimization, OptimizationTarget, BaselineResults
from fleximorpv2.config import SiteConfig, load_config


class TestBaselineOptimization:
    """Test baseline optimization functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = load_config("alaska")
        self.optimizer = BaselineOptimization(self.config)
    
    def test_initialization(self):
        """Test optimizer initialization."""
        assert self.optimizer.config == self.config
        assert self.optimizer.platform_model is not None
        assert self.optimizer.tech_model is not None
        assert self.optimizer.economic_model is not None
        assert self.optimizer.results is None
    
    def test_setup_optimization_bounds(self):
        """Test optimization bounds setup."""
        self.optimizer._setup_optimization_bounds()
        
        assert 'wind_capacity' in self.optimizer.bounds
        assert 'platform_area' in self.optimizer.bounds
        assert 'water_depth' in self.optimizer.bounds
        assert 'distance_to_shore' in self.optimizer.bounds
        
        # Check bounds are reasonable
        assert self.optimizer.bounds['platform_area'][0] > 0
        assert self.optimizer.bounds['water_depth'][0] > 0
    
    def test_decode_variables(self):
        """Test variable decoding."""
        target = OptimizationTarget('location', (60.0, -150.0))
        # Alaska config enables wind + solar + hydro (3 techs) + 3 platform vars = 6 elements
        n_techs = len(self.config.get_enabled_technologies())
        x_vals = [50.0, 25.0, 5.0][:n_techs] + [10000, 50, 20]
        x = np.array(x_vals)

        decoded = self.optimizer._decode_variables(x, target)

        assert 'wind_capacity' in decoded
        assert decoded['platform_area'] == 10000
        assert decoded['water_depth'] == 50
        assert decoded['distance_to_shore'] == 20
    
    @patch('fleximorpv2.baseline_optimization.APIDataLoader')
    def test_load_optimization_data(self, mock_loader):
        """Test data loading for optimization."""
        mock_loader.return_value.load_weather_data.return_value = {
            'wind_speed': np.random.normal(8, 2, 8760),
            'solar_irradiance': np.random.normal(200, 50, 8760)
        }
        
        target = OptimizationTarget('location', (60.0, -150.0))
        self.optimizer._load_optimization_data(target)
        
        assert hasattr(self.optimizer, 'resource_data')
    
    def test_optimization_target_creation(self):
        """Test optimization target creation."""
        target = OptimizationTarget(
            target_type='production',
            target_value=1000000,
            constraints={'max_investment': 50000000}
        )
        
        assert target.target_type == 'production'
        assert target.target_value == 1000000
        assert target.constraints['max_investment'] == 50000000
    
    def test_get_initial_guess(self):
        """Test initial guess generation."""
        x0 = self.optimizer._get_initial_guess()
        
        assert len(x0) > 0
        assert all(x >= 0 for x in x0)
    
    def test_invalid_target_type(self):
        """Test handling of invalid target type."""
        with pytest.raises(ValueError):
            self.optimizer.optimize('invalid_target', 100)
    
    def test_results_to_dict(self):
        """Test results serialization."""
        results = BaselineResults(
            optimal_design={'wind_capacity': 100},
            objective_value=85.5,
            technology_capacities={'wind': 100, 'solar': 50},
            financial_metrics={'lcoe': 85.5, 'npv': 1000000},
            technical_metrics={'capacity_factor': 0.4},
            optimization_info={'success': True},
            timestamp='2025-01-01T00:00:00'
        )
        
        result_dict = results.to_dict()
        
        assert 'optimal_design' in result_dict
        assert 'objective_value' in result_dict
        assert result_dict['objective_value'] == 85.5


class TestOptimizationConstraints:
    """Test optimization constraint handling."""
    
    def setup_method(self):
        self.config = load_config("alaska")
        self.optimizer = BaselineOptimization(self.config)
    
    def test_constraint_penalties(self):
        """Test constraint penalty application."""
        performance = {
            'lcoe': 85.0,
            'npv': 1000000,
            'capex': 60000000,  # Exceeds max investment
            'capacity_factor': 0.25,  # Below minimum
            'annual_energy': 1000000,
        }
        
        original_lcoe = performance['lcoe']
        design_vars = {'wind_capacity': 100}
        target = OptimizationTarget('production', 1000000)
        
        penalized = self.optimizer._apply_constraints(performance, design_vars, target)
        
        # LCOE should be penalized
        assert penalized['lcoe'] > original_lcoe
    
    def test_production_target_constraint(self):
        """Test production target constraint."""
        performance = {
            'lcoe': 85.0,
            'annual_energy': 800000,  # Below target
            'capex': 50000000,
            'capacity_factor': 0.35,
        }
        
        original_lcoe = performance['lcoe']
        design_vars = {'wind_capacity': 100}
        target = OptimizationTarget('production', 1000000)  # 1 GWh target
        
        penalized = self.optimizer._apply_constraints(performance, design_vars, target)
        
        # Should add penalty for missing production target
        assert penalized['lcoe'] > original_lcoe


@pytest.fixture
def mock_config():
    """Create mock configuration for testing."""
    config = Mock(spec=SiteConfig)
    config.name = "TestSite"
    config.coordinates = (60.0, -150.0)
    config.get_enabled_technologies.return_value = ['wind', 'solar']

    # Mock technology configurations
    wind_tech_config = Mock()
    wind_tech_config.cost_per_mw = 1600000
    solar_tech_config = Mock()
    solar_tech_config.cost_per_mw = 1200000
    config.technologies = {
        'wind': wind_tech_config,
        'solar': solar_tech_config
    }

    config.optimization = {
        'objective': 'minimize_lcoe',
        'constraints': {
            'max_investment': 50000000,
            'min_capacity_factor': 0.3
        }
    }
    config.economic = {
        'project_lifetime': 25,
        'discount_rate': 0.08
    }
    return config


def test_optimization_with_mock_config(mock_config):
    """Test optimization with mocked configuration."""
    optimizer = BaselineOptimization(mock_config)
    
    # Check that mock config is used correctly
    assert optimizer.config.name == "TestSite"
    assert optimizer.config.coordinates == (60.0, -150.0)
