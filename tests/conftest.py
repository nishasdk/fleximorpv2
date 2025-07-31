"""
Pytest configuration and fixtures for FlexiMORP v2 test suite.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from unittest.mock import Mock

# Test configuration
TEST_DATA_DIR = Path(__file__).parent / "test_data"
MOCK_WEATHER_DATA_SIZE = 8760  # One year of hourly data


@pytest.fixture
def mock_weather_data():
    """Generate mock weather data for testing."""
    np.random.seed(42)
    return {
        'wind_speed': np.random.normal(8.0, 2.0, MOCK_WEATHER_DATA_SIZE),
        'solar_irradiance': np.random.gamma(2, 100, MOCK_WEATHER_DATA_SIZE),
        'wave_height': np.random.exponential(2.0, MOCK_WEATHER_DATA_SIZE),
        'temperature': np.random.normal(15.0, 5.0, MOCK_WEATHER_DATA_SIZE),
        'timestamp': pd.date_range('2024-01-01', periods=MOCK_WEATHER_DATA_SIZE, freq='H')
    }


@pytest.fixture
def mock_site_config():
    """Create mock site configuration for testing."""
    return {
        'name': 'TestSite',
        'coordinates': (60.0, -150.0),
        'technologies': {
            'wind': {'enabled': True, 'max_capacity': 200, 'capex': 2500},
            'solar': {'enabled': True, 'max_capacity': 100, 'capex': 2000},
            'wave': {'enabled': False, 'max_capacity': 50, 'capex': 4000}
        },
        'economic': {
            'discount_rate': 0.08,
            'project_lifetime': 25,
            'electricity_price': 0.12,
            'currency': 'GBP'
        },
        'optimization': {
            'objective': 'minimize_lcoe',
            'constraints': {
                'max_investment': 50000000,
                'min_capacity_factor': 0.3,
                'max_total_capacity': 300
            }
        },
        'uncertainty': {
            'monte_carlo_runs': 1000,
            'variables': {
                'weather': 'stochastic',
                'electricity_price': 'scenario_based',
                'capex': 'normal_distribution'
            }
        },
        'flexibility': {
            'decision_points': [5, 10, 15],
            'expansion_options': [50, 100],
            'abandonment_option': True,
            'technology_switching': True
        }
    }


@pytest.fixture
def sample_optimization_result():
    """Create sample optimization result for testing."""
    return {
        'optimal_design': {
            'wind_capacity': 100,
            'solar_capacity': 50,
            'platform_area': 7500,
            'water_depth': 45,
            'distance_to_shore': 25
        },
        'objective_value': 85.5,
        'technology_capacities': {'wind': 100, 'solar': 50},
        'financial_metrics': {
            'lcoe': 85.5,
            'npv': 1000000,
            'irr': 0.12,
            'capex': 35000000,
            'opex': 1050000
        },
        'technical_metrics': {
            'capacity_factor': 0.42,
            'annual_energy': 550000,
            'total_capacity': 150
        },
        'optimization_info': {
            'success': True,
            'iterations': 250,
            'function_evaluations': 3750
        }
    }


@pytest.fixture
def sample_uncertainty_scenarios():
    """Create sample uncertainty scenarios for testing."""
    np.random.seed(42)
    n_scenarios = 100
    
    scenarios = []
    for i in range(n_scenarios):
        scenario = {
            'scenario_id': i,
            'lcoe': np.random.normal(85, 15),
            'npv': np.random.normal(1000000, 500000),
            'capacity_factor': np.random.normal(0.4, 0.05),
            'annual_energy': np.random.normal(550000, 75000),
            'weather_multiplier': np.random.normal(1.0, 0.15),
            'cost_multiplier': np.random.normal(1.0, 0.20)
        }
        scenarios.append(scenario)
    
    return scenarios


@pytest.fixture
def sample_mcda_data():
    """Create sample MCDA data for testing."""
    np.random.seed(42)
    n_alternatives = 20
    
    data = {
        'alternative_id': [f'Alt_{i+1}' for i in range(n_alternatives)],
        'lcoe': np.random.uniform(70, 120, n_alternatives),
        'emissions_reduction': np.random.uniform(10000, 50000, n_alternatives),
        'social_acceptance': np.random.uniform(60, 95, n_alternatives),
        'aquaculture_synergy': np.random.uniform(40, 85, n_alternatives)
    }
    
    return pd.DataFrame(data)


# Test data generation utilities
def generate_test_trio_solutions(n_solutions=50):
    """Generate test TRIO solutions."""
    np.random.seed(42)
    
    solutions = []
    for i in range(n_solutions):
        solution = {
            'solution_id': f'S{i+1}',
            'latitude': np.random.uniform(59.0, 62.0),
            'longitude': np.random.uniform(-155.0, -148.0),
            'wind_capacity': np.random.randint(30, 120),
            'solar_capacity': np.random.randint(20, 80),
            'lcoe': np.random.uniform(75, 110),
            'emissions_reduction': np.random.uniform(15000, 45000),
            'social_acceptance': np.random.uniform(55, 90),
            'aquaculture_synergy': np.random.uniform(35, 80)
        }
        solution['total_capacity'] = solution['wind_capacity'] + solution['solar_capacity']
        solutions.append(solution)
    
    return pd.DataFrame(solutions)


# Custom assertions for testing
def assert_optimization_result_valid(result):
    """Assert that optimization result has valid structure."""
    required_keys = ['optimal_design', 'objective_value', 'technology_capacities',
                    'financial_metrics', 'technical_metrics', 'optimization_info']
    
    for key in required_keys:
        assert key in result, f"Missing required key: {key}"
    
    assert result['objective_value'] > 0, "Objective value should be positive"
    assert result['technical_metrics']['capacity_factor'] <= 1.0, "Capacity factor should be <= 1.0"
    assert result['financial_metrics']['lcoe'] > 0, "LCOE should be positive"


def assert_mcda_scores_valid(scores):
    """Assert that MCDA scores are valid."""
    required_criteria = ['lcoe', 'emissions_reduction', 'social_acceptance', 'aquaculture_synergy']
    
    for criterion in required_criteria:
        assert criterion in scores, f"Missing MCDA criterion: {criterion}"
        assert scores[criterion] >= 0, f"{criterion} should be non-negative"
    
    # LCOE should be reasonable (£50-200/MWh)
    assert 50 <= scores['lcoe'] <= 200, f"LCOE {scores['lcoe']} outside reasonable range"


def assert_uncertainty_results_valid(results):
    """Assert that uncertainty analysis results are valid."""
    required_keys = ['mean_performance', 'std_performance', 'risk_metrics']
    
    for key in required_keys:
        assert key in results, f"Missing required key: {key}"
    
    # Check that standard deviations are positive
    for metric, std_val in results['std_performance'].items():
        assert std_val >= 0, f"Standard deviation for {metric} should be non-negative"
    
    # Check risk metrics
    if 'prob_negative_npv' in results['risk_metrics']:
        prob = results['risk_metrics']['prob_negative_npv']
        assert 0 <= prob <= 1, "Probability should be between 0 and 1"


# Test performance benchmarks
PERFORMANCE_BENCHMARKS = {
    'lcoe_min': 50,  # £/MWh
    'lcoe_max': 200,  # £/MWh
    'capacity_factor_min': 0.2,
    'capacity_factor_max': 0.8,
    'npv_threshold': -10000000,  # -£10M (maximum acceptable loss)
    'optimization_max_iterations': 5000,
    'monte_carlo_min_runs': 100
}


# Pytest markers for test categories
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow
pytest.mark.api = pytest.mark.api
