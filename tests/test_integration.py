"""
Test suite for complete workflow integration.
"""

import pytest
from unittest.mock import Mock, patch
import json
import tempfile
from pathlib import Path

from fleximorpv2.baseline_optimization import BaselineOptimization
from fleximorpv2.uncertainty_analysis import UncertaintyAnalysis
from fleximorpv2.flexible_design import FlexibleDesign
from fleximorpv2.sensitivity_analysis import SensitivityAnalysis
from fleximorpv2.config import load_config


class TestCompleteWorkflow:
    """Test complete 4-step analysis workflow."""
    
    def setup_method(self):
        self.config = load_config("alaska")
    
    @patch('fleximorpv2.utils.data_loader.APIDataLoader')
    def test_baseline_to_uncertainty_workflow(self, mock_loader):
        """Test workflow from baseline to uncertainty analysis."""
        # Mock data loading
        mock_loader.return_value.load_weather_data.return_value = {
            'wind_speed': [8.0] * 8760,
            'solar_irradiance': [200.0] * 8760
        }
        
        # Step 1: Baseline optimization
        baseline = BaselineOptimization(self.config)
        baseline.resource_data = mock_loader.return_value.load_weather_data.return_value
        
        # Mock evaluation for speed
        with patch.object(baseline, '_evaluate_platform_performance') as mock_eval:
            mock_eval.return_value = {
                'lcoe': 85.0,
                'npv': 1000000,
                'capacity_factor': 0.35,
                'capex': 50000000,
                'opex': 2000000,
                'revenue': 8000000,
                'annual_energy': 100000
            }
            
            baseline_results = baseline.optimize('production', 1000000, maxiter=10)
        
        assert baseline_results.objective_value > 0
        assert baseline_results.optimal_design is not None
        
        # Step 2: Uncertainty analysis
        uncertainty = UncertaintyAnalysis(self.config)
        
        # Mock scenario evaluation for speed
        with patch.object(uncertainty, '_evaluate_scenarios') as mock_scenarios:
            mock_scenarios.return_value = [
                {'lcoe': 85.0, 'npv': 1000000, 'capacity_factor': 0.35, 'scenario_id': i}
                for i in range(100)
            ]
            
            uncertainty_results = uncertainty.analyze_uncertainty(
                baseline_results.optimal_design, 
                reoptimize=False
            )
        
        assert uncertainty_results.mean_performance['lcoe'] > 0
        assert len(uncertainty_results.scenario_results) > 0
    
    def test_results_serialization(self):
        """Test that results can be saved and loaded."""
        from fleximorpv2.baseline_optimization import BaselineResults
        
        results = BaselineResults(
            optimal_design={'wind_capacity': 100},
            objective_value=85.5,
            technology_capacities={'wind': 100},
            financial_metrics={'lcoe': 85.5},
            technical_metrics={'capacity_factor': 0.4},
            optimization_info={'success': True},
            timestamp='2025-01-01T00:00:00'
        )
        
        # Test serialization
        result_dict = results.to_dict()
        json_str = json.dumps(result_dict)
        
        # Should not raise exception
        loaded_dict = json.loads(json_str)
        assert loaded_dict['objective_value'] == 85.5


class TestCaseStudyConfigurations:
    """Test case study specific configurations."""
    
    def test_alaska_config_loading(self):
        """Test Alaska configuration loads correctly."""
        config = load_config("alaska")
        
        assert "alaska" in config.name.lower()
        assert config.coordinates is not None
        assert len(config.coordinates) == 2
    
    def test_blyth_config_loading(self):
        """Test Blyth configuration loads correctly."""
        config = load_config("blyth")
        
        assert "blyth" in config.name.lower()
        assert config.coordinates is not None
        
    def test_eastport_config_loading(self):
        """Test Eastport configuration loads correctly."""
        config = load_config("eastport")
        
        assert "eastport" in config.name.lower()
        assert config.coordinates is not None


class TestAPIIntegration:
    """Test API integration components."""
    
    @patch('requests.get')
    def test_api_data_loading(self, mock_get):
        """Test API data loading with mocked requests."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': {
                'wind_speed': [8.0] * 24,
                'temperature': [15.0] * 24
            }
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        from fleximorpv2.utils.data_loader import APIDataLoader
        config = load_config("alaska")
        loader = APIDataLoader(config)
        
        # This would normally make real API calls
        # Test passes if no exception is raised during initialization
        assert loader is not None


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_site_config(self):
        """Test handling of invalid site configuration."""
        with pytest.raises((FileNotFoundError, ValueError)):
            load_config("nonexistent_site")
    
    def test_optimization_with_no_data(self):
        """Test optimization behavior with missing data."""
        config = load_config("alaska")
        optimizer = BaselineOptimization(config)
        
        # This should handle missing resource data gracefully
        with pytest.raises((AttributeError, ValueError)):
            optimizer.optimize('production', 1000000, maxiter=1)


def test_package_imports():
    """Test that all main modules can be imported."""
    import fleximorpv2
    import fleximorpv2.baseline_optimization
    import fleximorpv2.uncertainty_analysis
    import fleximorpv2.flexible_design
    import fleximorpv2.sensitivity_analysis
    import fleximorpv2.config
    import fleximorpv2.graphics
    
    # Should not raise import errors
    assert True
