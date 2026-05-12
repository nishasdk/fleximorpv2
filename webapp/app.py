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
    from fleximorpv2.config import load_config, create_default_config, _parse_config
    from fleximorpv2.baseline_optimization import BaselineOptimization
    from fleximorpv2.uncertainty_analysis import UncertaintyAnalysis
    from fleximorpv2.flexible_design import FlexibleDesign
    from fleximorpv2.graphics import GraphicsEngine
    _REAL_MODULES_AVAILABLE = True
except ImportError:
    load_config = None
    GraphicsEngine = None
    _REAL_MODULES_AVAILABLE = False


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
            run_complete_analysis(latitude, longitude, technologies, target_type, target_value, uncertainty_simulations, site_name=selected_site)
    
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


def _baseline_to_webapp_dict(results, config) -> dict:
    """Convert BaselineResults to webapp display dict."""
    tech_breakdown = {}
    for tech, capacity in results.technology_capacities.items():
        if capacity > 0 and tech in config.technologies:
            tech_breakdown[tech] = {
                'capacity': round(capacity, 2),
                'capacity_factor': config.technologies[tech].capacity_factor,
                'lcoe': results.financial_metrics.get('lcoe', 0),
            }
    annual_energy_mwh = results.technical_metrics.get('annual_energy', 0)
    return {
        'lcoe': results.financial_metrics.get('lcoe', 0),
        'total_capacity': results.technical_metrics.get('total_capacity', 0),
        'capacity_factor': results.technical_metrics.get('capacity_factor', 0),
        'annual_production': annual_energy_mwh / 1000,  # MWh → GWh
        'technology_breakdown': tech_breakdown,
        'capex': results.financial_metrics.get('capex', 0) / 1e6,
        'opex': results.financial_metrics.get('opex', 0) / 1e6,
        'npv': results.financial_metrics.get('npv', 0) / 1e6,
    }


def _uncertainty_to_webapp_dict(results) -> dict:
    """Convert UncertaintyResults to webapp display dict."""
    lcoe_mean = results.mean_performance.get('lcoe', 85)
    lcoe_std = results.std_performance.get('lcoe', 12)
    percs = results.percentiles.get('lcoe', {})
    return {
        'n_simulations': results.uncertainty_info.get('monte_carlo_runs', 0),
        'lcoe_mean': lcoe_mean,
        'lcoe_std': lcoe_std,
        'lcoe_p5': percs.get('p5', lcoe_mean - 1.645 * lcoe_std),
        'lcoe_p95': percs.get('p95', lcoe_mean + 1.645 * lcoe_std),
        'var_95': results.risk_metrics.get('lcoe_var_95', lcoe_mean + 1.645 * lcoe_std),
        'success_probability': 1.0 - results.risk_metrics.get('prob_negative_npv', 0.27),
    }


def _flexibility_to_webapp_dict(results) -> dict:
    """Convert FlexibleResults to webapp display dict."""
    flat = results.to_flat_dict()
    staging = flat.get('optimal_staging', [])
    triggers = flat.get('expansion_triggers', {})

    expansion_stages = [
        {
            'Year': s.get('year', 0),
            'Capacity (MW)': s.get('capacity_mw', 0),
            'Technology': ', '.join(s.get('technologies', ['wind'])),
        }
        for s in staging
    ]
    if not expansion_stages:
        expansion_stages = [
            {'Year': 0, 'Capacity (MW)': 40, 'Technology': 'Wind'},
            {'Year': 3, 'Capacity (MW)': 30, 'Technology': 'Solar'},
        ]

    decision_triggers = {
        'electricity_price_threshold': f"≥${triggers.get('electricity_price_threshold', 110):.0f}/MWh",
        'technology_cost_reduction': f"≥{triggers.get('technology_cost_reduction', 0.15) * 100:.0f}%",
        'capacity_utilization': f"≥{triggers.get('capacity_utilization', 0.85) * 100:.0f}%",
    }
    return {
        'real_options_value': flat.get('real_options_value', 0),
        'flexibility_premium': flat.get('flexibility_premium', 0),
        'expansion_stages': expansion_stages,
        'decision_triggers': decision_triggers,
    }


_SITE_NAME_MAP = {'alaska': 'alaska', 'blyth': 'blyth', 'eastport': 'eastport'}


def _run_real_analysis(site_name, latitude, longitude, technologies, target_type, target_value):
    """Run real FlexiMORP analysis. Raises on failure so caller can fall back to mock."""
    site_key = site_name.lower() if site_name.lower() in _SITE_NAME_MAP else None

    if site_key:
        config = load_config(site_key)
    else:
        raw = create_default_config(
            f"Custom_{latitude:.1f}_{longitude:.1f}", [latitude, longitude]
        )
        for tech in ['wind', 'solar', 'wave']:
            raw['technologies'][tech]['enabled'] = tech in technologies
        config = _parse_config(raw)

    # Cap MC runs for webapp responsiveness
    config.uncertainty['monte_carlo_runs'] = min(
        config.uncertainty.get('monte_carlo_runs', 1000), 50
    )

    # Step 1: Baseline optimisation (scipy is faster than differential_evolution for webapp)
    baseline_opt = BaselineOptimization(config)
    max_cap = config.optimization.get('constraints', {}).get('max_total_capacity', 500)
    if target_type == 'capacity':
        avg_cf = 0.35
        production_kwh = target_value * avg_cf * 8760 * 1000
    elif target_type == 'production':
        production_kwh = target_value * 1e6
    else:
        production_kwh = max_cap * 0.35 * 8760 * 1000 * 0.5
    baseline_results = baseline_opt.optimize('production', production_kwh, method='scipy')

    # Step 2: Uncertainty analysis
    uncertainty_analyzer = UncertaintyAnalysis(config)
    uncertainty_results = uncertainty_analyzer.analyze_uncertainty(
        baseline_design=baseline_results.optimal_design, reoptimize=False
    )

    # Step 3: Flexible design
    flex_analyzer = FlexibleDesign(config)
    flex_results = flex_analyzer.analyze_flexibility(baseline_results.optimal_design)

    return (
        _baseline_to_webapp_dict(baseline_results, config),
        _uncertainty_to_webapp_dict(uncertainty_results),
        _flexibility_to_webapp_dict(flex_results),
    )


def run_complete_analysis(latitude, longitude, technologies, target_type, target_value, n_simulations, site_name="Custom"):
    """Run the complete 4-step analysis"""

    if not technologies:
        st.error("Please select at least one technology.")
        return

    st.session_state.analysis_running = True
    st.session_state.analysis_complete = False

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
    .stSpinner, .stSpinner > div,
    [data-testid="stStatusWidget"], .stStatus,
    [data-testid="stAppViewContainer"] .stStatus,
    .StatusWidget, [class*="StatusWidget"], [class*="stStatus"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    progress_container = st.container()
    with progress_container:
        progress_bar = st.progress(0)
        status_container = st.container()

        baseline_result = None
        uncertainty_result = None
        flexibility_result = None
        used_real_analysis = False

        if _REAL_MODULES_AVAILABLE:
            with status_container:
                st.markdown(
                    '<div class="progress-circle"></div>'
                    ' <strong>Steps 1–3/4:</strong> Running real optimization & uncertainty analysis...',
                    unsafe_allow_html=True,
                )
            try:
                baseline_result, uncertainty_result, flexibility_result = _run_real_analysis(
                    site_name, latitude, longitude, technologies, target_type, target_value
                )
                used_real_analysis = True
            except Exception as exc:
                st.warning(f"Real analysis unavailable ({type(exc).__name__}: {exc}). Using demonstration data.")

        if baseline_result is None:
            baseline_result = create_mock_baseline_result(latitude, longitude, technologies, target_type)
            uncertainty_result = create_mock_uncertainty_result(n_simulations)
            flexibility_result = create_mock_flexibility_result()

        progress_bar.progress(0.75)

        # Step 4: Environmental assessment (always demonstration — environmental.py is incomplete)
        status_container.empty()
        with status_container:
            st.markdown(
                '<div class="progress-circle"></div>'
                ' <strong>Step 4/4:</strong> Completing environmental assessment...',
                unsafe_allow_html=True,
            )
        environmental_result = create_mock_environmental_result(latitude, longitude, technologies)
        progress_bar.progress(1.0)

        status_container.empty()
        progress_bar.empty()

    st.session_state.results = {
        'baseline': baseline_result,
        'uncertainty': uncertainty_result,
        'flexibility': flexibility_result,
        'environmental': environmental_result,
    }
    st.session_state.analysis_complete = True
    st.session_state.analysis_running = False

    if used_real_analysis:
        st.success("⚡ Analysis complete using real FlexiMORP optimization!")
    else:
        st.success("⚡ Analysis complete! (demonstration data)")
    st.rerun()


def show_results_dashboard():
    """Display comprehensive results dashboard"""

    results = st.session_state.results
    baseline = results['baseline']

    st.header("📊 Analysis Results")

    # ── Top key metrics ──────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Optimal LCOE", f"${baseline['lcoe']:.1f}/MWh", f"{baseline['lcoe']-85:.1f}")
    with col2:
        st.metric("Total Capacity", f"{baseline['total_capacity']:.1f} MW")
    with col3:
        st.metric("Capacity Factor", f"{baseline['capacity_factor']:.1%}")
    with col4:
        st.metric("Environmental Score", f"{results['environmental']['overall_environmental_score']}/100")

    st.divider()

    # ── Deployment Rollout Plan ───────────────────────────────────────────────
    show_rollout_plan(baseline, results['flexibility'])

    st.divider()

    # ── Detailed tabs ─────────────────────────────────────────────────────────
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


def show_rollout_plan(baseline: dict, flexibility: dict):
    """Deployment timeline shown on the results home page."""

    stages = flexibility.get('expansion_stages', [])
    if not stages:
        return

    st.subheader("Deployment Rollout Plan")

    # Build enriched timeline with cumulative totals
    sorted_stages = sorted(stages, key=lambda s: s.get('Year', 0))
    cumulative = 0.0
    plan_rows = []
    for i, stage in enumerate(sorted_stages):
        year = stage.get('Year', 0)
        cap = float(stage.get('Capacity (MW)', 0))
        tech = str(stage.get('Technology', 'Mixed')).title()
        cumulative += cap
        plan_rows.append({
            'Phase': f"Phase {i + 1}",
            'Year': year,
            'Technology': tech,
            'New Capacity (MW)': cap,
            'Cumulative Total (MW)': round(cumulative, 1),
        })
    plan_df = pd.DataFrame(plan_rows)

    # Colour palette per technology keyword
    _TECH_COLOURS = {
        'Wind':  '#2196F3',
        'Solar': '#FF9800',
        'Wave':  '#00BCD4',
        'Hydro': '#4CAF50',
        'Mixed': '#9C27B0',
    }

    def _tech_colour(name: str) -> str:
        for key, colour in _TECH_COLOURS.items():
            if key.lower() in name.lower():
                return colour
        return '#78909C'

    chart_col, table_col = st.columns([3, 2])

    with chart_col:
        fig = go.Figure()

        # One bar trace per unique technology label
        for tech in plan_df['Technology'].unique():
            rows = plan_df[plan_df['Technology'] == tech]
            fig.add_trace(go.Bar(
                x=rows['Year'],
                y=rows['New Capacity (MW)'],
                name=tech,
                marker_color=_tech_colour(tech),
                text=[f"+{v:.0f} MW" for v in rows['New Capacity (MW)']],
                textposition='inside',
                textfont_color='white',
            ))

        # Cumulative total as a secondary line on the right axis
        fig.add_trace(go.Scatter(
            x=plan_df['Year'],
            y=plan_df['Cumulative Total (MW)'],
            mode='lines+markers+text',
            name='Cumulative Total',
            line=dict(color='#212121', width=2),
            marker=dict(size=9, symbol='diamond'),
            text=[f"{v:.0f} MW" for v in plan_df['Cumulative Total (MW)']],
            textposition='top center',
            textfont=dict(size=11, color='#212121'),
            yaxis='y2',
        ))

        fig.update_layout(
            barmode='stack',
            xaxis=dict(
                title='Project Year',
                tickmode='array',
                tickvals=plan_df['Year'].tolist(),
                ticktext=[f"Year {y}" for y in plan_df['Year']],
            ),
            yaxis=dict(title='New Capacity Added (MW)', showgrid=False),
            yaxis2=dict(
                title='Cumulative Total (MW)',
                overlaying='y',
                side='right',
                showgrid=True,
                gridcolor='rgba(0,0,0,0.07)',
            ),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            height=360,
            margin=dict(t=40, b=40, l=10, r=10),
            plot_bgcolor='white',
        )

        st.plotly_chart(fig, use_container_width=True)

    with table_col:
        st.markdown("**Phase-by-phase breakdown**")

        # Styled table
        display_df = plan_df[['Phase', 'Year', 'Technology', 'New Capacity (MW)', 'Cumulative Total (MW)']].copy()
        try:
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'New Capacity (MW)': st.column_config.NumberColumn(format="%.0f MW"),
                    'Cumulative Total (MW)': st.column_config.NumberColumn(format="%.0f MW"),
                },
            )
        except Exception:
            st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.markdown("---")

        # Summary stats below the table
        final_cap = plan_df['Cumulative Total (MW)'].iloc[-1]
        duration = int(plan_df['Year'].max()) - int(plan_df['Year'].min())
        n_phases = len(plan_df)

        s1, s2, s3 = st.columns(3)
        s1.metric("Final Capacity", f"{final_cap:.0f} MW")
        s2.metric("Duration", f"{duration} yrs")
        s3.metric("Phases", str(n_phases))

        # Technology mix in final fleet
        tech_totals = plan_df.groupby('Technology')['New Capacity (MW)'].sum()
        st.markdown("**Final technology mix**")
        for tech, cap in tech_totals.items():
            pct = cap / final_cap * 100
            st.progress(int(pct), text=f"{tech}: {cap:.0f} MW ({pct:.0f}%)")


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
    if latitude > 60:  # Arctic / Alaska
        constraint_level = 'high'
    elif 50 < latitude <= 60:  # Northern European waters (Blyth etc.)
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
