"""
Financial calculator utilities for FlexiMORPv2.

Comprehensive financial analysis tools including NPV, IRR, LCOE calculations,
cash flow modeling, and financial risk assessment.
"""

import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
import math

from ..config import SiteConfig


@dataclass
class CashFlowProjection:
    """Cash flow projection for the project."""
    years: np.ndarray
    revenues: np.ndarray
    opex: np.ndarray
    net_cash_flows: np.ndarray
    cumulative_cash_flows: np.ndarray
    capex: float


@dataclass
class FinancialMetrics:
    """Complete set of financial metrics."""
    npv: float
    irr: float
    lcoe: float
    payback_period: float
    discounted_payback_period: float
    profitability_index: float
    return_on_investment: float


class FinancialCalculator:
    """
    Comprehensive financial calculator for offshore renewable projects.
    
    Handles various financial calculations including cash flow projections,
    economic metrics, and risk assessments.
    """
    
    def __init__(self, config: SiteConfig):
        """
        Initialize financial calculator.
        
        Args:
            config: Site configuration object
        """
        self.config = config
        
        # Financial parameters
        self.financial_params = {
            'corporate_tax_rate': self.config.economic.get('tax_rate', 0.25),
            'depreciation_period': 10,  # years for tax depreciation
            'working_capital_rate': 0.05,  # 5% of annual revenue
            'salvage_value_rate': 0.1,  # 10% of original CAPEX
            'debt_to_equity_ratio': 0.7,  # 70% debt financing
            'debt_interest_rate': 0.05,  # 5% interest on debt
            'equity_return_requirement': 0.12  # 12% required return on equity
        }
    
    def calculate_metrics(self, 
                         capex: float,
                         opex: float,
                         revenue: float,
                         project_life: int,
                         **kwargs) -> Dict[str, float]:
        """
        Calculate comprehensive financial metrics.
        
        Args:
            capex: Total capital expenditure
            opex: Annual operating expenditure
            revenue: Annual revenue
            project_life: Project lifetime in years
            **kwargs: Additional parameters, including required annual_energy
                in MWh/year for LCOE calculation
            
        Returns:
            Dictionary with financial metrics
        """
        discount_rate = self.config.economic.get('discount_rate', 0.08)
        
        # Generate cash flow projection
        cash_flow = self.project_cash_flow_projection(
            capex, opex, revenue, project_life, **kwargs
        )
        
        # Calculate core metrics
        npv = self.calculate_npv(cash_flow.net_cash_flows, discount_rate, capex)
        irr = self.calculate_irr(cash_flow.net_cash_flows, capex)
        
        # LCOE calculation. Energy cannot be inferred reliably from total
        # revenue because revenue may include subsidies or capacity payments.
        annual_energy = kwargs.get('annual_energy')
        if annual_energy is None:
            raise ValueError("annual_energy is required to calculate LCOE")
        lcoe = self.calculate_lcoe(capex, opex, annual_energy, discount_rate, project_life)
        
        # Other metrics
        payback = self.calculate_payback_period(cash_flow.cumulative_cash_flows)
        discounted_payback = self.calculate_discounted_payback_period(
            cash_flow.net_cash_flows, discount_rate, capex
        )
        pi = self.calculate_profitability_index(npv, capex)
        roi = self.calculate_return_on_investment(cash_flow.net_cash_flows, capex)
        
        return {
            'npv': npv,
            'irr': irr,
            'lcoe': lcoe,
            'payback_period': payback,
            'discounted_payback_period': discounted_payback,
            'profitability_index': pi,
            'return_on_investment': roi
        }
    
    def project_cash_flow_projection(self, 
                                   capex: float,
                                   opex: float,
                                   revenue: float,
                                   project_life: int,
                                   **kwargs) -> CashFlowProjection:
        """
        Generate detailed cash flow projection.
        
        Args:
            capex: Capital expenditure
            opex: Annual operating expenditure
            revenue: Annual revenue
            project_life: Project lifetime
            **kwargs: Additional parameters
            
        Returns:
            CashFlowProjection object
        """
        years = np.arange(1, project_life + 1)
        revenues = np.zeros(project_life)
        opex_flows = np.zeros(project_life)
        
        # Revenue parameters
        inflation_rate = self.config.economic.get('inflation_rate', 0.02)
        degradation_rate = kwargs.get('degradation_rate', 0.005)  # 0.5% annual degradation
        
        # OPEX parameters
        opex_escalation = kwargs.get('opex_escalation', inflation_rate)
        
        for i, year in enumerate(years):
            # Revenue with degradation and price escalation
            degradation_factor = (1 - degradation_rate) ** (year - 1)
            price_escalation = (1 + inflation_rate) ** (year - 1)
            revenues[i] = revenue * degradation_factor * price_escalation
            
            # OPEX with escalation
            opex_flows[i] = opex * (1 + opex_escalation) ** (year - 1)
        
        # Calculate taxes
        tax_flows = self._calculate_taxes(capex, revenues, opex_flows, years)
        
        # Net cash flows (after tax)
        net_cash_flows = revenues - opex_flows - tax_flows
        
        # Add salvage value in final year
        salvage_value = capex * self.financial_params['salvage_value_rate']
        net_cash_flows[-1] += salvage_value
        
        # Cumulative cash flows
        cumulative_cash_flows = np.cumsum(net_cash_flows) - capex
        
        return CashFlowProjection(
            years=years,
            revenues=revenues,
            opex=opex_flows,
            net_cash_flows=net_cash_flows,
            cumulative_cash_flows=cumulative_cash_flows,
            capex=capex
        )
    
    def _calculate_taxes(self, 
                        capex: float,
                        revenues: np.ndarray,
                        opex: np.ndarray,
                        years: np.ndarray) -> np.ndarray:
        """Calculate annual tax payments."""
        
        tax_rate = self.financial_params['corporate_tax_rate']
        depreciation_period = min(self.financial_params['depreciation_period'], len(years))
        
        # Straight-line depreciation
        annual_depreciation = capex / depreciation_period
        
        taxes = np.zeros(len(years))
        
        for i, year in enumerate(years):
            # Taxable income
            depreciation = annual_depreciation if year <= depreciation_period else 0
            taxable_income = revenues[i] - opex[i] - depreciation
            
            # Tax (only if positive taxable income)
            taxes[i] = max(0, taxable_income * tax_rate)
        
        return taxes
    
    def calculate_npv(self, 
                     cash_flows: np.ndarray, 
                     discount_rate: float, 
                     initial_investment: float) -> float:
        """Calculate Net Present Value."""
        
        npv = -initial_investment
        
        for i, cash_flow in enumerate(cash_flows):
            year = i + 1
            pv = cash_flow / ((1 + discount_rate) ** year)
            npv += pv
        
        return npv
    
    def calculate_irr(self, 
                     cash_flows: np.ndarray, 
                     initial_investment: float,
                     max_iterations: int = 100,
                     tolerance: float = 1e-6) -> float:
        """Calculate Internal Rate of Return using Newton-Raphson method."""
        
        # Initial guess
        irr_guess = 0.1
        
        for iteration in range(max_iterations):
            # Calculate NPV and its derivative at current guess
            npv = -initial_investment
            npv_derivative = 0
            
            for i, cash_flow in enumerate(cash_flows):
                year = i + 1
                npv += cash_flow / ((1 + irr_guess) ** year)
                npv_derivative -= year * cash_flow / ((1 + irr_guess) ** (year + 1))
            
            # Newton-Raphson update
            if abs(npv_derivative) < 1e-12:
                break
                
            irr_new = irr_guess - npv / npv_derivative
            
            # Check convergence
            if abs(irr_new - irr_guess) < tolerance:
                return irr_new
            
            irr_guess = irr_new
            
            # Prevent negative or extremely high IRR
            irr_guess = max(-0.99, min(irr_guess, 10.0))
        
        # If no convergence, try bisection method
        return self._irr_bisection(cash_flows, initial_investment)
    
    def _irr_bisection(self, 
                      cash_flows: np.ndarray, 
                      initial_investment: float) -> float:
        """Calculate IRR using bisection method as fallback."""
        
        def npv_at_rate(rate):
            npv = -initial_investment
            for i, cf in enumerate(cash_flows):
                npv += cf / ((1 + rate) ** (i + 1))
            return npv
        
        # Find bounds
        low_rate = -0.99
        high_rate = 5.0
        
        # Check if solution exists
        if npv_at_rate(low_rate) * npv_at_rate(high_rate) > 0:
            return 0.0  # No IRR found
        
        # Bisection method
        for _ in range(100):
            mid_rate = (low_rate + high_rate) / 2
            npv_mid = npv_at_rate(mid_rate)
            
            if abs(npv_mid) < 1e-6:
                return mid_rate
            
            if npv_at_rate(low_rate) * npv_mid < 0:
                high_rate = mid_rate
            else:
                low_rate = mid_rate
        
        return (low_rate + high_rate) / 2
    
    def calculate_lcoe(self, 
                      capex: float,
                      opex: float,
                      annual_energy: float,
                      discount_rate: float,
                      project_life: int) -> float:
        """Calculate Levelized Cost of Energy (LCOE)."""
        
        if annual_energy <= 0:
            return float('inf')
        
        # Present value of costs
        pv_capex = capex
        pv_opex = 0
        
        for year in range(1, project_life + 1):
            pv_opex += opex / ((1 + discount_rate) ** year)
        
        total_pv_costs = pv_capex + pv_opex
        
        # Present value of energy (with degradation)
        pv_energy = 0
        degradation_rate = 0.005  # 0.5% annual degradation
        
        for year in range(1, project_life + 1):
            degradation_factor = (1 - degradation_rate) ** (year - 1)
            yearly_energy = annual_energy * degradation_factor
            pv_energy += yearly_energy / ((1 + discount_rate) ** year)
        
        # LCOE in £/MWh
        lcoe = total_pv_costs / pv_energy if pv_energy > 0 else float('inf')
        
        return lcoe
    
    def calculate_payback_period(self, cumulative_cash_flows: np.ndarray) -> float:
        """Calculate simple payback period."""
        
        # Find first positive cumulative cash flow
        positive_indices = np.where(cumulative_cash_flows > 0)[0]
        
        if len(positive_indices) == 0:
            return float('inf')  # Never pays back
        
        first_positive_year = positive_indices[0] + 1
        
        if first_positive_year == 1:
            return 1.0
        
        # Interpolate for exact payback time
        prev_cash_flow = cumulative_cash_flows[first_positive_year - 2]
        curr_cash_flow = cumulative_cash_flows[first_positive_year - 1]
        
        fraction = -prev_cash_flow / (curr_cash_flow - prev_cash_flow)
        payback = first_positive_year - 1 + fraction
        
        return payback
    
    def calculate_discounted_payback_period(self, 
                                          cash_flows: np.ndarray,
                                          discount_rate: float,
                                          initial_investment: float) -> float:
        """Calculate discounted payback period."""
        
        cumulative_pv = -initial_investment
        
        for i, cash_flow in enumerate(cash_flows):
            year = i + 1
            pv_cash_flow = cash_flow / ((1 + discount_rate) ** year)
            cumulative_pv += pv_cash_flow
            
            if cumulative_pv > 0:
                # Interpolate for exact payback time
                if i == 0:
                    return 1.0
                
                prev_cumulative = cumulative_pv - pv_cash_flow
                fraction = -prev_cumulative / pv_cash_flow
                return year - 1 + fraction
        
        return float('inf')  # Never pays back on discounted basis
    
    def calculate_profitability_index(self, npv: float, initial_investment: float) -> float:
        """Calculate profitability index."""
        
        if initial_investment <= 0:
            return 0.0
        
        return (npv + initial_investment) / initial_investment
    
    def calculate_return_on_investment(self, 
                                     cash_flows: np.ndarray, 
                                     initial_investment: float) -> float:
        """Calculate average return on investment."""
        
        if initial_investment <= 0:
            return 0.0
        
        total_returns = np.sum(cash_flows)
        average_annual_return = total_returns / len(cash_flows)
        
        return average_annual_return / initial_investment
    
    def monte_carlo_financial_analysis(self, 
                                     base_params: Dict[str, float],
                                     uncertainty_params: Dict[str, Dict[str, float]],
                                     n_simulations: int = 10000) -> Dict[str, Any]:
        """
        Perform Monte Carlo analysis of financial metrics.
        
        Args:
            base_params: Base case parameters
            uncertainty_params: Uncertainty distributions for each parameter
            n_simulations: Number of simulations
            
        Returns:
            Dictionary with simulation results and statistics
        """
        
        # Storage for results
        npv_results = []
        irr_results = []
        lcoe_results = []
        
        for sim in range(n_simulations):
            # Sample uncertain parameters
            sim_params = base_params.copy()
            
            for param, uncertainty in uncertainty_params.items():
                distribution = uncertainty.get('distribution', 'normal')
                
                if distribution == 'normal':
                    mean = uncertainty['mean']
                    std = uncertainty['std']
                    sim_params[param] = np.random.normal(mean, std)
                elif distribution == 'uniform':
                    low = uncertainty['low']
                    high = uncertainty['high']
                    sim_params[param] = np.random.uniform(low, high)
                elif distribution == 'triangular':
                    low = uncertainty['low']
                    mode = uncertainty['mode']
                    high = uncertainty['high']
                    sim_params[param] = np.random.triangular(low, mode, high)
            
            # Ensure positive values where required
            sim_params['capex'] = max(0, sim_params['capex'])
            sim_params['opex'] = max(0, sim_params['opex'])
            sim_params['revenue'] = max(0, sim_params['revenue'])
            
            # Calculate metrics for this simulation
            try:
                metrics = self.calculate_metrics(**sim_params)
                npv_results.append(metrics['npv'])
                irr_results.append(metrics['irr'])
                lcoe_results.append(metrics['lcoe'])
            except:
                # Skip invalid simulations
                continue
        
        # Calculate statistics
        results = {
            'npv': {
                'mean': np.mean(npv_results),
                'std': np.std(npv_results),
                'percentiles': {
                    'p5': np.percentile(npv_results, 5),
                    'p25': np.percentile(npv_results, 25),
                    'p50': np.percentile(npv_results, 50),
                    'p75': np.percentile(npv_results, 75),
                    'p95': np.percentile(npv_results, 95)
                },
                'probability_positive': np.mean(np.array(npv_results) > 0)
            },
            'irr': {
                'mean': np.mean(irr_results),
                'std': np.std(irr_results),
                'percentiles': {
                    'p5': np.percentile(irr_results, 5),
                    'p25': np.percentile(irr_results, 25),
                    'p50': np.percentile(irr_results, 50),
                    'p75': np.percentile(irr_results, 75),
                    'p95': np.percentile(irr_results, 95)
                }
            },
            'lcoe': {
                'mean': np.mean(lcoe_results),
                'std': np.std(lcoe_results),
                'percentiles': {
                    'p5': np.percentile(lcoe_results, 5),
                    'p25': np.percentile(lcoe_results, 25),
                    'p50': np.percentile(lcoe_results, 50),
                    'p75': np.percentile(lcoe_results, 75),
                    'p95': np.percentile(lcoe_results, 95)
                }
            },
            'simulation_info': {
                'n_simulations': len(npv_results),
                'n_successful': len(npv_results),
                'success_rate': len(npv_results) / n_simulations
            }
        }
        
        return results
    
    def sensitivity_analysis(self, 
                           base_params: Dict[str, float],
                           sensitivity_params: List[str],
                           variation_range: float = 0.2) -> Dict[str, Dict[str, float]]:
        """
        Perform sensitivity analysis on financial metrics.
        
        Args:
            base_params: Base case parameters
            sensitivity_params: List of parameters to analyze
            variation_range: Relative variation range (e.g., 0.2 for ±20%)
            
        Returns:
            Dictionary with sensitivity results
        """
        
        base_metrics = self.calculate_metrics(**base_params)
        sensitivity_results = {}
        
        for param in sensitivity_params:
            if param not in base_params:
                continue
            
            base_value = base_params[param]
            variations = [-variation_range, variation_range]
            
            param_sensitivities = {}
            
            for variation in variations:
                test_params = base_params.copy()
                test_params[param] = base_value * (1 + variation)
                
                # Ensure positive values
                test_params[param] = max(0, test_params[param])
                
                try:
                    test_metrics = self.calculate_metrics(**test_params)
                    
                    # Calculate sensitivity (% change in metric / % change in parameter)
                    for metric_name, metric_value in test_metrics.items():
                        base_metric = base_metrics[metric_name]
                        
                        if base_metric != 0:
                            metric_change = (metric_value - base_metric) / base_metric
                            sensitivity = metric_change / variation
                        else:
                            sensitivity = 0.0
                        
                        param_sensitivities[f'{metric_name}_sensitivity'] = sensitivity
                
                except:
                    # Handle calculation errors
                    for metric_name in base_metrics.keys():
                        param_sensitivities[f'{metric_name}_sensitivity'] = 0.0
            
            sensitivity_results[param] = param_sensitivities
        
        return sensitivity_results
    
    def debt_equity_analysis(self, 
                           capex: float,
                           debt_ratio: float,
                           debt_interest_rate: float,
                           equity_return_requirement: float) -> Dict[str, float]:
        """
        Analyze debt and equity financing structure.
        
        Args:
            capex: Total capital expenditure
            debt_ratio: Debt to total capital ratio
            debt_interest_rate: Interest rate on debt
            equity_return_requirement: Required return on equity
            
        Returns:
            Dictionary with financing analysis
        """
        
        debt_amount = capex * debt_ratio
        equity_amount = capex * (1 - debt_ratio)
        
        # Annual debt service (assuming simple interest for now)
        annual_debt_service = debt_amount * debt_interest_rate
        
        # Weighted average cost of capital (WACC)
        tax_rate = self.financial_params['corporate_tax_rate']
        after_tax_debt_cost = debt_interest_rate * (1 - tax_rate)
        
        wacc = (debt_ratio * after_tax_debt_cost + 
                (1 - debt_ratio) * equity_return_requirement)
        
        return {
            'debt_amount': debt_amount,
            'equity_amount': equity_amount,
            'annual_debt_service': annual_debt_service,
            'wacc': wacc,
            'after_tax_debt_cost': after_tax_debt_cost,
            'debt_to_equity_ratio': debt_ratio / (1 - debt_ratio)
        }
    
    def real_options_valuation(self, 
                              base_npv: float,
                              volatility: float,
                              option_life: float,
                              risk_free_rate: float) -> Dict[str, float]:
        """
        Calculate real options value using Black-Scholes approach.
        
        Args:
            base_npv: Base case NPV
            volatility: Volatility of underlying asset
            option_life: Life of the option (years)
            risk_free_rate: Risk-free interest rate
            
        Returns:
            Dictionary with option values
        """
        
        # Simplified real options calculation
        # This is a basic implementation - real applications would be more sophisticated
        
        if base_npv <= 0:
            return {'option_value': 0.0, 'expanded_npv': base_npv}
        
        # Parameters for Black-Scholes formula
        S = abs(base_npv)  # Current "price" (absolute NPV)
        K = 0  # Strike price (cost of exercising option)
        T = option_life
        r = risk_free_rate
        sigma = volatility
        
        # Black-Scholes calculation for call option
        d1 = (math.log(S/max(K, 1)) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        
        # Standard normal cumulative distribution function (approximation)
        def norm_cdf(x):
            return 0.5 * (1 + math.erf(x / math.sqrt(2)))
        
        # Call option value
        option_value = S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
        
        # Expanded NPV including option value
        expanded_npv = base_npv + option_value
        
        return {
            'option_value': option_value,
            'expanded_npv': expanded_npv,
            'option_premium': option_value / max(S, 1) * 100  # As percentage
        }
    
    def get_financial_summary(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """Get summary of financial analysis results."""
        
        # Interpret results
        investment_grade = "Poor"
        if metrics.get('npv', 0) > 0 and metrics.get('irr', 0) > 0.1:
            if metrics.get('irr', 0) > 0.15:
                investment_grade = "Excellent"
            elif metrics.get('irr', 0) > 0.12:
                investment_grade = "Good"
            else:
                investment_grade = "Acceptable"
        
        payback = metrics.get('payback_period', float('inf'))
        payback_assessment = "Poor"
        if payback < 7:
            payback_assessment = "Excellent"
        elif payback < 10:
            payback_assessment = "Good"
        elif payback < 15:
            payback_assessment = "Acceptable"
        
        return {
            'investment_grade': investment_grade,
            'payback_assessment': payback_assessment,
            'key_metrics': {
                'npv_millions': metrics.get('npv', 0) / 1e6,
                'irr_percent': metrics.get('irr', 0) * 100,
                'lcoe_per_mwh': metrics.get('lcoe', 0),
                'payback_years': payback
            },
            'profitability': metrics.get('npv', 0) > 0,
            'hurdle_rate_met': metrics.get('irr', 0) > self.config.economic.get('discount_rate', 0.08)
        }
