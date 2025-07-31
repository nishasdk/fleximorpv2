        env_score = 85
    
    suitability_scores = {}
    for tech in technologies:
        suitability_scores[tech] = {
            'resource_score': 0.8 if tech == 'wind' else 0.6 if tech == 'solar' else 0.7,
            'constraint_score': 0.9 - (0.2 if constraint_level == 'high' else 0.1 if constraint_level == 'medium' else 0),
            'conflict_score': 0.8,
            'climate_score': 0.75
        }
    
    return {
        'overall_environmental_score': env_score,
        'suitability_scores': suitability_scores,
        'constraints': {
            'protected_areas': constraint_level,
            'marine_habitats': 'medium',
            'fishing_conflicts': 'low' if 'Alaska' in str(latitude) else 'medium',
            'stakeholder_conflicts': constraint_level
        }
    }


def create_mock_results(latitude, longitude, technologies, target_type):
    """Create complete mock results set"""
    
    return {
        'baseline': create_mock_baseline_result(latitude, longitude, technologies, target_type),
        'uncertainty': create_mock_uncertainty_result(500),
        'flexibility': create_mock_flexibility_result(),
        'environmental': create_mock_environmental_result(latitude, longitude, technologies)
    }


def generate_recommendations():
    """Generate project recommendations based on results"""
    
    baseline = st.session_state.results.get('baseline', {})
    env = st.session_state.results.get('environmental', {})
    
    recommendations = []
    
    # LCOE-based recommendations
    lcoe = baseline.get('lcoe', 85)
    if lcoe < 80:
        recommendations.append("Excellent economic performance - proceed with detailed feasibility study")
    elif lcoe < 100:
        recommendations.append("Good economic potential - consider cost optimization strategies")
    else:
        recommendations.append("High LCOE - evaluate alternative technologies or site selection")
    
    # Environmental recommendations
    env_score = env.get('overall_environmental_score', 75)
    if env_score < 70:
        recommendations.append("Environmental concerns identified - develop comprehensive mitigation plan")
    
    # Technology mix recommendations
    tech_breakdown = baseline.get('technology_breakdown', {})
    if 'wind' in tech_breakdown and tech_breakdown['wind']['capacity'] > 30:
        recommendations.append("Wind-dominated design - ensure robust foundation design for extreme weather")
    
    # Default recommendations
    if not recommendations:
        recommendations = [
            "Proceed with detailed environmental impact assessment",
            "Engage with local stakeholders early in the process",
            "Consider phased development approach to manage risks",
            "Develop comprehensive monitoring and maintenance plan"
        ]
    
    return recommendations


if __name__ == "__main__":
    main()
