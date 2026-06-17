"""
Test suite for the technology performance model.
"""

import numpy as np

from fleximorpv2.config import load_config
from fleximorpv2.models.technologies import TechnologyModel, ResourceData


class TestSolarDeploymentType:
    """Regression tests for #27: deployment_options use 'enabled', not 'available'."""

    def setup_method(self):
        self.config = load_config("alaska")
        self.tech_model = TechnologyModel(self.config)
        self.resource_data = ResourceData(
            wind_speed=np.full(8760, 8.0),
            solar_irradiance=np.full(8760, 200.0),
            wave_height=np.full(8760, 1.5),
            wave_period=np.full(8760, 6.0),
            temperature=np.full(8760, 5.0),
            timestamps=np.arange(8760),
        )

    def test_determine_solar_deployment_type_does_not_raise(self):
        deploy_type, deployment_config = self.tech_model._determine_solar_deployment_type({})
        assert deploy_type in ("land", "floating", "both")
        assert isinstance(deployment_config, dict)

    def test_specified_deployment_type_is_honoured(self):
        deploy_type, _ = self.tech_model._determine_solar_deployment_type(
            {"solar_deployment_type": "floating"}
        )
        assert deploy_type == "floating"

    def test_solar_performance_calculation_does_not_raise(self):
        """End-to-end smoke test: nonzero solar capacity must not crash performance calc."""
        performance = self.tech_model.calculate_performance(
            {"wind_capacity": 0.5, "solar_capacity": 0.5},
            self.resource_data,
        )
        assert performance["solar_capacity_factor"] >= 0.0


class TestHydroPerformance:
    """Regression test: hydro_config is a TechnologyConfig, not a dict (AttributeError on .get())."""

    def setup_method(self):
        self.config = load_config("alaska")
        self.tech_model = TechnologyModel(self.config)
        self.resource_data = ResourceData(
            wind_speed=np.full(8760, 8.0),
            solar_irradiance=np.full(8760, 200.0),
            wave_height=np.full(8760, 1.5),
            wave_period=np.full(8760, 6.0),
            temperature=np.full(8760, 5.0),
            timestamps=np.arange(8760),
        )

    def test_hydro_performance_calculation_does_not_raise(self):
        performance = self.tech_model.calculate_performance(
            {"hydro_capacity": 0.5},
            self.resource_data,
        )
        assert performance["hydro_capacity_factor"] >= 0.0
        assert performance["hydro_annual_energy"] >= 0.0

    def test_hydro_profile_combines_with_non_8760_length_resource_data(self):
        """Regression test: hydro's generation_profile was hardcoded to length
        8760, which broke combination with other techs' profiles (sized from
        the actual resource_data) whenever resource data wasn't exactly 8760
        timesteps long (e.g. 8761, as produced by the synthetic data generator)."""
        resource_data = ResourceData(
            wind_speed=np.full(8761, 8.0),
            solar_irradiance=np.full(8761, 200.0),
            wave_height=np.full(8761, 1.5),
            wave_period=np.full(8761, 6.0),
            temperature=np.full(8761, 5.0),
            timestamps=np.arange(8761),
        )
        performance = self.tech_model.calculate_performance(
            {"wind_capacity": 0.5, "hydro_capacity": 0.5},
            resource_data,
        )
        assert performance["capacity_factor"] >= 0.0
