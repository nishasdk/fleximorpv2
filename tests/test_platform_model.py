"""
Tests for platform sizing and performance metrics.
"""

import pytest

from fleximorpv2.config import SiteConfig
from fleximorpv2.models.platform import PlatformModel


@pytest.fixture
def minimal_platform_config():
    return SiteConfig(
        name="Test site",
        coordinates=[0.0, 0.0],
        technologies={},
        optimization={},
        uncertainty={},
        flexibility={},
        economic={"project_lifetime": 20},
    )


def _design_and_measure(model: PlatformModel, design_vars, technology_requirements):
    specs = model.design_platform(design_vars, technology_requirements)
    performance = model.calculate_performance(design_vars)
    return specs, performance


def test_platform_load_utilization_is_derived_from_design(minimal_platform_config):
    model = PlatformModel(minimal_platform_config)
    design_vars = {"platform_area": 50000, "water_depth": 35, "distance_to_shore": 5}
    tech_requirements = {
        "wind": {"capacity": 20, "load_per_mw": 80, "area_per_mw": 300},
        "solar": {"capacity": 20, "load_per_mw": 15, "area_per_mw": 4000},
    }

    specs, performance = _design_and_measure(model, design_vars, tech_requirements)

    expected = specs.required_load_capacity / specs.max_load_capacity
    assert performance["platform_load_utilization"] == pytest.approx(expected)
    assert 0 < performance["platform_load_utilization"] < 1
    assert model.performance is not None
    assert model.performance.load_utilization == pytest.approx(expected)


def test_platform_load_utilization_changes_with_technology_load(minimal_platform_config):
    model = PlatformModel(minimal_platform_config)
    design_vars = {"platform_area": 500000, "water_depth": 35, "distance_to_shore": 5}

    low_load_requirements = {
        "wind": {"capacity": 20, "load_per_mw": 80, "area_per_mw": 300},
        "solar": {"capacity": 20, "load_per_mw": 15, "area_per_mw": 4000},
    }
    high_load_requirements = {
        "wind": {"capacity": 80, "load_per_mw": 80, "area_per_mw": 300},
        "solar": {"capacity": 80, "load_per_mw": 15, "area_per_mw": 4000},
    }

    low_specs, low_perf = _design_and_measure(model, design_vars, low_load_requirements)
    high_specs, high_perf = _design_and_measure(model, design_vars, high_load_requirements)

    assert low_specs.max_load_capacity == pytest.approx(high_specs.max_load_capacity)
    assert low_perf["platform_load_utilization"] < high_perf["platform_load_utilization"]
    assert high_perf["platform_load_utilization"] == pytest.approx(
        high_specs.required_load_capacity / high_specs.max_load_capacity
    )
