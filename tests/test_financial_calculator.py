"""
Regression tests for financial and economic metric calculations.
"""

import pytest

from fleximorpv2.config import SiteConfig
from fleximorpv2.models.economics import EconomicModel
from fleximorpv2.utils.financial import FinancialCalculator


@pytest.fixture
def minimal_config():
    return SiteConfig(
        name="Test site",
        coordinates=[0.0, 0.0],
        technologies={},
        optimization={},
        uncertainty={},
        flexibility={},
        economic={
            "discount_rate": 0.08,
            "project_lifetime": 20,
            "electricity_price": 0.10,
            "tax_rate": 0.25,
        },
    )


def test_calculate_metrics_requires_annual_energy_for_lcoe(minimal_config):
    calc = FinancialCalculator(minimal_config)

    with pytest.raises(ValueError, match="annual_energy is required"):
        calc.calculate_metrics(
            capex=1_000_000,
            opex=50_000,
            revenue=1_000_000,
            project_life=20,
        )


def test_calculate_metrics_uses_supplied_annual_energy(minimal_config):
    calc = FinancialCalculator(minimal_config)

    capex = 1_000_000
    opex = 50_000
    annual_energy = 10_000
    revenue = annual_energy * minimal_config.economic["electricity_price"] * 1000

    metrics = calc.calculate_metrics(
        capex=capex,
        opex=opex,
        revenue=revenue,
        project_life=20,
        annual_energy=annual_energy,
    )
    direct_lcoe = calc.calculate_lcoe(capex, opex, annual_energy, 0.08, 20)

    assert metrics["lcoe"] == pytest.approx(direct_lcoe)
    assert metrics["lcoe"] > 1.0


def test_economic_revenues_preserve_annual_energy_for_lcoe(minimal_config):
    model = EconomicModel(minimal_config)
    tech_performance = {
        "annual_energy": 10_000,
        "total_capacity": 2.0,
    }

    revenues = model._calculate_revenues(tech_performance)
    metrics = model._calculate_economic_metrics(
        costs={"capex": 1_000_000, "opex": 50_000},
        revenues=revenues,
    )

    assert revenues["annual_energy"] == tech_performance["annual_energy"]
    assert revenues["electricity_revenue"] == pytest.approx(1_000_000)
    assert metrics["lcoe"] > 1.0
