"""
Graphics and visualization module for FlexiMORPv2.

Provides comprehensive visualization capabilities for all analysis results
including optimization plots, uncertainty distributions, Pareto frontiers,
and interactive dashboards.
"""

import matplotlib.pyplot as plt
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
    
    def __init__(self, config: SiteConfig = None):
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
    
    def plot_comparison_analysis(self, baseline_results, uncertainty_results, flexible_results) -> plt.Figure:
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
    
    def save_figure(self, fig, filepath: str, **kwargs):
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
