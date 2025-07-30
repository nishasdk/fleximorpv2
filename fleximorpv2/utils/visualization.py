"""
Visualization utilities for FlexiMORPv2.

Helper functions for creating plots and charts used by both notebooks
and the web application.
"""

import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional, Union
import warnings

# Set up plotting style
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")


class VisualizationUtils:
    """
    Utility class for creating visualizations.
    
    Provides both matplotlib and plotly implementations for flexibility
    between notebook and web application usage.
    """
    
    def __init__(self, style: str = 'plotly'):
        """
        Initialize visualization utilities.
        
        Args:
            style: Plotting style ('plotly' or 'matplotlib')
        """
        self.style = style
        self.colors = {
            'wind': '#1f77b4',
            'solar': '#ff7f0e', 
            'wave': '#2ca02c',
            'primary': '#2E86C1',
            'secondary': '#F39C12',
            'success': '#27AE60',
            'warning': '#F1C40F',
            'danger': '#E74C3C'
        }
    
    def plot_technology_performance(self, 
                                  performance_data: Dict[str, Dict[str, float]],
                                  title: str = "Technology Performance Comparison") -> Union[plt.Figure, go.Figure]:
        """
        Plot technology performance comparison.
        
        Args:
            performance_data: Dictionary with technology performance metrics
            title: Plot title
            
        Returns:
            Figure object (matplotlib or plotly)
        """
        
        if self.style == 'plotly':
            return self._plot_tech_performance_plotly(performance_data, title)
        else:
            return self._plot_tech_performance_matplotlib(performance_data, title)
    
    def _plot_tech_performance_plotly(self, 
                                    performance_data: Dict[str, Dict[str, float]], 
                                    title: str) -> go.Figure:
        """Create technology performance plot using plotly."""
        
        technologies = list(performance_data.keys())
        metrics = ['capacity_factor', 'annual_energy_mwh', 'availability']
        
        fig = make_subplots(
            rows=1, cols=3,
            subplot_titles=['Capacity Factor', 'Annual Energy (MWh)', 'Availability'],
            specs=[[{"secondary_y": False}, {"secondary_y": False}, {"secondary_y": False}]]
        )
        
        for i, metric in enumerate(metrics):
            values = [performance_data[tech].get(metric, 0) for tech in technologies]
            colors_list = [self.colors.get(tech, f'rgb({np.random.randint(0,255)},{np.random.randint(0,255)},{np.random.randint(0,255)})') 
                          for tech in technologies]
            
            fig.add_trace(
                go.Bar(
                    x=technologies,
                    y=values,
                    name=metric.replace('_', ' ').title(),
                    marker_color=colors_list,
                    showlegend=False
                ),
                row=1, col=i+1
            )
        
        fig.update_layout(
            title=title,
            height=400,
            showlegend=False
        )
        
        return fig
    
    def _plot_tech_performance_matplotlib(self, 
                                        performance_data: Dict[str, Dict[str, float]], 
                                        title: str) -> plt.Figure:
        """Create technology performance plot using matplotlib."""
        
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        fig.suptitle(title)
        
        technologies = list(performance_data.keys())
        metrics = ['capacity_factor', 'annual_energy_mwh', 'availability']
        metric_titles = ['Capacity Factor', 'Annual Energy (MWh)', 'Availability']
        
        for i, (metric, metric_title) in enumerate(zip(metrics, metric_titles)):
            values = [performance_data[tech].get(metric, 0) for tech in technologies]
            colors_list = [self.colors.get(tech, 'gray') for tech in technologies]
            
            axes[i].bar(technologies, values, color=colors_list)
            axes[i].set_title(metric_title)
            axes[i].set_ylabel(metric_title)
            
            # Format y-axis based on metric
            if metric == 'capacity_factor' or metric == 'availability':
                axes[i].set_ylim(0, 1)
                axes[i].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1%}'))
        
        plt.tight_layout()
        return fig
    
    def plot_cost_breakdown(self, 
                           cost_data: Dict[str, float],
                           title: str = "Cost Breakdown") -> Union[plt.Figure, go.Figure]:
        """
        Plot cost breakdown pie chart.
        
        Args:
            cost_data: Dictionary with cost categories and values
            title: Plot title
            
        Returns:
            Figure object
        """
        
        if self.style == 'plotly':
            return self._plot_cost_breakdown_plotly(cost_data, title)
        else:
            return self._plot_cost_breakdown_matplotlib(cost_data, title)
    
    def _plot_cost_breakdown_plotly(self, 
                                   cost_data: Dict[str, float], 
                                   title: str) -> go.Figure:
        """Create cost breakdown pie chart using plotly."""
        
        labels = list(cost_data.keys())
        values = list(cost_data.values())
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.3,
            textinfo='label+percent',
            textposition='outside'
        )])
        
        fig.update_layout(
            title=title,
            annotations=[dict(text='CAPEX', x=0.5, y=0.5, font_size=20, showarrow=False)]
        )
        
        return fig
    
    def _plot_cost_breakdown_matplotlib(self, 
                                       cost_data: Dict[str, float], 
                                       title: str) -> plt.Figure:
        """Create cost breakdown pie chart using matplotlib."""
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        labels = list(cost_data.keys())
        values = list(cost_data.values())
        
        wedges, texts, autotexts = ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
        
        ax.set_title(title)
        plt.tight_layout()
        
        return fig
    
    def plot_financial_metrics(self, 
                              metrics: Dict[str, float],
                              title: str = "Financial Metrics") -> Union[plt.Figure, go.Figure]:
        """
        Plot key financial metrics.
        
        Args:
            metrics: Dictionary with financial metrics
            title: Plot title
            
        Returns:
            Figure object
        """
        
        if self.style == 'plotly':
            return self._plot_financial_metrics_plotly(metrics, title)
        else:
            return self._plot_financial_metrics_matplotlib(metrics, title)
    
    def _plot_financial_metrics_plotly(self, 
                                      metrics: Dict[str, float], 
                                      title: str) -> go.Figure:
        """Create financial metrics plot using plotly."""
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=['NPV (£M)', 'IRR (%)', 'LCOE (£/MWh)', 'Payback (Years)'],
            specs=[[{"type": "indicator"}, {"type": "indicator"}],
                   [{"type": "indicator"}, {"type": "indicator"}]]
        )
        
        # NPV
        npv_color = "green" if metrics.get('npv', 0) > 0 else "red"
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=metrics.get('npv', 0) / 1e6,
            title={'text': "NPV (£M)"},
            gauge={'bar': {'color': npv_color}},
        ), row=1, col=1)
        
        # IRR
        irr_color = "green" if metrics.get('irr', 0) > 0.1 else "red"
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=metrics.get('irr', 0) * 100,
            title={'text': "IRR (%)"},
            gauge={'bar': {'color': irr_color}},
        ), row=1, col=2)
        
        # LCOE
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=metrics.get('lcoe', 0),
            title={'text': "LCOE (£/MWh)"},
            gauge={'bar': {'color': "blue"}},
        ), row=2, col=1)
        
        # Payback Period
        payback_color = "green" if metrics.get('payback_period', float('inf')) < 10 else "red"
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=min(metrics.get('payback_period', 0), 20),  # Cap at 20 years for display
            title={'text': "Payback (Years)"},
            gauge={'bar': {'color': payback_color}},
        ), row=2, col=2)
        
        fig.update_layout(title=title, height=600)
        
        return fig
    
    def _plot_financial_metrics_matplotlib(self, 
                                          metrics: Dict[str, float], 
                                          title: str) -> plt.Figure:
        """Create financial metrics plot using matplotlib."""
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle(title)
        
        # NPV
        npv_value = metrics.get('npv', 0) / 1e6
        color = 'green' if npv_value > 0 else 'red'
        axes[0, 0].bar(['NPV'], [npv_value], color=color)
        axes[0, 0].set_ylabel('£ Million')
        axes[0, 0].set_title('Net Present Value')
        
        # IRR
        irr_value = metrics.get('irr', 0) * 100
        color = 'green' if irr_value > 10 else 'red'
        axes[0, 1].bar(['IRR'], [irr_value], color=color)
        axes[0, 1].set_ylabel('Percentage')
        axes[0, 1].set_title('Internal Rate of Return')
        
        # LCOE
        lcoe_value = metrics.get('lcoe', 0)
        axes[1, 0].bar(['LCOE'], [lcoe_value], color='blue')
        axes[1, 0].set_ylabel('£/MWh')
        axes[1, 0].set_title('Levelized Cost of Energy')
        
        # Payback Period
        payback_value = min(metrics.get('payback_period', 0), 20)
        color = 'green' if payback_value < 10 else 'red'
        axes[1, 1].bar(['Payback'], [payback_value], color=color)
        axes[1, 1].set_ylabel('Years')
        axes[1, 1].set_title('Payback Period')
        
        plt.tight_layout()
        return fig
    
    def plot_cash_flow_projection(self, 
                                 cash_flow_data: Dict[str, np.ndarray],
                                 title: str = "Cash Flow Projection") -> Union[plt.Figure, go.Figure]:
        """
        Plot cash flow projection over time.
        
        Args:
            cash_flow_data: Dictionary with cash flow arrays
            title: Plot title
            
        Returns:
            Figure object
        """
        
        if self.style == 'plotly':
            return self._plot_cash_flow_plotly(cash_flow_data, title)
        else:
            return self._plot_cash_flow_matplotlib(cash_flow_data, title)
    
    def _plot_cash_flow_plotly(self, 
                              cash_flow_data: Dict[str, np.ndarray], 
                              title: str) -> go.Figure:
        """Create cash flow plot using plotly."""
        
        years = cash_flow_data.get('years', np.arange(1, len(list(cash_flow_data.values())[0]) + 1))
        
        fig = go.Figure()
        
        # Revenue
        if 'revenues' in cash_flow_data:
            fig.add_trace(go.Scatter(
                x=years,
                y=cash_flow_data['revenues'],
                name='Revenue',
                line=dict(color='green'),
                fill='tonexty'
            ))
        
        # OPEX
        if 'opex' in cash_flow_data:
            fig.add_trace(go.Scatter(
                x=years,
                y=-cash_flow_data['opex'],  # Negative for costs
                name='OPEX',
                line=dict(color='red'),
                fill='tonexty'
            ))
        
        # Net Cash Flow
        if 'net_cash_flows' in cash_flow_data:
            fig.add_trace(go.Scatter(
                x=years,
                y=cash_flow_data['net_cash_flows'],
                name='Net Cash Flow',
                line=dict(color='blue', width=3)
            ))
        
        # Cumulative Cash Flow
        if 'cumulative_cash_flows' in cash_flow_data:
            fig.add_trace(go.Scatter(
                x=years,
                y=cash_flow_data['cumulative_cash_flows'],
                name='Cumulative Cash Flow',
                line=dict(color='purple', width=2, dash='dash')
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Year",
            yaxis_title="Cash Flow (£)",
            hovermode='x unified'
        )
        
        return fig
    
    def _plot_cash_flow_matplotlib(self, 
                                  cash_flow_data: Dict[str, np.ndarray], 
                                  title: str) -> plt.Figure:
        """Create cash flow plot using matplotlib."""
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        years = cash_flow_data.get('years', np.arange(1, len(list(cash_flow_data.values())[0]) + 1))
        
        # Revenue
        if 'revenues' in cash_flow_data:
            ax.fill_between(years, 0, cash_flow_data['revenues'], 
                           alpha=0.3, color='green', label='Revenue')
        
        # OPEX
        if 'opex' in cash_flow_data:
            ax.fill_between(years, 0, -cash_flow_data['opex'], 
                           alpha=0.3, color='red', label='OPEX')
        
        # Net Cash Flow
        if 'net_cash_flows' in cash_flow_data:
            ax.plot(years, cash_flow_data['net_cash_flows'], 
                   color='blue', linewidth=3, label='Net Cash Flow')
        
        # Cumulative Cash Flow
        if 'cumulative_cash_flows' in cash_flow_data:
            ax.plot(years, cash_flow_data['cumulative_cash_flows'], 
                   color='purple', linewidth=2, linestyle='--', label='Cumulative Cash Flow')
        
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        ax.set_title(title)
        ax.set_xlabel('Year')
        ax.set_ylabel('Cash Flow (£)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def plot_sensitivity_analysis(self, 
                                 sensitivity_data: Dict[str, Dict[str, float]],
                                 title: str = "Sensitivity Analysis") -> Union[plt.Figure, go.Figure]:
        """
        Plot sensitivity analysis results.
        
        Args:
            sensitivity_data: Dictionary with sensitivity results
            title: Plot title
            
        Returns:
            Figure object
        """
        
        if self.style == 'plotly':
            return self._plot_sensitivity_plotly(sensitivity_data, title)
        else:
            return self._plot_sensitivity_matplotlib(sensitivity_data, title)
    
    def _plot_sensitivity_plotly(self, 
                                sensitivity_data: Dict[str, Dict[str, float]], 
                                title: str) -> go.Figure:
        """Create sensitivity analysis plot using plotly."""
        
        parameters = list(sensitivity_data.keys())
        metrics = ['npv_sensitivity', 'irr_sensitivity', 'lcoe_sensitivity']
        metric_names = ['NPV', 'IRR', 'LCOE']
        
        fig = go.Figure()
        
        for i, (metric, metric_name) in enumerate(zip(metrics, metric_names)):
            values = [sensitivity_data[param].get(metric, 0) for param in parameters]
            
            fig.add_trace(go.Bar(
                name=metric_name,
                x=parameters,
                y=values,
                offsetgroup=i
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Parameters",
            yaxis_title="Sensitivity (% change in metric / % change in parameter)",
            barmode='group'
        )
        
        return fig
    
    def _plot_sensitivity_matplotlib(self, 
                                    sensitivity_data: Dict[str, Dict[str, float]], 
                                    title: str) -> plt.Figure:
        """Create sensitivity analysis plot using matplotlib."""
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        parameters = list(sensitivity_data.keys())
        metrics = ['npv_sensitivity', 'irr_sensitivity', 'lcoe_sensitivity']
        metric_names = ['NPV', 'IRR', 'LCOE']
        
        x = np.arange(len(parameters))
        width = 0.25
        
        for i, (metric, metric_name) in enumerate(zip(metrics, metric_names)):
            values = [sensitivity_data[param].get(metric, 0) for param in parameters]
            ax.bar(x + i * width, values, width, label=metric_name)
        
        ax.set_title(title)
        ax.set_xlabel('Parameters')
        ax.set_ylabel('Sensitivity')
        ax.set_xticks(x + width)
        ax.set_xticklabels(parameters, rotation=45)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def plot_monte_carlo_results(self, 
                                mc_results: Dict[str, Dict[str, Any]],
                                title: str = "Monte Carlo Analysis") -> Union[plt.Figure, go.Figure]:
        """
        Plot Monte Carlo analysis results.
        
        Args:
            mc_results: Dictionary with Monte Carlo results
            title: Plot title
            
        Returns:
            Figure object
        """
        
        if self.style == 'plotly':
            return self._plot_monte_carlo_plotly(mc_results, title)
        else:
            return self._plot_monte_carlo_matplotlib(mc_results, title)
    
    def _plot_monte_carlo_plotly(self, 
                                mc_results: Dict[str, Dict[str, Any]], 
                                title: str) -> go.Figure:
        """Create Monte Carlo results plot using plotly."""
        
        fig = make_subplots(
            rows=1, cols=3,
            subplot_titles=['NPV Distribution', 'IRR Distribution', 'LCOE Distribution']
        )
        
        metrics = ['npv', 'irr', 'lcoe']
        
        for i, metric in enumerate(metrics):
            if metric in mc_results:
                percentiles = mc_results[metric]['percentiles']
                
                # Create box plot representation
                fig.add_trace(go.Box(
                    y=[percentiles['p5'], percentiles['p25'], percentiles['p50'], 
                       percentiles['p75'], percentiles['p95']],
                    name=metric.upper(),
                    boxpoints='outliers'
                ), row=1, col=i+1)
        
        fig.update_layout(title=title, height=400)
        
        return fig
    
    def _plot_monte_carlo_matplotlib(self, 
                                    mc_results: Dict[str, Dict[str, Any]], 
                                    title: str) -> plt.Figure:
        """Create Monte Carlo results plot using matplotlib."""
        
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        fig.suptitle(title)
        
        metrics = ['npv', 'irr', 'lcoe']
        metric_titles = ['NPV Distribution', 'IRR Distribution', 'LCOE Distribution']
        
        for i, (metric, metric_title) in enumerate(zip(metrics, metric_titles)):
            if metric in mc_results:
                percentiles = mc_results[metric]['percentiles']
                
                # Create box plot
                box_data = [percentiles['p5'], percentiles['p25'], percentiles['p50'], 
                           percentiles['p75'], percentiles['p95']]
                
                axes[i].boxplot(box_data)
                axes[i].set_title(metric_title)
                axes[i].set_ylabel(metric.upper())
        
        plt.tight_layout()
        return fig
    
    def plot_optimization_convergence(self, 
                                     convergence_data: Dict[str, List[float]],
                                     title: str = "Optimization Convergence") -> Union[plt.Figure, go.Figure]:
        """
        Plot optimization convergence.
        
        Args:
            convergence_data: Dictionary with convergence data
            title: Plot title
            
        Returns:
            Figure object
        """
        
        if self.style == 'plotly':
            return self._plot_convergence_plotly(convergence_data, title)
        else:
            return self._plot_convergence_matplotlib(convergence_data, title)
    
    def _plot_convergence_plotly(self, 
                                convergence_data: Dict[str, List[float]], 
                                title: str) -> go.Figure:
        """Create convergence plot using plotly."""
        
        fig = go.Figure()
        
        iterations = convergence_data.get('iterations', list(range(len(convergence_data.get('objective_values', [])))))
        objective_values = convergence_data.get('objective_values', [])
        
        fig.add_trace(go.Scatter(
            x=iterations,
            y=objective_values,
            mode='lines+markers',
            name='Objective Function',
            line=dict(color='blue', width=2)
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Iteration",
            yaxis_title="Objective Function Value"
        )
        
        return fig
    
    def _plot_convergence_matplotlib(self, 
                                    convergence_data: Dict[str, List[float]], 
                                    title: str) -> plt.Figure:
        """Create convergence plot using matplotlib."""
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        iterations = convergence_data.get('iterations', list(range(len(convergence_data.get('objective_values', [])))))
        objective_values = convergence_data.get('objective_values', [])
        
        ax.plot(iterations, objective_values, 'b-o', linewidth=2, markersize=4)
        ax.set_title(title)
        ax.set_xlabel('Iteration')
        ax.set_ylabel('Objective Function Value')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def create_dashboard_layout(self, 
                               figures: List[Union[plt.Figure, go.Figure]],
                               titles: List[str]) -> go.Figure:
        """
        Create a dashboard layout with multiple figures.
        
        Args:
            figures: List of figure objects
            titles: List of titles for each figure
            
        Returns:
            Combined dashboard figure (plotly only)
        """
        
        if self.style != 'plotly':
            raise ValueError("Dashboard layout only supported for plotly style")
        
        # This is a simplified dashboard layout
        # In practice, you'd create a more sophisticated layout
        
        n_figures = len(figures)
        rows = (n_figures + 1) // 2
        
        fig = make_subplots(
            rows=rows, 
            cols=2,
            subplot_titles=titles,
            vertical_spacing=0.1,
            horizontal_spacing=0.1
        )
        
        for i, figure in enumerate(figures):
            row = (i // 2) + 1
            col = (i % 2) + 1
            
            # Extract traces from the figure and add to dashboard
            for trace in figure.data:
                fig.add_trace(trace, row=row, col=col)
        
        fig.update_layout(
            title="FlexiMORP Analysis Dashboard",
            height=300 * rows,
            showlegend=False
        )
        
        return fig
    
    def save_figure(self, 
                   figure: Union[plt.Figure, go.Figure], 
                   filepath: str, 
                   format: str = 'png'):
        """
        Save figure to file.
        
        Args:
            figure: Figure object to save
            filepath: Output file path
            format: File format ('png', 'pdf', 'html', 'svg')
        """
        
        if isinstance(figure, go.Figure):
            # Plotly figure
            if format.lower() == 'html':
                figure.write_html(filepath)
            elif format.lower() == 'pdf':
                figure.write_image(filepath, format='pdf')
            elif format.lower() == 'svg':
                figure.write_image(filepath, format='svg')
            else:
                figure.write_image(filepath, format='png')
        else:
            # Matplotlib figure
            figure.savefig(filepath, format=format, dpi=300, bbox_inches='tight')
        
        print(f"Figure saved to {filepath}")
