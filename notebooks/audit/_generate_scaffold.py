#!/usr/bin/env python3
"""Generate FlexiMORP audit notebook scaffolds."""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent


def md(text: str) -> dict:
    # Generator strings use "\\n" placeholders; convert to real newlines for rendering.
    text = text.replace("\\n", "\n")
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


def notebook(*cells) -> dict:
    return {
        "cells": list(cells),
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11.0"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


SETUP = code(
    """import sys
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("error", category=RuntimeWarning)


def _repo_root() -> Path:
    for candidate in [Path.cwd(), *Path.cwd().parents]:
        if (candidate / "fleximorpv2").is_dir():
            return candidate
    raise RuntimeError(
        "Could not find fleximorp-project root. "
        "Open Jupyter from the repo or a notebooks/ subdirectory."
    )


_repo = _repo_root()
_audit = _repo / "notebooks" / "audit"
for path in (_repo, _audit):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from _audit_helpers import (
    REPO_ROOT,
    OUTPUT_DIR,
    SITE_OUTPUT_DIR,
    reload_fleximorp,
    assert_close,
    assert_energy_balance,
    assert_cf_bounds,
    assert_positive,
)

reload_fleximorp()
np.random.seed(42)
print(f"Repo root: {REPO_ROOT}")
print(f"Audit outputs: {OUTPUT_DIR}")
print(f"Site outputs: {SITE_OUTPUT_DIR}")"""
)

AUDIT_NOTEBOOKS = {
    "01_financial_primitives.ipynb": {
        "title": "# 01 — Financial Primitives\\n\\n**Module:** `fleximorpv2/utils/financial.py`\\n\\nHand-verify NPV, IRR, LCOE, and payback on toy projects before trusting pipeline outputs.",
        "sections": [
            ("## Checklist\\n\\n- [ ] NPV sign convention (−CAPEX at t=0)\\n- [ ] IRR matches spreadsheet on 3-year toy cash flow\\n- [ ] LCOE = PV(costs) / PV(generation) without degradation\\n- [ ] LCOE rises when degradation is enabled\\n- [ ] Trace callers that omit `annual_energy` (revenue/0.1 fallback)\\n- [ ] Payback interpolation at fractional year",
             code(
                 """from fleximorpv2.config import load_config
from fleximorpv2.utils.financial import FinancialCalculator

config = load_config("alaska")
calc = FinancialCalculator(config)

# TODO: toy case — CAPEX=1e6, OPEX=50e3/yr, energy=10_000 MWh/yr, r=8%, life=20
# Hand-compute expected LCOE in markdown above, then:
# lcoe = calc.calculate_lcoe(capex=..., opex=..., annual_energy=..., discount_rate=0.08, project_life=20)
# assert_close(lcoe, EXPECTED, label="LCOE golden case")

raise NotImplementedError("Complete golden-case calculations and remove this line")"""
             )),
            ("## Sensitivity plots\\n\\n- [ ] Higher CAPEX → higher LCOE\\n- [ ] Lower annual energy → higher LCOE",
             code("# TODO: sweep one parameter at a time and plot\npass")),
        ],
    },
    "02_wind_power_curve.ipynb": {
        "title": "# 02 — Wind Power Curve\\n\\n**Module:** `fleximorpv2/models/technologies.py`\\n\\nVerify cut-in/rated/cut-out behaviour and capacity factor vs wind speed.",
        "sections": [
            ("## Checklist\\n\\n- [ ] Power = 0 below cut-in and above cut-out\\n- [ ] Cubic ramp between cut-in and rated\\n- [ ] Flat rated output above rated speed\\n- [ ] Wake loss reduces output\\n- [ ] CF monotonic with mean wind (until rated)\\n- [ ] Hub-height shear correction direction",
             code(
                 """from fleximorpv2.config import load_config
from fleximorpv2.models.technologies import TechnologyModel, ResourceData

config = load_config("blyth")
model = TechnologyModel(config)

# TODO: build ResourceData with constant wind speeds and verify power curve points
# speeds = [0, 3, 7.5, 12, 20, 26]
# for v in speeds: print(v, model._wind_power_curve(v, model.technology_params['wind']))

raise NotImplementedError("Add constant-wind ResourceData test")"""
             )),
        ],
    },
    "03_solar_and_degradation.ipynb": {
        "title": "# 03 — Solar & Degradation\\n\\n**Module:** `fleximorpv2/models/technologies.py`\\n\\nIrradiance, temperature derating, deployment type, seasonal ice factor.",
        "sections": [
            ("## Checklist\\n\\n- [ ] Hotter temperature → lower output (negative temp coeff)\\n- [ ] Higher irradiance → higher output\\n- [ ] Alaska seasonal ice factor reduces winter output\\n- [ ] Land vs floating deployment modifiers\\n- [ ] annual_energy = CF × capacity × 8760",
             code(
                 """from fleximorpv2.config import load_config
from fleximorpv2.models.technologies import TechnologyModel

config = load_config("alaska")
model = TechnologyModel(config)

# TODO: synthetic ResourceData with controlled irradiance/temperature/timestamps
raise NotImplementedError("Add solar golden cases")"""
             )),
        ],
    },
    "04_wave_and_hydro.ipynb": {
        "title": "# 04 — Wave & Hydro\\n\\n**Module:** `fleximorpv2/models/technologies.py`\\n\\nWave height/period curve and river hydro assumptions.",
        "sections": [
            ("## Checklist\\n\\n- [ ] Wave power peaks near optimal Hs/Tp\\n- [ ] Zero or reduced output above max operational height\\n- [ ] Hydro CF plausible for riverine sites\\n- [ ] Enabled tech matches site config (wave=Blyth, hydro=Alaska/Eastport)",
             code(
                 """from fleximorpv2.config import load_config

blyth = load_config("blyth")
alaska = load_config("alaska")
print("Blyth techs:", blyth.get_enabled_technologies())
print("Alaska techs:", alaska.get_enabled_technologies())

# TODO: wave performance with synthetic wave_height / wave_period arrays
raise NotImplementedError("Add wave/hydro golden cases")"""
             )),
        ],
    },
    "05_platform_sizing.ipynb": {
        "title": "# 05 — Platform Sizing\\n\\n**Module:** `fleximorpv2/models/platform.py`\\n\\nArea, load limits, depth constraints, footprint.",
        "sections": [
            ("## Checklist\\n\\n- [ ] Platform area scales with technology space requirements\\n- [ ] Load utilization placeholder (0.8) documented\\n- [ ] Water depth selects platform type\\n- [ ] Infeasible designs flagged (overload / too shallow)",
             code(
                 """from fleximorpv2.config import load_config
from fleximorpv2.models.platform import PlatformModel

config = load_config("blyth")
platform = PlatformModel(config)

# TODO: design_vars sweep — area vs total_load_requirement
raise NotImplementedError("Add platform sizing checks")"""
             )),
        ],
    },
    "06_cost_stack.ipynb": {
        "title": "# 06 — Cost Stack\\n\\n**Module:** `fleximorpv2/models/economics.py`\\n\\nCAPEX/OPEX breakdown, subsidies, grid connection costs.",
        "sections": [
            ("## Checklist\\n\\n- [ ] total_capex equals sum of components\\n- [ ] Installation 25% applied to tech CAPEX only\\n- [ ] Development 15% base documented\\n- [ ] Grid £/km scales with distance_to_shore\\n- [ ] Placeholder hourly generation profile noted as limitation",
             code(
                 """from fleximorpv2.config import load_config
from fleximorpv2.models.economics import EconomicModel

config = load_config("eastport")
economics = EconomicModel(config)

# TODO: fixed design_vars + tech_performance dict; verify cost breakdown sums
raise NotImplementedError("Add cost stack reconciliation")"""
             )),
        ],
    },
    "07_uncertainty_sampling.ipynb": {
        "title": "# 07 — Uncertainty Sampling\\n\\n**Module:** `fleximorpv2/uncertainty_analysis.py`\\n\\nMonte Carlo vs LHS, VaR/CVaR, scenario perturbations.",
        "sections": [
            ("## Checklist\\n\\n- [ ] MC histograms match configured distributions\\n- [ ] LHS covers space better than MC (fewer samples)\\n- [ ] VaR/CVaR definitions correct (95th percentile)\\n- [ ] Perturbations change LCOE (not cosmetic)\\n- [ ] `success_rate = 1.0` placeholder flagged",
             code(
                 """from fleximorpv2.config import load_config
from fleximorpv2.uncertainty_analysis import UncertaintyAnalysis

config = load_config("alaska")
config.uncertainty["monte_carlo_runs"] = 50
analyzer = UncertaintyAnalysis(config)

# TODO: compare_sampling_methods with small n_runs; plot LCOE distributions
raise NotImplementedError("Add sampling verification")"""
             )),
        ],
    },
    "08_optimization_sanity.ipynb": {
        "title": "# 08 — Optimization Sanity\\n\\n**Module:** `fleximorpv2/baseline_optimization.py`\\n\\nObjective sign, constraints, monotonicity sweeps.",
        "sections": [
            ("## Checklist\\n\\n- [ ] Optimal LCOE ≤ random nearby designs\\n- [ ] Production target enforced\\n- [ ] Max capacity respected\\n- [ ] Sweep one capacity variable — LCOE has sensible shape\\n- [ ] differential_evolution vs scipy within tolerance",
             code(
                 """from fleximorpv2.config import load_config
from fleximorpv2.baseline_optimization import BaselineOptimization

config = load_config("alaska")
config.uncertainty["monte_carlo_runs"] = 10
opt = BaselineOptimization(config)

# TODO: run optimize with fixed seed; then compare to perturbed designs
results = opt.optimize("production", 200_000, method="scipy")
assert_positive(results.financial_metrics["lcoe"], label="baseline LCOE")
print(results.financial_metrics)
print(results.technical_metrics)"""
             )),
        ],
    },
    "09_cross_module_consistency.ipynb": {
        "title": "# 09 — Cross-Module Consistency\\n\\nCompare outputs across TechnologyModel, EconomicModel, FinancialCalculator, and Streamlit.",
        "sections": [
            ("## Checklist\\n\\n- [ ] Technology annual_energy matches economic revenue inputs\\n- [ ] LCOE from FinancialCalculator ≈ implied LCOE from cost/energy\\n- [ ] Baseline mean MC LCOE same order of magnitude as baseline\\n- [ ] Document Streamlit vs engine divergences (`webapp/app.py`)",
             code(
                 """from fleximorpv2.config import load_config
from fleximorpv2.baseline_optimization import BaselineOptimization

config = load_config("alaska")
config.uncertainty["monte_carlo_runs"] = 10
results = BaselineOptimization(config).optimize("production", 200_000, method="scipy")

assert_energy_balance(
    results.technical_metrics["annual_energy"],
    results.technical_metrics["total_capacity"],
    results.technical_metrics["capacity_factor"],
)
assert_cf_bounds(results.technical_metrics["capacity_factor"])

# TODO: reconcile LCOE from financial_metrics vs manual cost/energy calculation
print("Financial:", results.financial_metrics)
print("Technical:", results.technical_metrics)"""
             )),
        ],
    },
}

SITE_NOTEBOOKS = {
    "alaska_pipeline.ipynb": {
        "site": "alaska",
        "title": "# Alaska Pipeline — Igiugig\\n\\nEnd-to-end audit for riverine wind/solar/hydro. **No fallback values on failure.**",
    },
    "blyth_pipeline.ipynb": {
        "site": "blyth",
        "title": "# Blyth Pipeline — North Sea Offshore\\n\\nEnd-to-end audit for wind/solar/wave commercial site.",
    },
    "eastport_pipeline.ipynb": {
        "site": "eastport",
        "title": "# Eastport Pipeline — Maine Nearshore\\n\\nEnd-to-end audit for wind/solar/tidal with fishing constraints.",
    },
}


def site_notebook(name: str, meta: dict) -> dict:
    site = meta["site"]
    return notebook(
        md(meta["title"]),
        SETUP,
        md(
            f"## 1. Config audit\\n\\n- [ ] Load `data/{site}/config.yaml`\\n"
            f"- [ ] Validate with `validate_config()`\\n- [ ] Print enabled technologies and economic assumptions"
        ),
        code(
            f"""from fleximorpv2.config import load_config, validate_config

config = load_config("{site}")
validate_config(config)
print(f"Site: {{config.name}}")
print(f"Coords: {{config.coordinates}}")
print(f"Techs: {{config.get_enabled_technologies()}}")
print(f"Discount rate: {{config.economic.get('discount_rate')}}")"""
        ),
        md(
            "## 2. Resource data audit\\n\\n"
            "- [ ] Inspect synthetic weather means (wind, irradiance, wave if applicable)\n"
            "- [ ] Confirm units: m/s, W/m², m, s\n"
            "- [ ] Note whether live API or synthetic path is used"
        ),
        code(
            f"""from fleximorpv2.utils.data_loader import APIDataLoader

loader = APIDataLoader(config)
resource = loader.load_weather_data(
    coordinates=config.coordinates,
    technologies=config.get_enabled_technologies(),
)
print("Wind mean (m/s):", float(resource.wind_speed.mean()))
print("Solar mean (W/m²):", float(resource.solar_irradiance.mean()))
if hasattr(resource, "wave_height") and resource.wave_height is not None:
    print("Wave Hs mean (m):", float(resource.wave_height.mean()))"""
        ),
        md(
            "## 3. Baseline optimization\\n\\n"
            "- [ ] Run with fixed seed / reproducible method\n"
            "- [ ] Record LCOE, NPV, capacities, annual energy\n"
            "- [ ] **Verify production target units (kWh vs MWh)**"
        ),
        code(
            f"""from fleximorpv2.baseline_optimization import BaselineOptimization

config.uncertainty["monte_carlo_runs"] = 10
baseline = BaselineOptimization(config)
results = baseline.optimize("production", 200_000, method="scipy")

assert_positive(results.financial_metrics["lcoe"], label="LCOE")
assert_energy_balance(
    results.technical_metrics["annual_energy"],
    results.technical_metrics["total_capacity"],
    results.technical_metrics["capacity_factor"],
)
print(results.financial_metrics)
print(results.technical_metrics)
print(results.technology_capacities)
optimal_design = results.optimal_design"""
        ),
        md(
            "## 4. Uncertainty analysis\\n\\n"
            "- [ ] Monte Carlo n=50 then n=500 locally\n"
            "- [ ] Latin Hypercube comparison\n"
            "- [ ] Mean LCOE same order of magnitude as baseline"
        ),
        code(
            """from fleximorpv2.uncertainty_analysis import UncertaintyAnalysis

analyzer = UncertaintyAnalysis(config)
uncertainty = analyzer.analyze_uncertainty(
    baseline_design=optimal_design,
    sampling_method="monte_carlo",
    reoptimize=False,
)
print(uncertainty.mean_performance)
print(uncertainty.risk_metrics)

# TODO: run latin_hypercube and compare_sampling_methods"""
        ),
        md(
            "## 5. Extended pipeline (optional)\\n\\n"
            "- [ ] Flexible design (`fleximorpv2/flexible_design.py`)\n"
            "- [ ] Sensitivity analysis\n"
            "- [ ] Save plots to `notebooks/sites/outputs/`"
        ),
        code("# TODO: flexible design + sensitivity\npass"),
    )


def main() -> None:
    audit_dir = REPO / "notebooks" / "audit"
    sites_dir = REPO / "notebooks" / "sites"

    for filename, meta in AUDIT_NOTEBOOKS.items():
        cells = [md(meta["title"]), SETUP]
        for section_md, section_code in meta["sections"]:
            cells.extend([md(section_md), section_code])
        path = audit_dir / filename
        path.write_text(json.dumps(notebook(*cells), indent=1) + "\n")
        print(f"Wrote {path.relative_to(REPO)}")

    for filename, meta in SITE_NOTEBOOKS.items():
        path = sites_dir / filename
        path.write_text(json.dumps(site_notebook(filename, meta), indent=1) + "\n")
        print(f"Wrote {path.relative_to(REPO)}")


if __name__ == "__main__":
    main()
