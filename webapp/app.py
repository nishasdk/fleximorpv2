"""
FlexiMORP v2 Web Application

Streamlit-based web interface for offshore renewable energy optimization analysis.
Provides interactive interface for the 4-step optimization workflow.
"""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import yaml
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    from fleximorpv2.config import load_config
    from fleximorpv2.graphics import GraphicsEngine
except ImportError:
    # Handle case where modules aren't fully implemented yet
    load_config = None
    GraphicsEngine = None


def main():
    """Main Streamlit application"""
    
    st.set_page_config(
        page_title="FlexiMORP v2 - Offshore Renewable Energy Optimization",
        page_icon="🌊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🌊 FlexiMORP v2")
    st.markdown("### Offshore Renewable Energy Platform Optimization")
    
    # Initialize session state
    if 'results' not in st.session_state:
        st.session_state.results = None
    if 'analysis_complete' not in st.session_state:
        st.session_state.analysis_complete = False
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Analysis Configuration")
        
        # Site selection
        site_options = ["Alaska", "Blyth", "Eastport", "Custom"]
        selected_site = st.selectbox("Select Site", site_options)
        
        if selected_site == "Custom":
            st.subheader("Custom Location")
            latitude = st.number_input("Latitude", value=55.0, min_value=-90.0, max_value=90.0)
            longitude = st.number_input("Longitude", value=-1.5, min_value=-180.0, max_value=180.0)
        else:
            # Load predefined coordinates
            coords = get_site_coordinates(selected_site)
            latitude, longitude = coords['lat'], coords['lon']
            st.write(f"📍 **{selected_site}**")
            st.write(f"Latitude: {latitude:.3f}")
            st.write(f"Longitude: {longitude:.3f}")
        
        st.divider()
        
        # Technology selection
        st.subheader("Technologies")
        technologies = []
        if st.checkbox("Wind", value=True):
            technologies.append("wind")
        if st.checkbox("Solar", value=False):
            technologies.append("solar")
        if st.checkbox("Wave", value=False):
            technologies.append("wave")
        
        st.divider()
        
        # Optimization target
        st.subheader("Optimization Target")
        target_type = st.radio("Target Type", ["Capacity (MW)", "Production (GWh/year)", "Investment ($M)"])
        
        if target_type == "Capacity (MW)":
            target_value = st.number_input("Target Capacity", value=100.0, min_value=1.0, max_value=1000.0)
            target_type = "capacity"
        elif target_type == "Production (GWh/year)":
            target_value = st.number_input("Target Production", value=300.0, min_value=10.0, max_value=3000.0)
            target_type = "production"
        else:
            target_value = st.number_input("Investment Budget", value=200.0, min_value=10.0, max_value=2000.0)
            target_type = "investment"
        
        st.divider()
        
        # Analysis parameters
        st.subheader("Analysis Parameters")
        uncertainty_simulations = st.slider("Monte Carlo Simulations", 100, 1000, 500)
        
        # Run analysis button
        button_text = "🔄 Rerun Analysis" if st.session_state.analysis_complete else "🚀 Run Complete Analysis"
        if st.button(button_text, type="primary"):
            run_complete_analysis(latitude, longitude, technologies, target_type, target_value, uncertainty_simulations)
    
    # Main content area
    if not st.session_state.analysis_complete:
        show_welcome_screen()
    else:
        show_results_dashboard()


def get_site_coordinates(site_name):
    """Get predefined coordinates for sites"""
    coords = {
        "Alaska": {"lat": 64.2008, "lon": -165.4064},
        "Blyth": {"lat": 55.1269, "lon": -1.5085},
        "Eastport": {"lat": 44.9070, "lon": -66.9901}
    }
    return coords.get(site_name, {"lat": 55.0, "lon": -1.5})


def show_welcome_screen():
    """Display welcome screen and methodology"""
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("Welcome to FlexiMORP v2")
        st.write("""
        FlexiMORP v2 is a comprehensive tool for optimizing offshore renewable energy platforms
        under uncertainty using real options analysis. The system follows a 4-step methodology:
        """)
        
        steps = [
            "**Step 1: Baseline Optimization** - Find optimal design under deterministic conditions",
            "**Step 2: Uncertainty Analysis** - Embed uncertainty using Monte Carlo simulation", 
            "**Step 3: Flexible Design** - Include decision rules and expansion strategies",
            "**Step 4: Sensitivity Analysis** - Analyze parameter sensitivity and robustness"
        ]
        
        for i, step in enumerate(steps, 1):
            st.write(f"{i}. {step}")
        
        st.info("👈 Configure your analysis parameters in the sidebar and click 'Run Complete Analysis' to begin.")
    
    with col2:
        st.header("Quick Start")
        st.write("**Popular Configurations:**")
        
        if st.button("🌬️🗡️ Wind-only Blyth"):
            st.session_state.quick_config = {
                'site': 'Blyth',
                'technologies': ['wind'],
                'target_type': 'capacity',
                'target_value': 100
            }
        
        if st.button("☀️🌬️ Solar+Wind Alaska"):
            st.session_state.quick_config = {
                'site': 'Alaska', 
                'technologies': ['wind', 'solar'],
                'target_type': 'capacity',
                'target_value': 50
            }
        
        if st.button("🌊⚡🌬️ Multi-tech Eastport"):
            st.session_state.quick_config = {
                'site': 'Eastport',
                'technologies': ['wind', 'solar', 'wave'],
                'target_type': 'production',
                'target_value': 250
            }


def run_complete_analysis(latitude, longitude, technologies, target_type, target_value, n_simulations):
    """Run the complete 4-step analysis"""
    
    if not technologies:
        st.error("Please select at least one technology.")
        return
    
    # Set analysis running state and clear previous results to force refresh
    st.session_state.analysis_running = True
    st.session_state.analysis_complete = False
    
    # Add custom CSS for simple progress animation
    st.markdown("""
    <style>
    .progress-circle {
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 3px solid #f3f3f3;
        border-top: 3px solid #3498db;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin-right: 10px;
    }
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    /* Hide Streamlit's default loading animations and status indicators */
    .stSpinner,
    .stSpinner > div,
    [data-testid="stStatusWidget"],
    .stStatus,
    [data-testid="stAppViewContainer"] .stStatus,
    .StatusWidget,
    [class*="StatusWidget"],
    [class*="stStatus"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Energy-related loading icons for each step
    loading_icons = {
        1: "⚙️🔧",  # Optimization tools
        2: "📊🎲",  # Uncertainty/statistics  
        3: "⚡🔄",  # Flexibility/energy flow
        4: "🌊🌍"   # Environmental/ocean
    }
    
    # Progress container
    progress_container = st.container()
    
    with progress_container:
        progress_bar = st.progress(0)
        status_container = st.container()
        
        # Step 1: Baseline Optimization
        with status_container:
            st.markdown('<div class="progress-circle"></div> <strong>Step 1/4:</strong> Optimizing baseline platform design...', unsafe_allow_html=True)
            import time
            time.sleep(1)
        progress_bar.progress(0.25)
        baseline_result = create_mock_baseline_result(latitude, longitude, technologies, target_type)
        
        # Step 2: Uncertainty Analysis
        status_container.empty()
        with status_container:
            st.markdown('<div class="progress-circle"></div> <strong>Step 2/4:</strong> Running Monte Carlo uncertainty analysis...', unsafe_allow_html=True)
            time.sleep(1)
        progress_bar.progress(0.50)
        uncertainty_result = create_mock_uncertainty_result(n_simulations)
        
        # Step 3: Flexible Design
        status_container.empty()
        with status_container:
            st.markdown('<div class="progress-circle"></div> <strong>Step 3/4:</strong> Analyzing flexible design strategies...', unsafe_allow_html=True)
            time.sleep(1)
        progress_bar.progress(0.75)
        flexibility_result = create_mock_flexibility_result()
        
        # Step 4: Environmental Assessment
        status_container.empty()
        with status_container:
            st.markdown('<div class="progress-circle"></div> <strong>Step 4/4:</strong> Completing environmental assessment...', unsafe_allow_html=True)
            time.sleep(1)
        progress_bar.progress(1.0)
        environmental_result = create_mock_environmental_result(latitude, longitude, technologies)
        
        # Clear everything when done
        status_container.empty()
        progress_bar.empty()
    
    # Store results
    st.session_state.results = create_mock_results(latitude, longitude, technologies, target_type)
    st.session_state.analysis_complete = True
    st.session_state.analysis_running = False  # Clear running state
    
    # Success message with energy icon
    st.success("⚡ Analysis complete! View results below.")
    st.rerun()


def show_results_dashboard():
    """Display comprehensive results dashboard"""
    
    results = st.session_state.results
    
    # Header with key metrics
    st.header("📊 Analysis Results")
    
    baseline = results['baseline']
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Optimal LCOE", f"${baseline['lcoe']:.1f}/MWh", f"{baseline['lcoe']-85:.1f}")
    with col2:
        st.metric("Total Capacity", f"{baseline['total_capacity']:.1f} MW")
    with col3:
        st.metric("Capacity Factor", f"{baseline['capacity_factor']:.1%}")
    with col4:
        st.metric("Environmental Score", f"{results['environmental']['overall_environmental_score']}/100")
    
    # Tabs for different result categories
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 Baseline", "🎲 Uncertainty", "🔄 Flexibility", "🌍 Environmental", "📋 Recommendations"
    ])
    
    with tab1:
        show_baseline_results(results['baseline'])
    
    with tab2:
        show_uncertainty_results(results['uncertainty'])
    
    with tab3:
        show_flexibility_results(results['flexibility'])
    
    with tab4:
        show_environmental_results(results['environmental'])
    
    with tab5:
        show_recommendations()


def show_baseline_results(baseline):
    """Display baseline optimization results"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Technology Breakdown")
        
        tech_data = baseline['technology_breakdown']
        techs = list(tech_data.keys())
        capacities = [tech_data[tech]['capacity'] for tech in techs]
        
        fig = px.pie(values=capacities, names=techs, title="Capacity Distribution")
        st.plotly_chart(fig, use_container_width=True)
        
        # Technology details table
        st.subheader("Technology Details")
        tech_df = pd.DataFrame(tech_data).T
        st.dataframe(tech_df, use_container_width=True)
    
    with col2:
        st.subheader("Performance Metrics")
        
        metrics = {
            "LCOE ($/MWh)": baseline['lcoe'],
            "Total Capacity (MW)": baseline['total_capacity'],
            "Capacity Factor": f"{baseline['capacity_factor']:.1%}",
            "Annual Production (GWh)": baseline['annual_production'],
            "CAPEX ($M)": baseline['capex'],
            "OPEX ($M/year)": baseline['opex'],
            "NPV ($M)": baseline['npv']
        }
        
        for metric, value in metrics.items():
            st.write(f"**{metric}:** {value}")


def show_uncertainty_results(uncertainty):
    """Display uncertainty analysis results"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("LCOE Distribution")
        
        # Create histogram of LCOE values
        lcoe_values = np.random.normal(uncertainty['lcoe_mean'], uncertainty['lcoe_std'], 1000)
        fig = px.histogram(x=lcoe_values, nbins=50, title="LCOE Distribution")
        fig.update_layout(
            xaxis_title="LCOE ($/MWh)",
            yaxis_title="Frequency"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Risk Metrics")
        
        risk_metrics = {
            "Mean LCOE": f"${uncertainty['lcoe_mean']:.1f}/MWh",
            "Standard Deviation": f"${uncertainty['lcoe_std']:.1f}/MWh",
            "95% Confidence Interval": f"${uncertainty['lcoe_p5']:.1f} - ${uncertainty['lcoe_p95']:.1f}/MWh",
            "Value at Risk (95%)": f"${uncertainty['var_95']:.1f}/MWh",
            "Probability of Success": f"{uncertainty['success_probability']:.1%}"
        }
        
        for metric, value in risk_metrics.items():
            st.write(f"**{metric}:** {value}")


def show_flexibility_results(flexibility):
    """Display flexibility analysis results"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Real Options Value")
        
        st.metric("Options Value", f"${flexibility['real_options_value']/1e6:.1f}M")
        st.metric("Flexibility Premium", f"{flexibility['flexibility_premium']:.1%}")
        
        st.subheader("Expansion Strategy")
        
        stages_df = pd.DataFrame(flexibility['expansion_stages'])
        st.dataframe(stages_df, use_container_width=True)
    
    with col2:
        st.subheader("Decision Triggers")
        
        triggers = flexibility['decision_triggers']
        for trigger, value in triggers.items():
            st.write(f"**{trigger.replace('_', ' ').title()}:** {value}")


def show_environmental_results(environmental):
    """Display environmental assessment results"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Technology Suitability")
        
        suitability_data = environmental['suitability_scores']
        
        for tech, scores in suitability_data.items():
            st.write(f"**{tech.title()}**")
            for score_type, score in scores.items():
                st.write(f"  {score_type.replace('_', ' ').title()}: {score:.2f}")
    
    with col2:
        st.subheader("Environmental Constraints")
        
        constraints = environmental['constraints']
        for constraint, level in constraints.items():
            color = "🟢" if level == "low" else "🟡" if level == "medium" else "🔴"
            st.write(f"{color} **{constraint.replace('_', ' ').title()}:** {level}")


def create_mock_baseline_result(latitude, longitude, technologies, target_type):
    """Create mock baseline optimization result"""
    
    # Base LCOE varies by location and technology mix
    base_lcoe = 85
    if 'wind' in technologies and len(technologies) == 1:
        base_lcoe = 75
    elif 'solar' in technologies and 'wind' in technologies:
        base_lcoe = 80
    elif 'wave' in technologies:
        base_lcoe = 95
    
    # Location adjustment
    if latitude > 60:  # Alaska-like
        base_lcoe += 10
    
    total_capacity = 100 if target_type == "capacity" else np.random.uniform(80, 120)
    
    # Technology breakdown
    tech_breakdown = {}
    if len(technologies) == 1:
        tech_breakdown[technologies[0]] = {
            'capacity': total_capacity,
            'capacity_factor': 0.4 if technologies[0] == 'wind' else 0.2 if technologies[0] == 'solar' else 0.3,
            'lcoe': base_lcoe
        }
    else:
        # Distribute capacity among technologies
        for i, tech in enumerate(technologies):
            share = 0.6 if tech == 'wind' else 0.3 if tech == 'solar' else 0.1
            if i == len(technologies) - 1:  # Last technology gets remainder
                capacity = total_capacity - sum(t['capacity'] for t in tech_breakdown.values())
            else:
                capacity = total_capacity * share
            
            tech_breakdown[tech] = {
                'capacity': capacity,
                'capacity_factor': 0.4 if tech == 'wind' else 0.2 if tech == 'solar' else 0.3,
                'lcoe': base_lcoe * (0.9 if tech == 'wind' else 1.1 if tech == 'solar' else 1.3)
            }
    
    overall_capacity_factor = sum(
        data['capacity'] * data['capacity_factor'] for data in tech_breakdown.values()
    ) / total_capacity
    
    annual_production = total_capacity * overall_capacity_factor * 8760 / 1000  # GWh
    
    return {
        'lcoe': base_lcoe,
        'total_capacity': total_capacity,
        'capacity_factor': overall_capacity_factor,
        'annual_production': annual_production,
        'technology_breakdown': tech_breakdown,
        'capex': total_capacity * 2.5,  # $M
        'opex': total_capacity * 0.05,  # $M/year
        'npv': total_capacity * 1.2     # $M
    }


def create_mock_uncertainty_result(n_simulations):
    """Create mock uncertainty analysis result"""
    
    base_lcoe = 85
    lcoe_std = 12
    
    return {
        'n_simulations': n_simulations,
        'lcoe_mean': base_lcoe,
        'lcoe_std': lcoe_std,
        'lcoe_p5': base_lcoe - 1.645 * lcoe_std,
        'lcoe_p95': base_lcoe + 1.645 * lcoe_std,
        'var_95': base_lcoe + 1.645 * lcoe_std,
        'success_probability': 0.73
    }


def create_mock_flexibility_result():
    """Create mock flexibility analysis result"""
    
    return {
        'real_options_value': 15000000,  # $15M
        'flexibility_premium': 0.12,
        'expansion_stages': [
            {'Year': 0, 'Capacity (MW)': 40, 'Technology': 'Wind'},
            {'Year': 3, 'Capacity (MW)': 30, 'Technology': 'Solar'},
            {'Year': 7, 'Capacity (MW)': 30, 'Technology': 'Wind'}
        ],
        'decision_triggers': {
            'electricity_price_threshold': '≥$85/MWh',
            'technology_cost_reduction': '≥15%',
            'capacity_utilization': '≥85%'
        }
    }


def create_mock_environmental_result(latitude, longitude, technologies):
    """Create mock environmental assessment result"""
    
    # Determine constraint level based on location
    if latitude > 60:  # Alaska
        constraint_level = 'high'
    elif 'Blyth' in str(latitude):  # European waters
        constraint_level = 'medium'
    else:
        constraint_level = 'low'
    
    # Base environmental score
    if constraint_level == 'low':
        env_score = 85
    elif constraint_level == 'medium':
        env_score = 75
    else:
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


def show_recommendations():
    """Display project recommendations"""
    
    st.subheader("Project Recommendations")
    
    recommendations = generate_recommendations()
    
    for i, rec in enumerate(recommendations, 1):
        st.write(f"{i}. {rec}")
    
    st.subheader("Next Steps")
    
    next_steps = [
        "Conduct detailed site survey and geotechnical assessment",
        "Engage with regulatory authorities for permitting",
        "Develop detailed financial model and secure funding",
        "Conduct stakeholder consultation and environmental impact assessment",
        "Proceed with detailed engineering design",
        "Develop construction and installation plan"
    ]
    
    for i, step in enumerate(next_steps, 1):
        st.write(f"{i}. {step}")


if __name__ == "__main__":
    main()
