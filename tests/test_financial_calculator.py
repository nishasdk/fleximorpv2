"""
Regression tests for financial and economic metric calculations.
"""

import pytest
import numpy as np

from fleximorpv2.config import SiteConfig, TechnologyConfig
from fleximorpv2.models.technologies import TechnologyModel, ResourceData
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


def test_technology_model_returns_hourly_generation_profile():
    config = SiteConfig(
        name="Test site",
        coordinates=[0.0, 0.0],
        technologies={
            "wind": TechnologyConfig(
                enabled=True,
                cost_per_mw=2500,
                capacity_factor=0.4,
                technical_params={"availability": 1.0},
            )
        },
        optimization={},
        uncertainty={},
        flexibility={},
        economic={"discount_rate": 0.08, "project_lifetime": 20, "electricity_price": 0.10},
    )
    model = TechnologyModel(config)

    wind_speed = np.tile([2.0, 15.0], 4380)
    resource = ResourceData(
        wind_speed=wind_speed,
        solar_irradiance=np.zeros(8760),
        wave_height=np.zeros(8760),
        wave_period=np.ones(8760),
        temperature=np.zeros(8760),
        timestamps=np.arange(8760),
    )
    perf = model.calculate_performance({"wind_capacity": 2.0}, resource)

    assert "generation_profile" in perf
    assert perf["generation_profile"].shape == (8760,)
    assert not np.allclose(perf["generation_profile"], np.ones(8760))
    assert perf["annual_energy"] == pytest.approx(float(np.sum(perf["generation_profile"])))
    assert perf["annual_energy"] > 0


def test_economic_model_uses_real_generation_profile(minimal_config):
    model = EconomicModel(minimal_config)
    generation_profile = np.tile([0.0, 2.0], 4380)
    tech_performance = {
        "annual_energy": float(np.sum(generation_profile)),
        "generation_profile": generation_profile,
        "total_capacity": 2.0,
    }

    revenues = model._calculate_revenues(tech_performance)

    assert revenues["annual_energy"] == pytest.approx(float(np.sum(generation_profile)))
    assert model.revenue_model is not None
    assert model.revenue_model.generation_profile.shape == (8760,)
    assert np.array_equal(model.revenue_model.generation_profile, generation_profile)
