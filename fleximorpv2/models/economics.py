"""
Economic model for offshore renewable energy systems.

Handles financial analysis, cost calculations, revenue modeling,
and economic performance metrics for offshore renewable platforms.
"""

import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
import math

from ..config import SiteConfig


@dataclass
class CostBreakdown:
    """Detailed cost breakdown for the project."""
    technology_capex: float
    platform_capex: float
    installation_capex: float
    grid_connection_capex: float
    development_capex: float
    total_capex: float
    
    technology_opex: float
    platform_opex: float
    grid_opex: float
    insurance_opex: float
    total_opex: float


@dataclass
class RevenueModel:
    """Revenue modeling for the project."""
    electricity_revenue: float
    subsidy_revenue: float
    capacity_payments: float
    total_annual_revenue: float
    electricity_price: float
    annual_energy: float
    generation_profile: np.ndarray


class EconomicModel:
    """
    Economic model for offshore renewable energy platforms.
    
    Handles comprehensive financial analysis including CAPEX/OPEX calculations,
    revenue modeling, and economic performance metrics.
    """
    
    def __init__(self, config: SiteConfig):
        """
        Initialize economic model.
        
        Args:
            config: Site configuration object
        """
        self.config = config
        self.cost_breakdown: Optional[CostBreakdown] = None
        self.revenue_model: Optional[RevenueModel] = None
        
        # Economic parameters
        self.economic_params = {
            # Installation cost factors
            'installation_factor': 0.25,  # 25% of equipment CAPEX
            'grid_connection_cost_per_km': 100000,  # £100k per km
            'development_cost_factor': 0.15,  # 15% of total CAPEX
            
            # OPEX factors
            'platform_opex_factor': 0.02,  # 2% of platform CAPEX per year
            'grid_opex_factor': 0.01,  # 1% of grid CAPEX per year
            'insurance_rate': 0.005,  # 0.5% of total CAPEX per year
            
            # Revenue factors
            'capacity_payment_rate': 45000,  # £45/MW/year
            'subsidy_rates': {
                'wind': 0.08,    # £80/MWh
                'solar': 0.06,   # £60/MWh
                'wave': 0.12     # £120/MWh
            },
            
            # Market factors
            'electricity_price_volatility': 0.3,  # 30% volatility
            'fuel_price_correlation': 0.7,
            'carbon_price_impact': 0.02  # £20/tonne CO2
        }
    
    def calculate_economics(self, 
                          design_vars: Dict[str, Any], 
                          tech_performance: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate comprehensive economic performance.
        
        Args:
            design_vars: Platform design variables
            tech_performance: Technology performance metrics
            
        Returns:
            Dictionary with economic performance metrics
        """
        # Calculate costs
        costs = self._calculate_total_costs(design_vars, tech_performance)
        
        # Calculate revenues
        revenues = self._calculate_revenues(tech_performance)
        
        # Calculate economic metrics
        economic_metrics = self._calculate_economic_metrics(costs, revenues)
        
        # Combine all metrics
        all_metrics = {**costs, **revenues, **economic_metrics}
        
        return all_metrics
    
    def _calculate_total_costs(self, 
                              design_vars: Dict[str, Any], 
                              tech_performance: Dict[str, float]) -> Dict[str, float]:
        """Calculate total project costs (CAPEX and OPEX)."""
        
        # Technology costs
        tech_capex = tech_performance.get('total_technology_capex', 0.0)
        tech_opex = tech_performance.get('total_technology_opex', 0.0)
        
        # Platform costs
        platform_costs = self._calculate_platform_costs(design_vars)
        platform_capex = platform_costs['total_platform_cost']
        platform_opex = platform_capex * self.economic_params['platform_opex_factor']
        
        # Installation costs
        installation_capex = tech_capex * self.economic_params['installation_factor']
        
        # Grid connection costs
        distance_to_shore = design_vars.get('distance_to_shore', 20)
        grid_connection_capex = distance_to_shore * self.economic_params['grid_connection_cost_per_km']
        grid_opex = grid_connection_capex * self.economic_params['grid_opex_factor']
        
        # Development costs
        equipment_capex = tech_capex + platform_capex + installation_capex + grid_connection_capex
        development_capex = equipment_capex * self.economic_params['development_cost_factor']
        
        # Total CAPEX
        total_capex = tech_capex + platform_capex + installation_capex + grid_connection_capex + development_capex
        
        # Insurance costs
        insurance_opex = total_capex * self.economic_params['insurance_rate']
        
        # Total OPEX
        total_opex = tech_opex + platform_opex + grid_opex + insurance_opex
        
        # Store cost breakdown
        self.cost_breakdown = CostBreakdown(
            technology_capex=tech_capex,
            platform_capex=platform_capex,
            installation_capex=installation_capex,
            grid_connection_capex=grid_connection_capex,
            development_capex=development_capex,
            total_capex=total_capex,
            technology_opex=tech_opex,
            platform_opex=platform_opex,
            grid_opex=grid_opex,
            insurance_opex=insurance_opex,
            total_opex=total_opex
        )
        
        return {
            'capex': total_capex,
            'opex': total_opex,
            'technology_capex': tech_capex,
            'platform_capex': platform_capex,
            'installation_capex': installation_capex,
            'grid_connection_capex': grid_connection_capex,
            'development_capex': development_capex,
            'technology_opex': tech_opex,
            'platform_opex': platform_opex,
            'grid_opex': grid_opex,
            'insurance_opex': insurance_opex
        }
    
    def _calculate_platform_costs(self, design_vars: Dict[str, Any]) -> Dict[str, float]:
        """Calculate platform-specific costs."""
        # This would typically interface with the PlatformModel
        # For now, simplified calculation
        
        platform_area = design_vars.get('platform_area', 10000)  # m²
        water_depth = design_vars.get('water_depth', 50)  # m
        distance_to_shore = design_vars.get('distance_to_shore', 20)  # km
        
        # Base cost per m² based on water depth
        if water_depth <= 50:
            cost_per_m2 = 15000  # Fixed platform
        elif water_depth <= 100:
            cost_per_m2 = 25000  # Semi-submersible
        else:
            cost_per_m2 = 35000  # Floating platform
        
        # Structural costs
        structural_cost = platform_area * cost_per_m2
        
        # Installation complexity factor
        complexity_factor = 1.0 + (water_depth / 200) * 0.5
        installation_cost = structural_cost * 0.3 * complexity_factor
        
        # Mooring costs (for floating platforms)
        if water_depth > 50:
            mooring_cost = structural_cost * 0.2
        else:
            mooring_cost = structural_cost * 0.1
        
        # Distance-dependent costs
        distance_cost = distance_to_shore * 50000  # £50k per km
        
        total_cost = structural_cost + installation_cost + mooring_cost + distance_cost
        
        return {
            'structural_cost': structural_cost,
            'installation_cost': installation_cost,
            'mooring_cost': mooring_cost,
            'distance_cost': distance_cost,
            'total_platform_cost': total_cost
        }
    
    def _calculate_revenues(self, tech_performance: Dict[str, float]) -> Dict[str, float]:
        """Calculate project revenues."""
        
        # Annual energy generation
        generation_profile = np.asarray(tech_performance.get('generation_profile', []), dtype=float)
        if generation_profile.size > 0:
            annual_energy = float(np.sum(generation_profile))  # MWh/year
        else:
            annual_energy = tech_performance.get('annual_energy', 0.0)  # MWh/year
            generation_profile = np.full(8760, annual_energy / 8760 if annual_energy > 0 else 0.0)
        
        # Electricity revenue
        electricity_price = self.config.economic.get('electricity_price', 0.10)  # £/kWh
        electricity_revenue = float(np.sum(generation_profile) * electricity_price * 1000)
        
        # Subsidy revenue (technology-specific)
        subsidy_revenue = self._calculate_subsidy_revenue(tech_performance)
        
        # Capacity payments
        total_capacity = tech_performance.get('total_capacity', 0.0)  # MW
        capacity_payments = total_capacity * self.economic_params['capacity_payment_rate']
        
        # Total annual revenue
        total_annual_revenue = electricity_revenue + subsidy_revenue + capacity_payments
        
        # Store revenue model
        self.revenue_model = RevenueModel(
            electricity_revenue=electricity_revenue,
            subsidy_revenue=subsidy_revenue,
            capacity_payments=capacity_payments,
            total_annual_revenue=total_annual_revenue,
            electricity_price=electricity_price,
            annual_energy=annual_energy,
            generation_profile=generation_profile
        )
        
        return {
            'revenue': total_annual_revenue,
            'annual_energy': annual_energy,
            'electricity_revenue': electricity_revenue,
            'subsidy_revenue': subsidy_revenue,
            'capacity_payments': capacity_payments
        }
    
    def _calculate_subsidy_revenue(self, tech_performance: Dict[str, float]) -> float:
        """Calculate technology-specific subsidy revenues."""
        total_subsidy = 0.0
        
        for tech_name in self.config.get_enabled_technologies():
            tech_energy = tech_performance.get(f'{tech_name}_annual_energy', 0.0)
            subsidy_rate = self.economic_params['subsidy_rates'].get(tech_name, 0.0)
            total_subsidy += tech_energy * subsidy_rate * 1000  # Convert MWh to kWh
        
        return total_subsidy
    
    def _calculate_economic_metrics(self, 
                                   costs: Dict[str, float], 
                                   revenues: Dict[str, float]) -> Dict[str, float]:
        """Calculate key economic performance metrics."""
        
        capex = costs['capex']
        opex = costs['opex']
        annual_revenue = revenues['revenue']
        
        # Project parameters
        discount_rate = self.config.economic.get('discount_rate', 0.08)
        project_life = self.config.economic.get('project_lifetime', 25)
        
        # LCOE (Levelized Cost of Energy)
        annual_energy = revenues.get('annual_energy', 1.0)  # Avoid division by zero
        if annual_energy > 0:
            lcoe = self._calculate_lcoe(capex, opex, annual_energy, discount_rate, project_life)
        else:
            lcoe = float('inf')
        
        # NPV (Net Present Value)
        npv = self._calculate_npv(capex, annual_revenue, opex, discount_rate, project_life)
        
        # IRR (Internal Rate of Return)
        irr = self._calculate_irr(capex, annual_revenue, opex, project_life)
        
        # Payback period
        payback = self._calculate_payback_period(capex, annual_revenue, opex)
        
        # Profitability index
        pi = (npv + capex) / capex if capex > 0 else 0.0
        
        return {
            'lcoe': lcoe,
            'npv': npv,
            'irr': irr,
            'payback_period': payback,
            'profitability_index': pi
        }
    
    def _calculate_lcoe(self, 
                       capex: float, 
                       opex: float, 
                       annual_energy: float, 
                       discount_rate: float, 
                       project_life: int) -> float:
        """Calculate Levelized Cost of Energy (LCOE)."""
        
        # Present value of costs
        pv_capex = capex
        pv_opex = 0.0
        
        for year in range(1, project_life + 1):
            pv_opex += opex / ((1 + discount_rate) ** year)
        
        total_pv_costs = pv_capex + pv_opex
        
        # Present value of energy
        pv_energy = 0.0
        for year in range(1, project_life + 1):
            # Apply degradation
            degradation_factor = (1 - 0.005) ** (year - 1)  # 0.5% annual degradation
            yearly_energy = annual_energy * degradation_factor
            pv_energy += yearly_energy / ((1 + discount_rate) ** year)
        
        # LCOE in £/MWh
        lcoe = (total_pv_costs / pv_energy) if pv_energy > 0 else float('inf')
        
        return lcoe
    
    def _calculate_npv(self, 
                      capex: float, 
                      annual_revenue: float, 
                      opex: float, 
                      discount_rate: float, 
                      project_life: int) -> float:
        """Calculate Net Present Value (NPV)."""
        
        npv = -capex  # Initial investment
        
        for year in range(1, project_life + 1):
            # Annual cash flow (revenue - opex)
            cash_flow = annual_revenue - opex
            
            # Apply electricity price escalation
            escalation_rate = self.config.economic.get('inflation_rate', 0.02)
            escalated_cash_flow = cash_flow * ((1 + escalation_rate) ** (year - 1))
            
            # Discount to present value
            pv_cash_flow = escalated_cash_flow / ((1 + discount_rate) ** year)
            npv += pv_cash_flow
        
        return npv
    
    def _calculate_irr(self, 
                      capex: float, 
                      annual_revenue: float, 
                      opex: float, 
                      project_life: int) -> float:
        """Calculate Internal Rate of Return (IRR) using iterative method."""
        
        def npv_at_rate(rate):
            npv = -capex
            for year in range(1, project_life + 1):
                cash_flow = annual_revenue - opex
                npv += cash_flow / ((1 + rate) ** year)
            return npv
        
        # Use bisection method to find IRR
        low_rate = 0.0
        high_rate = 1.0
        tolerance = 1e-6
        max_iterations = 100
        
        # Check if IRR exists
        if npv_at_rate(high_rate) > 0:
            return high_rate  # IRR > 100%
        
        if npv_at_rate(low_rate) < 0:
            return 0.0  # No positive IRR
        
        # Bisection method
        for _ in range(max_iterations):
            mid_rate = (low_rate + high_rate) / 2
            npv_mid = npv_at_rate(mid_rate)
            
            if abs(npv_mid) < tolerance:
                return mid_rate
            
            if npv_mid > 0:
                low_rate = mid_rate
            else:
                high_rate = mid_rate
        
        return (low_rate + high_rate) / 2
    
    def _calculate_payback_period(self, 
                                 capex: float, 
                                 annual_revenue: float, 
                                 opex: float) -> float:
        """Calculate simple payback period in years."""
        
        annual_cash_flow = annual_revenue - opex
        
        if annual_cash_flow <= 0:
            return float('inf')
        
        return capex / annual_cash_flow
    
    def calculate_sensitivity_to_electricity_price(self, 
                                                  price_range: Tuple[float, float], 
                                                  steps: int = 10) -> Dict[str, np.ndarray]:
        """Calculate sensitivity of economic metrics to electricity price."""
        
        if self.cost_breakdown is None or self.revenue_model is None:
            raise ValueError("Must calculate economics first")
        
        original_price = self.revenue_model.electricity_price
        prices = np.linspace(price_range[0], price_range[1], steps)
        
        npvs = []
        lcoes = []
        irrs = []
        
        for price in prices:
            # Recalculate revenue at new price
            tech_performance = {
                'annual_energy': self.revenue_model.annual_energy,
                'generation_profile': self.revenue_model.generation_profile
            }
            
            # Update electricity price in config temporarily
            original_config_price = self.config.economic.get('electricity_price', 0.10)
            self.config.economic['electricity_price'] = price
            
            # Recalculate economics
            revenues = self._calculate_revenues(tech_performance)
            costs = {
                'capex': self.cost_breakdown.total_capex,
                'opex': self.cost_breakdown.total_opex
            }
            
            metrics = self._calculate_economic_metrics(costs, revenues)
            
            npvs.append(metrics['npv'])
            lcoes.append(metrics['lcoe'])
            irrs.append(metrics['irr'])
            
            # Restore original price
            self.config.economic['electricity_price'] = original_config_price
        
        return {
            'prices': prices,
            'npvs': np.array(npvs),
            'lcoes': np.array(lcoes),
            'irrs': np.array(irrs)
        }
    
    def calculate_risk_metrics(self) -> Dict[str, float]:
        """Calculate project risk metrics."""
        
        if self.cost_breakdown is None:
            raise ValueError("Must calculate economics first")
        
        # Technology risk (based on technology maturity)
        tech_risks = {
            'wind': 0.05,    # Low risk - mature technology
            'solar': 0.03,   # Very low risk - mature technology
            'wave': 0.15     # High risk - emerging technology
        }
        
        total_capex = self.cost_breakdown.total_capex
        tech_capex = self.cost_breakdown.technology_capex
        
        # Weighted technology risk
        weighted_tech_risk = 0.0
        for tech_name in self.config.get_enabled_technologies():
            tech_config = self.config.technologies[tech_name]
            if tech_config.enabled:
                weight = tech_config.cost_per_mw / tech_capex if tech_capex > 0 else 0
                weighted_tech_risk += weight * tech_risks.get(tech_name, 0.1)
        
        # Market risk (electricity price volatility)
        market_risk = self.economic_params['electricity_price_volatility']
        
        # Financial risk (leverage dependent)
        financial_risk = 0.08  # Baseline 8% for renewable projects
        
        # Overall project risk
        overall_risk = (weighted_tech_risk * 0.4 + 
                       market_risk * 0.4 + 
                       financial_risk * 0.2)
        
        return {
            'technology_risk': weighted_tech_risk,
            'market_risk': market_risk,
            'financial_risk': financial_risk,
            'overall_risk': overall_risk,
            'risk_adjusted_discount_rate': self.config.economic.get('discount_rate', 0.08) + overall_risk
        }
    
    def get_cost_breakdown_summary(self) -> Dict[str, Any]:
        """Get detailed cost breakdown summary."""
        
        if self.cost_breakdown is None:
            return {"error": "No cost data available"}
        
        total_capex = self.cost_breakdown.total_capex
        total_opex = self.cost_breakdown.total_opex
        
        return {
            'capex_breakdown': {
                'technology': {
                    'amount': self.cost_breakdown.technology_capex,
                    'percentage': self.cost_breakdown.technology_capex / total_capex * 100
                },
                'platform': {
                    'amount': self.cost_breakdown.platform_capex,
                    'percentage': self.cost_breakdown.platform_capex / total_capex * 100
                },
                'installation': {
                    'amount': self.cost_breakdown.installation_capex,
                    'percentage': self.cost_breakdown.installation_capex / total_capex * 100
                },
                'grid_connection': {
                    'amount': self.cost_breakdown.grid_connection_capex,
                    'percentage': self.cost_breakdown.grid_connection_capex / total_capex * 100
                },
                'development': {
                    'amount': self.cost_breakdown.development_capex,
                    'percentage': self.cost_breakdown.development_capex / total_capex * 100
                },
                'total': total_capex
            },
            'opex_breakdown': {
                'technology': {
                    'amount': self.cost_breakdown.technology_opex,
                    'percentage': self.cost_breakdown.technology_opex / total_opex * 100
                },
                'platform': {
                    'amount': self.cost_breakdown.platform_opex,
                    'percentage': self.cost_breakdown.platform_opex / total_opex * 100
                },
                'grid': {
                    'amount': self.cost_breakdown.grid_opex,
                    'percentage': self.cost_breakdown.grid_opex / total_opex * 100
                },
                'insurance': {
                    'amount': self.cost_breakdown.insurance_opex,
                    'percentage': self.cost_breakdown.insurance_opex / total_opex * 100
                },
                'total': total_opex
            }
        }
    
    def get_revenue_breakdown_summary(self) -> Dict[str, Any]:
        """Get detailed revenue breakdown summary."""
        
        if self.revenue_model is None:
            return {"error": "No revenue data available"}
        
        total_revenue = self.revenue_model.total_annual_revenue
        
        return {
            'revenue_breakdown': {
                'electricity_sales': {
                    'amount': self.revenue_model.electricity_revenue,
                    'percentage': self.revenue_model.electricity_revenue / total_revenue * 100
                },
                'subsidies': {
                    'amount': self.revenue_model.subsidy_revenue,
                    'percentage': self.revenue_model.subsidy_revenue / total_revenue * 100
                },
                'capacity_payments': {
                    'amount': self.revenue_model.capacity_payments,
                    'percentage': self.revenue_model.capacity_payments / total_revenue * 100
                },
                'total': total_revenue
            },
            'electricity_price': self.revenue_model.electricity_price
        }
