"""
Graphics and visualization module for FlexiMORPv2.

Provides comprehensive visualization capabilities for all analysis results
including optimization plots, uncertainty distributions, Pareto frontiers,
and interactive dashboards.
"""

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import seaborn as sns
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from .config import SiteConfig


class GraphicsEngine:
    """
    Comprehensive graphics engine for FlexiMORP v2 visualizations.
    
    Handles all plotting and visualization needs across the analysis workflow.
    """
    
    def __init__(self, config: Optional[SiteConfig] = None):
        """Initialize graphics engine."""
        self.config = config
        
        # Color scheme for renewable energy themes
        self.colors = {
            'wind': '#3498DB',      # Blue
            'solar': '#F39C12',     # Orange
            'wave': '#16A085',      # Teal
            'baseline': '#2ECC71',  # Green
            'uncertainty': '#E74C3C', # Red
            'flexibility': '#9B59B6'  # Purple
        }
        
        # Set plotting style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
    
    def plot_optimization_results(self, results) -> go.Figure:
        """Create optimization results visualization."""
        
        # Technology breakdown pie chart
        tech_data = results.technology_capacities
        
        fig = go.Figure(data=[go.Pie(
            labels=list(tech_data.keys()),
            values=list(tech_data.values()),
            hole=0.3,
            marker_colors=[self.colors.get(tech, '#95A5A6') for tech in tech_data.keys()]
        )])
        
        fig.update_layout(
            title="Optimal Technology Mix",
            annotations=[dict(text='Capacity', x=0.5, y=0.5, font_size=20, showarrow=False)]
        )
        
        return fig
    
    def plot_uncertainty_results(self, results) -> go.Figure:
        """Create uncertainty analysis visualization."""
        
        # Monte Carlo simulation results
        n_sims = results.get('n_simulations', 1000)
        lcoe_mean = results.get('lcoe_mean', 85)
        lcoe_std = results.get('lcoe_std', 12)
        
        # Generate sample data
        lcoe_values = np.random.normal(lcoe_mean, lcoe_std, n_sims)
        
        fig = go.Figure()
        
        # Histogram
        fig.add_trace(go.Histogram(
            x=lcoe_values,
            nbinsx=50,
            name='LCOE Distribution',
            opacity=0.7,
            marker_color=self.colors['uncertainty']
        ))
        
        # Add mean line
        fig.add_vline(x=lcoe_mean, line_dash="dash", line_color="black", 
                     annotation_text=f"Mean: ${lcoe_mean:.1f}/MWh")
        
        fig.update_layout(
            title="LCOE Uncertainty Distribution",
            xaxis_title="LCOE ($/MWh)",
            yaxis_title="Frequency",
            showlegend=False
        )
        
        return fig
    
    def plot_flexibility_results(self, results) -> go.Figure:
        """Create flexibility analysis visualization."""
        
        # Expansion timeline
        stages = results.get('expansion_stages', [])
        
        years = [stage['Year'] for stage in stages]
        capacities = [stage['Capacity (MW)'] for stage in stages]
        technologies = [stage['Technology'] for stage in stages]
        
        fig = go.Figure()
        
        # Cumulative capacity over time
        cumulative_capacity = np.cumsum(capacities)
        
        fig.add_trace(go.Scatter(
            x=years,
            y=cumulative_capacity,
            mode='lines+markers',
            name='Cumulative Capacity',
            line=dict(color=self.colors['flexibility'], width=3),
            marker=dict(size=10)
        ))
        
        # Add annotations for each stage
        for i, (year, cap, tech) in enumerate(zip(years, capacities, technologies)):
            fig.add_annotation(
                x=year,
                y=cumulative_capacity[i],
                text=f"{tech}<br>+{cap} MW",
                showarrow=True,
                arrowhead=2,
                arrowcolor=self.colors['flexibility']
            )
        
        fig.update_layout(
            title="Flexible Expansion Strategy",
            xaxis_title="Year",
            yaxis_title="Cumulative Capacity (MW)"
        )
        
        return fig
    
    def plot_pareto_frontier(self, results, objectives: List[str]) -> go.Figure:
        """Create Pareto frontier visualization."""
        
        pareto_solutions = results.pareto_frontier
        objective_values = results.objective_values
        
        if len(objectives) >= 2:
            # 2D or 3D Pareto plot
            obj1_vals = objective_values[:, 0]
            obj2_vals = objective_values[:, 1]
            
            fig = go.Figure()
            
            if len(objectives) == 2:
                # 2D scatter plot
                fig.add_trace(go.Scatter(
                    x=obj1_vals,
                    y=obj2_vals,
                    mode='markers',
                    marker=dict(
                        size=8,
                        color=range(len(obj1_vals)),
                        colorscale='Viridis',
                        showscale=True
                    ),
                    name='Pareto Solutions'
                ))
                
                fig.update_layout(
                    title="Pareto Frontier",
                    xaxis_title=objectives[0].replace('_', ' ').title(),
                    yaxis_title=objectives[1].replace('_', ' ').title()
                )
            
            elif len(objectives) >= 3:
                # 3D scatter plot
                obj3_vals = objective_values[:, 2]
                
                fig.add_trace(go.Scatter3d(
                    x=obj1_vals,
                    y=obj2_vals,
                    z=obj3_vals,
                    mode='markers',
                    marker=dict(
                        size=5,
                        color=range(len(obj1_vals)),
                        colorscale='Viridis',
                        showscale=True
                    ),
                    name='Pareto Solutions'
                ))
                
                fig.update_layout(
                    title="3D Pareto Frontier",
                    scene=dict(
                        xaxis_title=objectives[0].replace('_', ' ').title(),
                        yaxis_title=objectives[1].replace('_', ' ').title(),
                        zaxis_title=objectives[2].replace('_', ' ').title()
                    )
                )
        
        return fig
    
    def plot_sensitivity_results(self, results) -> go.Figure:
        """Create sensitivity analysis visualization."""
        
        # Parameter rankings
        rankings = results.parameter_rankings
        
        params = [r[0] for r in rankings[:10]]  # Top 10 parameters
        sensitivities = [abs(r[1]) for r in rankings[:10]]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            y=params,
            x=sensitivities,
            orientation='h',
            marker_color=self.colors['baseline']
        ))
        
        fig.update_layout(
            title="Parameter Sensitivity Rankings",
            xaxis_title="Sensitivity Index",
            yaxis_title="Parameters",
            yaxis=dict(categoryorder='total ascending')
        )
        
        return fig
    def plot_comparison_analysis(self, baseline_results, uncertainty_results, flexible_results) -> Figure:
        """Create comprehensive comparison plot."""
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # LCOE comparison
        analysis_types = ['Baseline', 'Uncertainty', 'Flexibility']
        lcoe_values = [
            baseline_results.financial_metrics.get('lcoe', 85),
            uncertainty_results.get('lcoe_mean', 85),
            85 * 0.95  # Assume flexibility reduces LCOE by 5%
        ]
        colors = [self.colors['baseline'], self.colors['uncertainty'], self.colors['flexibility']]
        
        axes[0, 0].bar(analysis_types, lcoe_values, color=colors)
        axes[0, 0].set_title('LCOE Comparison')
        axes[0, 0].set_ylabel('LCOE ($/MWh)')
        
        # NPV comparison
        npv_values = [
            baseline_results.financial_metrics.get('npv', 50e6) / 1e6,
            50,  # Baseline NPV in millions
            55   # Flexibility premium
        ]
        
        axes[0, 1].bar(analysis_types, npv_values, color=colors)
        axes[0, 1].set_title('NPV Comparison')
        axes[0, 1].set_ylabel('NPV (£M)')
        
        # Risk vs Return scatter
        risk_values = [0.1, uncertainty_results.get('lcoe_std', 12) / 100, 0.08]
        return_values = npv_values
        
        for i, (risk, ret, label) in enumerate(zip(risk_values, return_values, analysis_types)):
            axes[1, 0].scatter(risk, ret, c=colors[i], s=100, label=label)
            axes[1, 0].annotate(label, (risk, ret), xytext=(5, 5), textcoords='offset points')
        
        axes[1, 0].set_xlabel('Risk Score')
        axes[1, 0].set_ylabel('NPV (£M)')
        axes[1, 0].set_title('Risk vs Return')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # Technology mix
        tech_capacities = baseline_results.technology_capacities
        tech_colors = [self.colors.get(tech, '#95A5A6') for tech in tech_capacities.keys()]
        
        axes[1, 1].bar(tech_capacities.keys(), tech_capacities.values(), color=tech_colors)
        axes[1, 1].set_title('Technology Mix (Baseline)')
        axes[1, 1].set_ylabel('Capacity (MW)')
        
        plt.tight_layout()
        return fig
    
    def create_comprehensive_visualization(self, base_design: Dict[str, Any], 
                                          uncertainty_summary: Dict[str, Any],
                                          flexibility_summary: Dict[str, Any], 
                                          ranked_sensitivities: List[Tuple[str, float]]) -> Figure:
        """
        Create comprehensive results visualization with all analysis results.
        
        Args:
            base_design: Dictionary with baseline design results
            uncertainty_summary: Dictionary with uncertainty analysis results
            flexibility_summary: Dictionary with flexibility analysis results
            ranked_sensitivities: List of tuples (parameter, sensitivity)
            
        Returns:
            Matplotlib Figure object with comprehensive visualization
        """
        
        print(f"\n{'='*60}")
        print("📈 CREATING COMPREHENSIVE VISUALIZATION")
        print('='*60)

        # Create comprehensive results visualization
        fig = plt.figure(figsize=(20, 16))
        gs = fig.add_gridspec(4, 4, hspace=0.3, wspace=0.3)

        # 1. NPV Distribution from uncertainty analysis
        ax1 = fig.add_subplot(gs[0, 0])
        np.random.seed(42)
        mean_npv = uncertainty_summary.get('mean_npv', 50e6)
        std_dev = max(abs(mean_npv) * 0.3, 1e6)  # ensure it's always positive and non-zero
        npv_samples = np.random.normal(loc=mean_npv, scale=std_dev, size=1000)
        ax1.hist(npv_samples/1e6, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
        ax1.axvline(mean_npv/1e6, color='red', linestyle='--', 
                   label=f'Mean: £{mean_npv/1e6:.1f}M')
        ax1.axvline(0, color='orange', linestyle=':', label='Break-even')
        ax1.set_xlabel('NPV (£M)')
        ax1.set_ylabel('Frequency')
        ax1.set_title('NPV Distribution\n(Monte Carlo)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 2. LCOE Box Plot
        ax2 = fig.add_subplot(gs[0, 1])
        lcoe_scenarios = ['Base Case', 'Mean (Uncertainty)', '95% VaR']
        base_lcoe = base_design.get('lcoe', 85)
        mean_lcoe = uncertainty_summary.get('mean_lcoe', base_lcoe)
        var_95_lcoe = uncertainty_summary.get('lcoe_var_95', mean_lcoe * 1.2)
        
        lcoe_values = [base_lcoe, mean_lcoe, var_95_lcoe]
        colors = ['green', 'orange', 'red']
        bars = ax2.bar(lcoe_scenarios, lcoe_values, color=colors, alpha=0.7, edgecolor='black')
        ax2.set_ylabel('LCOE (£/MWh)')
        ax2.set_title('LCOE Comparison\nAcross Scenarios')
        ax2.tick_params(axis='x', rotation=45)
        for bar, value in zip(bars, lcoe_values):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                     f'£{value:.0f}', ha='center', va='bottom', fontweight='bold')
        ax2.grid(True, alpha=0.3)

        # 3. Tornado Chart (Sensitivity Analysis)
        ax3 = fig.add_subplot(gs[0, 2])
        if ranked_sensitivities:
            top_5_params = [p for p, _ in ranked_sensitivities[:5]]
            sensitivities = [s for _, s in ranked_sensitivities[:5]]
            colors_tornado = ['red' if s < 0 else 'green' for s in sensitivities]
            bars = ax3.barh(range(len(top_5_params)), [abs(s) for s in sensitivities], 
                           color=colors_tornado, alpha=0.7)
            ax3.set_yticks(range(len(top_5_params)))
            ax3.set_yticklabels([p.replace('_', '\n').title() for p in top_5_params])
            ax3.set_xlabel('Sensitivity (Elasticity)')
            ax3.set_title('Tornado Chart\nTop 5 Sensitivities')
        else:
            ax3.text(0.5, 0.5, 'No Sensitivity\nData Available', 
                    ha='center', va='center', transform=ax3.transAxes)
            ax3.set_title('Tornado Chart\nTop 5 Sensitivities')
        ax3.grid(True, alpha=0.3)

        # 4. Flexibility Value Breakdown
        ax4 = fig.add_subplot(gs[0, 3])
        flex_options = ['Base NPV', 'Expansion', 'Tech Upgrade', 'Seasonal Shutdown']
        base_npv_val = mean_npv/1e6
        expansion_val = flexibility_summary.get('expansion_value', 5e6)/1e6
        upgrade_val = flexibility_summary.get('upgrade_value', 2e6)/1e6
        shutdown_val = flexibility_summary.get('shutdown_value', 1.5e6)/1e6
        
        flex_values = [base_npv_val, expansion_val, upgrade_val, shutdown_val]
        cumulative_values = np.cumsum([0] + flex_values)
        
        for i, (option, value) in enumerate(zip(flex_options, flex_values)):
            color = 'lightblue' if i == 0 else 'lightgreen'
            ax4.bar(i, value, bottom=cumulative_values[i], color=color, 
                   alpha=0.8, edgecolor='black', label=option)

        ax4.set_xticks(range(len(flex_options)))
        ax4.set_xticklabels([opt.replace(' ', '\n') for opt in flex_options], rotation=0)
        ax4.set_ylabel('Value (£M)')
        ax4.set_title('Flexibility Value\nWaterfall Chart')
        ax4.grid(True, alpha=0.3)

        # 5. Risk-Return Profile
        ax5 = fig.add_subplot(gs[1, 0])
        scenarios = ['Conservative', 'Base Case', 'Optimistic', 'With Flexibility']
        flex_premium = flexibility_summary.get('flexibility_premium', 5e6)
        returns = [15, mean_npv/1e6, 35, (mean_npv + flex_premium)/1e6]
        prob_negative = uncertainty_summary.get('prob_negative_npv', 0.25)
        risks = [0.15, prob_negative, 0.45, prob_negative * 0.7]
        colors_risk = ['green', 'blue', 'orange', 'purple']

        for i, (scenario, ret, risk, color) in enumerate(zip(scenarios, returns, risks, colors_risk)):
            ax5.scatter(risk, ret, s=200, c=color, alpha=0.7, edgecolors='black')
            ax5.annotate(scenario, (risk, ret), xytext=(5, 5), textcoords='offset points', 
                        fontsize=9, ha='left')

        ax5.set_xlabel('Risk (Probability of Loss)')
        ax5.set_ylabel('Expected Return (£M NPV)')
        ax5.set_title('Risk-Return Profile\nScenario Comparison')
        ax5.grid(True, alpha=0.3)

        # 6. Technology Performance Comparison
        ax6 = fig.add_subplot(gs[1, 1])
        tech_labels = ['Wind', 'Solar', 'Combined']
        wind_cf = base_design.get('wind_cf', base_design.get('wind_capacity_factor', 0.45))
        solar_cf = base_design.get('solar_cf', base_design.get('solar_capacity_factor', 0.18))
        combined_cf = base_design.get('capacity_factor', 0.40)

        tech_cfs = [wind_cf, solar_cf, combined_cf]
        colors_tech = ['lightblue', 'yellow', 'green']
        bars = ax6.bar(tech_labels, tech_cfs, color=colors_tech, alpha=0.7, edgecolor='black')
        ax6.set_ylabel('Capacity Factor')
        ax6.set_title('Technology Performance\nCapacity Factors')
        ax6.set_ylim(0, 0.6)
        for bar, cf in zip(bars, tech_cfs):
            ax6.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                     f'{cf:.1%}', ha='center', va='bottom', fontweight='bold')
        ax6.grid(True, alpha=0.3)

        # 7. Arctic Considerations (customize for your site)
        ax7 = fig.add_subplot(gs[1, 2])
        site_name = self.config.name if self.config else "Site"
        arctic_factors = ['Base\nConditions', 'Weather\nPenalty', 'Environmental\nImpact', 'Logistics\nPremium']
        arctic_impacts = [1.0, 0.95, 0.93, 1.25]  # Normalized impacts
        colors_arctic = ['blue', 'lightblue', 'white', 'red']
        bars = ax7.bar(arctic_factors, arctic_impacts, color=colors_arctic, 
                      alpha=0.7, edgecolor='black')
        ax7.axhline(1.0, color='green', linestyle='--', alpha=0.7, label='Baseline')
        ax7.set_ylabel('Performance/Cost Factor')
        ax7.set_title(f'{site_name} Impact Factors\nSite Considerations')
        ax7.legend()
        ax7.grid(True, alpha=0.3)

        # 8. Economic Metrics Spider Chart
        ax8 = fig.add_subplot(gs[1, 3], projection='polar')
        metrics = ['NPV\nScore', 'LCOE\nScore', 'IRR\nScore', 'Payback\nScore', 'Risk\nScore']
        n_metrics = len(metrics)

        # Normalize scores (0-1, higher = better)
        npv_score = max(0, min(1, (mean_npv + 20e6) / 60e6))
        lcoe_score = max(0, min(1, (150 - mean_lcoe) / 80))
        irr_score = 0.75  # Mock IRR score
        payback_score = 0.6  # Mock payback score
        risk_score = max(0, min(1, (0.5 - prob_negative) / 0.5))

        scores = [npv_score, lcoe_score, irr_score, payback_score, risk_score]
        theta = np.linspace(0, 2*np.pi, n_metrics, endpoint=False)
        theta = np.concatenate((theta, [theta[0]]))
        scores_plot = scores + [scores[0]]

        ax8.plot(theta, scores_plot, 'o-', linewidth=2, color='green', alpha=0.8)
        ax8.fill(theta, scores_plot, alpha=0.2, color='green')
        ax8.set_xticks(theta[:-1])
        ax8.set_xticklabels(metrics)
        ax8.set_ylim(0, 1)
        ax8.set_title('Economic Performance\nSpider Chart', pad=20)
        ax8.grid(True)

        # 9. Cash Flow Timeline
        ax9 = fig.add_subplot(gs[2, :2])
        years = np.arange(0, 26)
        capex = base_design.get('total_capex', base_design.get('capex', 250e6))
        annual_revenue = base_design.get('annual_revenue', 50e6)
        annual_opex = base_design.get('annual_opex', 15e6)
        annual_cf = annual_revenue - annual_opex

        cash_flows = [-capex] + [annual_cf] * 25
        cumulative_cf = np.cumsum(cash_flows)

        ax9.bar(years, np.array(cash_flows)/1e6, alpha=0.6, color='lightcoral', 
               label='Annual Cash Flow')
        ax9.plot(years, cumulative_cf/1e6, color='green', linewidth=3, 
                marker='o', label='Cumulative Cash Flow')
        ax9.axhline(0, color='black', linestyle='--', alpha=0.5)
        ax9.set_xlabel('Year')
        ax9.set_ylabel('Cash Flow (£M)')
        ax9.set_title('Project Cash Flow Timeline')
        ax9.legend()
        ax9.grid(True, alpha=0.3)

        # 10. Monte Carlo Results Summary
        ax10 = fig.add_subplot(gs[3, 0])
        mc_metrics = ['Mean NPV', 'P90 NPV', 'P10 NPV', 'VaR 5%']
        p90_npv = uncertainty_summary.get('p90_npv', mean_npv * 1.3)
        p10_npv = uncertainty_summary.get('p10_npv', mean_npv * 0.6)
        var_5_npv = uncertainty_summary.get('npv_var_5', -10e6)
        
        mc_values = [mean_npv/1e6, p90_npv/1e6, p10_npv/1e6, var_5_npv/1e6]
        colors_mc = ['blue', 'green', 'orange', 'red']
        bars = ax10.bar(mc_metrics, mc_values, color=colors_mc, alpha=0.7, edgecolor='black')
        ax10.set_ylabel('NPV (£M)')
        ax10.set_title('Monte Carlo Results\nNPV Statistics')
        ax10.tick_params(axis='x', rotation=45)
        for bar, value in zip(bars, mc_values):
            ax10.text(bar.get_x() + bar.get_width()/2, 
                     bar.get_height() + (2 if value > 0 else -4),
                     f'£{value:.1f}M', ha='center', 
                     va='bottom' if value > 0 else 'top', fontweight='bold')
        ax10.grid(True, alpha=0.3)

        # 11. Flexibility Options Exercise Probability
        ax11 = fig.add_subplot(gs[3, 1])
        flex_labels = ['Expansion', 'Tech\nUpgrade', 'Seasonal\nShutdown']
        expansion_prob = flexibility_summary.get('expansion_exercise_prob', 0.35)
        upgrade_prob = flexibility_summary.get('upgrade_exercise_prob', 0.22)
        shutdown_prob = flexibility_summary.get('shutdown_exercise_prob', 0.18)
        
        exercise_probs = [expansion_prob, upgrade_prob, shutdown_prob]

        bars = ax11.bar(flex_labels, exercise_probs, color='lightgreen', 
                       alpha=0.7, edgecolor='black')
        ax11.set_ylabel('Exercise Probability')
        ax11.set_title('Flexibility Options\nExercise Probability')
        ax11.set_ylim(0, 0.5)
        for bar, prob in zip(bars, exercise_probs):
            ax11.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                     f'{prob:.1%}', ha='center', va='bottom', fontweight='bold')
        ax11.grid(True, alpha=0.3)

        # 12. Break-even Analysis
        ax12 = fig.add_subplot(gs[3, 2:])
        price_range = np.linspace(80, 160, 50)
        breakeven_npvs = []
        
        base_electricity_price = uncertainty_summary.get('mean_electricity_price', 
                                                       base_design.get('electricity_price', 120))
        annual_energy = base_design.get('annual_energy', 350000)  # MWh
        
        discount_rate = base_design.get('discount_rate', 0.08)
        project_life = base_design.get('project_lifetime', 25)

        for price in price_range:
            # Simple NPV calculation for different electricity prices
            annual_revenue_calc = annual_energy * price / 1000  # Convert to £M
            annual_cf_calc = annual_revenue_calc - annual_opex/1e6  # £M
            
            # Simple NPV calculation
            pv_cash_flows = sum([annual_cf_calc / (1 + discount_rate)**year 
                               for year in range(1, project_life + 1)])
            npv_calc = pv_cash_flows - capex/1e6
            breakeven_npvs.append(npv_calc)

        ax12.plot(price_range, breakeven_npvs, linewidth=3, color='blue', label='NPV vs Price')
        ax12.axhline(0, color='red', linestyle='--', alpha=0.7, label='Break-even')
        ax12.axvline(base_electricity_price, color='green', linestyle=':', 
                    alpha=0.7, label=f'Base Price: £{base_electricity_price}/MWh')

        # Find approximate break-even price
        breakeven_npvs_arr = np.array(breakeven_npvs)
        if len(breakeven_npvs_arr) > 0:
            breakeven_idx = np.argmin(np.abs(breakeven_npvs_arr))
            breakeven_price = price_range[breakeven_idx]
            ax12.axvline(breakeven_price, color='orange', linestyle='-.', alpha=0.7, 
                        label=f'Break-even: £{breakeven_price:.0f}/MWh')

        ax12.set_xlabel('Electricity Price (£/MWh)')
        ax12.set_ylabel('NPV (£M)')
        ax12.set_title('Break-even Analysis - Electricity Price vs NPV')
        ax12.legend()
        ax12.grid(True, alpha=0.3)

        # Add site-specific title
        site_title = f"{site_name} Offshore Renewable Project - Comprehensive Analysis Results"
        plt.suptitle(site_title, fontsize=20, fontweight='bold')
        plt.tight_layout()
        
        print("✅ Comprehensive visualization completed")
        return fig
        
    def save_figure(self, fig, filepath: 'str | Path', **kwargs):
        """Save figure to file."""
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        if isinstance(fig, go.Figure):
            # Plotly figure
            fig.write_html(str(filepath.with_suffix('.html')))
            fig.write_image(str(filepath.with_suffix('.png')), **kwargs)
        else:
            # Matplotlib figure
            fig.savefig(filepath, dpi=300, bbox_inches='tight', **kwargs)
        
        print(f"Figure saved to: {filepath}")


def main():
    """Example usage of graphics engine."""
    # This would typically be called from notebooks or webapp
    pass


if __name__ == "__main__":
    main()
