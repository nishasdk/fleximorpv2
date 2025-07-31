"""
Test suite for Multi-Criteria Decision Analysis (MCDA) functionality.
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch

from fleximorpv2.sensitivity_analysis import SensitivityAnalysis
from fleximorpv2.config import load_site_config


class TestMCDAAnalysis:
    """Test MCDA analysis functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Create sample MCDA data
        np.random.seed(42)
        self.n_alternatives = 20
        
        self.mcda_data = pd.DataFrame({
            'alternative_id': [f'Alt_{i+1}' for i in range(self.n_alternatives)],
            'lcoe': np.random.uniform(70, 120, self.n_alternatives),
            'emissions_reduction': np.random.uniform(10000, 50000, self.n_alternatives),
            'social_acceptance': np.random.uniform(60, 95, self.n_alternatives),
            'aquaculture_synergy': np.random.uniform(40, 85, self.n_alternatives)
        })
        
        self.criteria_names = ['lcoe', 'emissions_reduction', 'social_acceptance', 'aquaculture_synergy']
        self.criteria_types = ['min', 'max', 'max', 'max']  # min=cost, max=benefit
    
    def test_entropy_weight_calculation(self):
        """Test entropy method for criteria weighting."""
        weights = self._calculate_entropy_weights()
        
        # Weights should sum to 1
        assert abs(sum(weights.values()) - 1.0) < 1e-6
        
        # All weights should be positive
        assert all(w > 0 for w in weights.values())
        
        # Check that we have weights for all criteria
        assert len(weights) == len(self.criteria_names)
        for criterion in self.criteria_names:
            assert criterion in weights
    
    def test_topsis_score_calculation(self):
        """Test TOPSIS scoring method."""
        weights = {'lcoe': 0.3, 'emissions_reduction': 0.3, 'social_acceptance': 0.2, 'aquaculture_synergy': 0.2}
        topsis_scores = self._calculate_topsis_scores(weights)
        
        # Should have scores for all alternatives
        assert len(topsis_scores) == self.n_alternatives
        
        # Scores should be between 0 and 1
        assert all(0 <= score <= 1 for score in topsis_scores)
        
        # Best solution should have highest score
        best_idx = np.argmax(topsis_scores)
        assert topsis_scores[best_idx] == max(topsis_scores)
    
    def test_criteria_normalization(self):
        """Test criteria normalization for MCDA."""
        normalized_data = self._normalize_criteria()
        
        # Check that normalized values are between 0 and 1
        for criterion in self.criteria_names:
            values = normalized_data[criterion]
            assert values.min() >= 0
            assert values.max() <= 1
            
            # For cost criteria (min type), lower original values should have higher normalized values
            if criterion == 'lcoe':
                original_min_idx = self.mcda_data[criterion].idxmin()
                assert normalized_data.loc[original_min_idx, criterion] == 1.0
    
    def test_ranking_consistency(self):
        """Test that ranking is consistent across methods."""
        weights = self._calculate_entropy_weights()
        topsis_scores = self._calculate_topsis_scores(weights)
        
        # Create ranking
        ranking = pd.DataFrame({
            'alternative_id': self.mcda_data['alternative_id'],
            'topsis_score': topsis_scores
        })
        ranking['rank'] = ranking['topsis_score'].rank(ascending=False)
        
        # Top-ranked solution should have highest TOPSIS score
        top_solution = ranking[ranking['rank'] == 1].iloc[0]
        assert top_solution['topsis_score'] == ranking['topsis_score'].max()
    
    # Helper methods for MCDA calculations
    def _calculate_entropy_weights(self):
        """Calculate criteria weights using entropy method."""
        normalized_data = self._normalize_criteria()
        
        entropies = []
        n_alternatives = len(normalized_data)
        
        for criterion in self.criteria_names:
            p_values = normalized_data[criterion] / normalized_data[criterion].sum()
            p_values = np.where(p_values == 0, 1e-10, p_values)
            
            entropy_j = -np.sum(p_values * np.log(p_values)) / np.log(n_alternatives)
            entropies.append(entropy_j)
        
        weights = np.array([(1 - e) for e in entropies])
        weights = weights / weights.sum()
        
        return dict(zip(self.criteria_names, weights))
    
    def _normalize_criteria(self):
        """Normalize criteria using min-max scaling."""
        normalized = self.mcda_data.copy()
        
        for i, criterion in enumerate(self.criteria_names):
            values = self.mcda_data[criterion].values
            
            if self.criteria_types[i] == 'min':  # Cost criteria
                normalized[criterion] = (values.max() - values) / (values.max() - values.min())
            else:  # Benefit criteria
                normalized[criterion] = (values - values.min()) / (values.max() - values.min())
        
        return normalized
    
    def _calculate_topsis_scores(self, weights):
        """Calculate TOPSIS scores for ranking alternatives."""
        normalized_data = self._normalize_criteria()
        weighted_data = normalized_data[self.criteria_names].multiply(list(weights.values()), axis=1)
        
        ideal_solution = weighted_data.max()
        anti_ideal_solution = weighted_data.min()
        
        distances_to_ideal = []
        distances_to_anti_ideal = []
        
        for idx, row in weighted_data.iterrows():
            d_ideal = np.sqrt(((row - ideal_solution) ** 2).sum())
            d_anti_ideal = np.sqrt(((row - anti_ideal_solution) ** 2).sum())
            
            distances_to_ideal.append(d_ideal)
            distances_to_anti_ideal.append(d_anti_ideal)
        
        distances_to_ideal = np.array(distances_to_ideal)
        distances_to_anti_ideal = np.array(distances_to_anti_ideal)
        
        topsis_scores = distances_to_anti_ideal / (distances_to_ideal + distances_to_anti_ideal)
        
        return topsis_scores


class TestTrioOptimization:
    """Test TRIO optimization functionality."""
    
    def setup_method(self):
        """Setup TRIO test fixtures."""
        self.mock_config = Mock()
        self.mock_config.coordinates = (60.5, -151.0)
        self.mock_config.get_enabled_technologies.return_value = ['wind', 'solar']
    
    def test_location_feasibility_check(self):
        """Test location feasibility constraints."""
        # Mock TRIO optimizer
        trio_optimizer = self._create_mock_trio_optimizer()
        
        # Test feasible location
        feasible_lat, feasible_lon = 60.2, -150.5
        assert trio_optimizer._is_feasible_location(feasible_lat, feasible_lon)
        
        # Test infeasible location (too far)
        infeasible_lat, infeasible_lon = 65.0, -140.0
        assert not trio_optimizer._is_feasible_location(infeasible_lat, infeasible_lon)
    
    def test_trio_solution_evaluation(self):
        """Test TRIO solution evaluation across criteria."""
        trio_optimizer = self._create_mock_trio_optimizer()
        
        location = (60.2, -150.5)
        wind_capacity = 80
        solar_capacity = 40
        
        solution = trio_optimizer.evaluate_solution(location, wind_capacity, solar_capacity)
        
        # Check solution structure
        assert 'location' in solution
        assert 'design' in solution
        assert 'technical_performance' in solution
        assert 'criteria_scores' in solution
        
        # Check criteria scores
        criteria = solution['criteria_scores']
        assert 'lcoe' in criteria
        assert 'emissions_reduction' in criteria
        assert 'social_acceptance' in criteria
        assert 'aquaculture_synergy' in criteria
        
        # Validate score ranges
        assert criteria['lcoe'] > 0
        assert criteria['emissions_reduction'] > 0 
        assert 0 <= criteria['social_acceptance'] <= 100
        assert 0 <= criteria['aquaculture_synergy'] <= 100
    
    def test_capacity_combinations(self):
        """Test different capacity combinations."""
        trio_optimizer = self._create_mock_trio_optimizer()
        location = (60.2, -150.5)
        
        capacity_combinations = [
            (50, 25),   # Wind-dominant
            (40, 40),   # Balanced
            (30, 50),   # Solar-dominant
        ]
        
        solutions = []
        for wind_cap, solar_cap in capacity_combinations:
            solution = trio_optimizer.evaluate_solution(location, wind_cap, solar_cap)
            solutions.append(solution)
        
        # Check that different combinations produce different results
        lcoe_values = [sol['criteria_scores']['lcoe'] for sol in solutions]
        assert len(set(lcoe_values)) > 1  # Should have different LCOE values
    
    def _create_mock_trio_optimizer(self):
        """Create mock TRIO optimizer for testing."""
        class MockTrioOptimizer:
            def __init__(self, config):
                self.config = config
            
            def _is_feasible_location(self, lat, lon):
                community_lat, community_lon = self.config.coordinates
                distance = np.sqrt((lat - community_lat)**2 + (lon - community_lon)**2)
                return distance < 2.0
            
            def evaluate_solution(self, location, wind_capacity, solar_capacity):
                # Mock evaluation
                lat, lon = location
                
                design = {
                    'wind_capacity': wind_capacity,
                    'solar_capacity': solar_capacity,
                    'platform_area': (wind_capacity + solar_capacity) * 50,
                    'water_depth': 40,
                    'distance_to_shore': abs(lat - self.config.coordinates[0]) * 111
                }
                
                # Mock technical performance
                tech_performance = {
                    'annual_energy': (wind_capacity * 0.4 + solar_capacity * 0.2) * 8760,
                    'capacity_factor': 0.35,
                    'wind_energy': wind_capacity * 0.4 * 8760,
                    'solar_energy': solar_capacity * 0.2 * 8760
                }
                
                # Mock criteria scores
                criteria_scores = {
                    'lcoe': 85.0 + np.random.normal(0, 10),
                    'emissions_reduction': tech_performance['annual_energy'] * 0.8,
                    'social_acceptance': 75.0 + np.random.normal(0, 10),
                    'aquaculture_synergy': 60.0 + np.random.normal(0, 15)
                }
                
                return {
                    'location': location,
                    'design': design,
                    'technical_performance': tech_performance,
                    'criteria_scores': criteria_scores
                }
        
        return MockTrioOptimizer(self.mock_config)


class TestAlaskaSpecificConstraints:
    """Test Alaska-specific constraints and considerations."""
    
    def test_arctic_technology_constraints(self):
        """Test Arctic-specific technology constraints."""
        # Wave energy should be disabled due to sea ice
        mock_config = Mock()
        mock_config.get_enabled_technologies.return_value = ['wind', 'solar']
        
        enabled_techs = mock_config.get_enabled_technologies()
        assert 'wind' in enabled_techs
        assert 'solar' in enabled_techs
        assert 'wave' not in enabled_techs
    
    def test_social_acceptance_factors(self):
        """Test social acceptance calculation for Alaska."""
        # Mock calculation that considers indigenous community factors
        def calculate_social_acceptance(distance_to_community, location_sensitivity):
            base_score = max(0, 100 - distance_to_community * 2)
            if distance_to_community < 5:  # Too close penalty
                base_score *= 0.7
            
            sensitivity_penalty = location_sensitivity * 10
            consultation_score = 90 - sensitivity_penalty
            
            return (base_score + consultation_score) / 2
        
        # Test different scenarios
        score1 = calculate_social_acceptance(10, 0.5)  # Moderate distance, low sensitivity
        score2 = calculate_social_acceptance(3, 0.8)   # Close distance, high sensitivity
        score3 = calculate_social_acceptance(25, 0.2)  # Far distance, low sensitivity
        
        assert 0 <= score1 <= 100
        assert 0 <= score2 <= 100
        assert 0 <= score3 <= 100
        
        # Close + high sensitivity should have lower score than moderate distance + low sensitivity
        assert score2 < score1
    
    def test_aquaculture_synergy_calculation(self):
        """Test aquaculture synergy scoring for Alaska."""
        def calculate_aquaculture_synergy(water_depth, platform_area, latitude):
            # Depth suitability (30-60m optimal)
            depth_score = max(0, 100 - abs(water_depth - 45) * 2)
            
            # Platform size benefit
            size_score = min(100, platform_area / 1000)
            
            # Environmental suitability (optimal around 60°N)
            env_score = max(0, 80 - abs(latitude - 60) * 5)
            
            return (depth_score + size_score + env_score) / 3
        
        # Test optimal conditions
        optimal_score = calculate_aquaculture_synergy(45, 5000, 60.0)
        
        # Test suboptimal conditions
        suboptimal_score = calculate_aquaculture_synergy(80, 2000, 62.0)
        
        assert optimal_score > suboptimal_score
        assert 0 <= optimal_score <= 100
        assert 0 <= suboptimal_score <= 100


def test_mcda_integration_with_trio():
    """Test integration between TRIO optimization and MCDA analysis."""
    # Generate mock TRIO solutions
    np.random.seed(42)
    n_solutions = 30
    
    trio_solutions = []
    for i in range(n_solutions):
        solution = {
            'solution_id': f'TRIO_{i+1}',
            'location': (np.random.uniform(59, 62), np.random.uniform(-155, -148)),
            'wind_capacity': np.random.randint(30, 120),
            'solar_capacity': np.random.randint(20, 80),
            'lcoe': np.random.uniform(75, 110),
            'emissions_reduction': np.random.uniform(15000, 45000),
            'social_acceptance': np.random.uniform(55, 90),
            'aquaculture_synergy': np.random.uniform(35, 80)
        }
        trio_solutions.append(solution)
    
    # Convert to DataFrame
    trio_df = pd.DataFrame(trio_solutions)
    
    # Apply MCDA analysis
    mcda_analyzer = TestMCDAAnalysis()
    mcda_analyzer.mcda_data = trio_df
    mcda_analyzer.criteria_names = ['lcoe', 'emissions_reduction', 'social_acceptance', 'aquaculture_synergy']
    mcda_analyzer.criteria_types = ['min', 'max', 'max', 'max']
    
    # Calculate weights and scores
    weights = mcda_analyzer._calculate_entropy_weights()
    topsis_scores = mcda_analyzer._calculate_topsis_scores(weights)
    
    # Add TOPSIS scores to dataframe
    trio_df['topsis_score'] = topsis_scores
    trio_df['rank'] = trio_df['topsis_score'].rank(ascending=False)
    
    # Validate integration results
    assert len(trio_df) == n_solutions
    assert 'topsis_score' in trio_df.columns
    assert 'rank' in trio_df.columns
    
    # Best solution should have rank 1
    best_solution = trio_df[trio_df['rank'] == 1].iloc[0]
    assert best_solution['topsis_score'] == trio_df['topsis_score'].max()
    
    # All scores should be valid
    assert all(0 <= score <= 1 for score in trio_df['topsis_score'])
    assert all(1 <= rank <= n_solutions for rank in trio_df['rank'])


if __name__ == "__main__":
    pytest.main([__file__])
