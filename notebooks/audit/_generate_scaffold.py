#!/usr/bin/env python3
"""Generate FlexiMORP audit notebook scaffolds."""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent


def md(text: str) -> dict:
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


NOTEBOOK_INTRO = (
    "Run cells **top to bottom**. Each markdown cell explains the **next code cell** — "
    "what it does, what to inspect in the output, and what counts as a pass.\n\n"
    "Track overall audit progress in Obsidian (`FlexiMORP Calculation Audit.md`). "
    "These notebooks are the lab workbook, not the checklist."
)


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


def audit_title(heading: str, module: str, purpose: str) -> str:
    return (
        f"# {heading}\n\n"
        f"**Code under test:** `{module}`\n\n"
        f"**Purpose:** {purpose}\n\n"
        f"{NOTEBOOK_INTRO}"
    )


AUDIT_NOTEBOOKS = {
    "01_financial_primitives.ipynb": {
        "title": audit_title(
            "01 — Financial primitives",
            "fleximorpv2/utils/financial.py",
            "Confirm NPV, IRR, LCOE, and payback match hand calculations before trusting pipeline results.",
        ),
        "sections": [
            (
                "## Step 1 — Golden-case LCOE\n\n"
                "**Run the next cell** after filling in `EXPECTED` from your hand calculation.\n\n"
                "Use this toy project (flat inputs, no tax complexity):\n\n"
                "| Input | Value |\n"
                "|-------|-------|\n"
                "| CAPEX | £1,000,000 |\n"
                "| OPEX | £50,000 / yr (flat) |\n"
                "| Annual energy | 10,000 MWh / yr (flat, no degradation first) |\n"
                "| Discount rate | 8% |\n"
                "| Project life | 20 years |\n\n"
                "**Formula:** LCOE = (CAPEX + Σ OPEX/(1+r)^t) / Σ Energy/(1+r)^t\n\n"
                "**Pass if:** `assert_close` within 0.01% of your spreadsheet.\n\n"
                "**Then:** repeat with degradation enabled in `calculate_lcoe` (hard-coded 0.5%/yr) — LCOE should increase slightly.\n\n"
                "**Also inspect:** `calculate_metrics()` — if `annual_energy` is omitted it guesses from `revenue / 0.1`. List any callers that hit this path.",
                code(
                    """from fleximorpv2.config import load_config
from fleximorpv2.utils.financial import FinancialCalculator

config = load_config("alaska")
calc = FinancialCalculator(config)

# Hand-compute LCOE for the table above, then set:
EXPECTED = None  # £/MWh

capex = 1_000_000
opex = 50_000
annual_energy = 10_000  # MWh/yr
discount_rate = 0.08
project_life = 20

lcoe = calc.calculate_lcoe(capex, opex, annual_energy, discount_rate, project_life)

if EXPECTED is None:
    raise ValueError("Set EXPECTED from your hand calculation, then re-run")
assert_close(lcoe, EXPECTED, label="LCOE golden case")
print(f"LCOE = {lcoe:.2f} £/MWh")"""
                ),
            ),
            (
                "## Step 2 — NPV and IRR on a 3-year toy cash flow\n\n"
                "**Run the next cell** with a simple cash flow you can replicate in Excel (`=NPV`, `=IRR`).\n\n"
                "**Pass if:** NPV sign is correct (−CAPEX at year 0, inflows discounted from year 1) and IRR within 0.1 pp of spreadsheet.",
                code(
                    """cash_flows = np.array([120_000, 130_000, 140_000])  # years 1–3
initial_investment = 300_000
discount_rate = 0.08

npv = calc.calculate_npv(cash_flows, discount_rate, initial_investment)
irr = calc.calculate_irr(cash_flows, initial_investment)

print(f"NPV = {npv:,.0f}")
print(f"IRR = {irr:.2%}")
# TODO: set EXPECTED_NPV / EXPECTED_IRR from spreadsheet and assert_close"""
                ),
            ),
            (
                "## Step 3 — Sensitivity (direction checks)\n\n"
                "**Run the next cell** to plot LCOE vs CAPEX and vs annual energy.\n\n"
                "**Pass if:** LCOE rises when CAPEX rises or energy falls (monotonic, no sign inversions).",
                code(
                    """capex_range = np.linspace(0.5e6, 2.0e6, 20)
lcoe_vs_capex = [
    calc.calculate_lcoe(c, 50_000, 10_000, 0.08, 20) for c in capex_range
]

energy_range = np.linspace(5_000, 20_000, 20)
lcoe_vs_energy = [
    calc.calculate_lcoe(1e6, 50_000, e, 0.08, 20) for e in energy_range
]

fig, axes = plt.subplots(1, 2, figsize=(10, 4))
axes[0].plot(capex_range / 1e6, lcoe_vs_capex)
axes[0].set(xlabel="CAPEX (£M)", ylabel="LCOE (£/MWh)", title="Higher CAPEX → higher LCOE")
axes[1].plot(energy_range, lcoe_vs_energy)
axes[1].set(xlabel="Annual energy (MWh/yr)", ylabel="LCOE (£/MWh)", title="More energy → lower LCOE")
plt.tight_layout()
plt.show()"""
                ),
            ),
        ],
    },
    "02_wind_power_curve.ipynb": {
        "title": audit_title(
            "02 — Wind power curve",
            "fleximorpv2/models/technologies.py",
            "Verify `_wind_power_curve` and capacity-factor logic for offshore wind.",
        ),
        "sections": [
            (
                "## Step 1 — Power curve shape\n\n"
                "**Run the next cell** to print normalised power at key wind speeds (Blyth config defaults: cut-in 3 m/s, rated 12 m/s, cut-out 25 m/s).\n\n"
                "**Pass if:**\n"
                "- 0 power below cut-in and above cut-out\n"
                "- Cubic rise between cut-in and rated (~0.125 at mid-point speed 7.5 m/s)\n"
                "- 1.0 (rated) from rated speed to cut-out",
                code(
                    """from fleximorpv2.config import load_config
from fleximorpv2.models.technologies import TechnologyModel

config = load_config("blyth")
model = TechnologyModel(config)
params = model.technology_params["wind"]

for speed in [0, 2, 3, 7.5, 12, 20, 25, 26]:
    p = model._wind_power_curve(speed, params)
    print(f"{speed:4.1f} m/s → {p:.3f} (normalised)")"""
                ),
            ),
            (
                "## Step 2 — Constant-wind capacity factor\n\n"
                "**Run the next cell** with synthetic `ResourceData` (constant 8 m/s, 8760 hours).\n\n"
                "**Pass if:** CF is between 0.25 and 0.55 after wake loss (15%) and availability; "
                "`annual_energy ≈ CF × capacity × 8760` MWh/yr.",
                code(
                    """from fleximorpv2.models.technologies import ResourceData

n = 8760
resource = ResourceData(
    wind_speed=np.full(n, 8.0),
    solar_irradiance=np.zeros(n),
    wave_height=np.zeros(n),
    wave_period=np.zeros(n),
    temperature=np.full(n, 10.0),
    timestamps=np.arange(n),
)
design = {"wind_capacity": 1.0, "solar_capacity": 0.0, "wave_capacity": 0.0}
perf = model.calculate_performance(design, resource)

print(perf)
assert_energy_balance(perf["annual_energy"], perf["total_capacity"], perf["capacity_factor"])"""
                ),
            ),
        ],
    },
    "03_solar_and_degradation.ipynb": {
        "title": audit_title(
            "03 — Solar output",
            "fleximorpv2/models/technologies.py",
            "Verify irradiance, temperature derating, and Alaska ice/seasonal modifiers.",
        ),
        "sections": [
            (
                "## Step 1 — Temperature derating direction\n\n"
                "**Run the next cell** with identical irradiance but two temperatures (0°C vs 35°C).\n\n"
                "**Pass if:** colder run produces **more** annual energy (temp coefficient is −0.004/°C).",
                code(
                    """from fleximorpv2.config import load_config
from fleximorpv2.models.technologies import TechnologyModel, ResourceData

config = load_config("alaska")
model = TechnologyModel(config)
n = 8760
irradiance = np.full(n, 200.0)  # W/m²


def solar_energy(temp_c: float) -> float:
    resource = ResourceData(
        wind_speed=np.zeros(n),
        solar_irradiance=irradiance,
        wave_height=np.zeros(n),
        wave_period=np.zeros(n),
        temperature=np.full(n, temp_c),
        timestamps=np.arange(n),
    )
    design = {"wind_capacity": 0.0, "solar_capacity": 1.0, "hydro_capacity": 0.0}
    return model.calculate_performance(design, resource)["annual_energy"]


cold = solar_energy(0.0)
hot = solar_energy(35.0)
print(f"Cold (0°C):  {cold:.0f} MWh/yr")
print(f"Hot (35°C):  {hot:.0f} MWh/yr")
assert cold > hot, "Expected colder site to outperform hot site at same irradiance"
print("PASS temperature derating direction")"""
                ),
            ),
        ],
    },
    "04_wave_and_hydro.ipynb": {
        "title": audit_title(
            "04 — Wave and hydro",
            "fleximorpv2/models/technologies.py",
            "Verify site-appropriate technologies: wave on Blyth, hydro on Alaska/Eastport.",
        ),
        "sections": [
            (
                "## Step 1 — Enabled technologies match each site\n\n"
                "**Run the next cell.**\n\n"
                "**Pass if:** Blyth includes `wave`; Alaska and Eastport include `hydro` (river/tidal) and not wave as primary.",
                code(
                    """from fleximorpv2.config import load_config

for site in ("blyth", "alaska", "eastport"):
    techs = load_config(site).get_enabled_technologies()
    print(f"{site}: {techs}")"""
                ),
            ),
            (
                "## Step 2 — Wave / hydro performance smoke test\n\n"
                "**Run the next cell** after building synthetic resource arrays.\n\n"
                "**Pass if:** outputs are finite, non-negative, and CF stays in [0, 1].",
                code(
                    """# TODO: build ResourceData with wave_height/period for Blyth
# and river flow proxy for Alaska hydro; print TechnologyPerformance
raise NotImplementedError("Add wave (Blyth) and hydro (Alaska) golden cases")"""
                ),
            ),
        ],
    },
    "05_platform_sizing.ipynb": {
        "title": audit_title(
            "05 — Platform sizing",
            "fleximorpv2/models/platform.py",
            "Check platform area, load limits, and depth-driven platform type.",
        ),
        "sections": [
            (
                "## Step 1 — Design platform from sample variables\n\n"
                "**Run the next cell** with a fixed design dict.\n\n"
                "**Pass if:** `design_platform` returns specs without error; footprint scales with area; "
                "document that `load_utilization=0.8` in platform.py is a placeholder, not measured load.",
                code(
                    """from fleximorpv2.config import load_config
from fleximorpv2.models.platform import PlatformModel

config = load_config("blyth")
platform = PlatformModel(config)
design_vars = {
    "wind_capacity": 50.0,
    "solar_capacity": 10.0,
    "wave_capacity": 5.0,
    "platform_area": 50_000,
    "water_depth": 35,
    "distance_to_shore": 5,
}
tech_perf = {"total_load_requirement": 8000, "total_space_requirement": 40_000}
specs = platform.design_platform(design_vars, tech_perf)
print(specs)"""
                ),
            ),
        ],
    },
    "06_cost_stack.ipynb": {
        "title": audit_title(
            "06 — Cost stack",
            "fleximorpv2/models/economics.py",
            "Reconcile CAPEX/OPEX components and flag placeholder revenue logic.",
        ),
        "sections": [
            (
                "## Step 1 — Cost breakdown sums\n\n"
                "**Run the next cell** with a fixed design + performance dict.\n\n"
                "**Pass if:**\n"
                "- `total_capex` equals sum of technology + platform + installation + grid + development lines\n"
                "- Grid cost grows when `distance_to_shore` increases\n"
                "- Note: `generation_profile=np.ones(8760)` is a placeholder — revenue timing is not hourly-realistic",
                code(
                    """from fleximorpv2.config import load_config
from fleximorpv2.models.economics import EconomicModel

config = load_config("eastport")
economics = EconomicModel(config)
design_vars = {"platform_area": 10_000, "water_depth": 30, "distance_to_shore": 2}
tech_perf = {
    "total_technology_capex": 2e7,
    "total_technology_opex": 4e5,
    "annual_energy": 50_000,
}
metrics = economics.calculate_economics(design_vars, tech_perf)
print({k: v for k, v in metrics.items() if "capex" in k or "opex" in k or k in ("capex", "opex")})
# TODO: assert component sum == metrics["capex"]"""
                ),
            ),
        ],
    },
    "07_uncertainty_sampling.ipynb": {
        "title": audit_title(
            "07 — Uncertainty sampling",
            "fleximorpv2/uncertainty_analysis.py",
            "Compare Monte Carlo vs Latin Hypercube and confirm scenarios move LCOE.",
        ),
        "sections": [
            (
                "## Step 1 — Sampling method comparison\n\n"
                "**Run the next cell** (small `n_runs=50` for speed).\n\n"
                "**Pass if:**\n"
                "- Both methods complete without error\n"
                "- LCOE distribution has non-zero spread when uncertainty params are enabled\n"
                "- LHS mean LCOE is in the same ballpark as MC (not identical, but same order of magnitude)",
                code(
                    """from fleximorpv2.config import load_config
from fleximorpv2.baseline_optimization import BaselineOptimization
from fleximorpv2.uncertainty_analysis import UncertaintyAnalysis

config = load_config("alaska")
config.uncertainty["monte_carlo_runs"] = 50
baseline = BaselineOptimization(config).optimize("production", 200_000, method="scipy")
analyzer = UncertaintyAnalysis(config)

comparison = analyzer.compare_sampling_methods(
    baseline_design=baseline.optimal_design,
    n_runs=50,
)
print(comparison["convergence_analysis"])"""
                ),
            ),
        ],
    },
    "08_optimization_sanity.ipynb": {
        "title": audit_title(
            "08 — Baseline optimization",
            "fleximorpv2/baseline_optimization.py",
            "Smoke-test the optimizer on Alaska and inspect constraints.",
        ),
        "sections": [
            (
                "## Step 1 — Run baseline optimize\n\n"
                "**Run the next cell.**\n\n"
                "Uses `target_type='production'`, `target_value=200_000`. "
                "The code comments say **kWh**; `TechnologyModel` reports **MWh/yr** — compare printed "
                "`annual_energy` to the target and note whether units align.\n\n"
                "**Pass if:**\n"
                "- Optimisation completes without exception\n"
                "- LCOE > 0\n"
                "- Total capacity ≤ config max (Alaska: 2 MW)\n"
                "- CapEx within budget if config sets one",
                code(
                    """from fleximorpv2.config import load_config
from fleximorpv2.baseline_optimization import BaselineOptimization

config = load_config("alaska")
config.uncertainty["monte_carlo_runs"] = 10
opt = BaselineOptimization(config)
results = opt.optimize("production", 200_000, method="scipy")

assert_positive(results.financial_metrics["lcoe"], label="LCOE")
print("Target production (as passed):", 200_000)
print("Annual energy (engine output):", results.technical_metrics["annual_energy"])
print("Financial:", results.financial_metrics)
print("Technical:", results.technical_metrics)
print("Capacities:", results.technology_capacities)"""
                ),
            ),
        ],
    },
    "09_cross_module_consistency.ipynb": {
        "title": audit_title(
            "09 — Cross-module consistency",
            "baseline pipeline + webapp/app.py",
            "Check that energy, LCOE, and capacity metrics agree across layers.",
        ),
        "sections": [
            (
                "## Step 1 — Energy balance on baseline result\n\n"
                "**Run the next cell.**\n\n"
                "**Pass if:** `annual_energy ≈ capacity_factor × total_capacity × 8760` (within 5%).\n\n"
                "If this fails with `annual_energy=0`, the bug is in technology/economic coupling — log it in Obsidian findings.",
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
print("Financial:", results.financial_metrics)
print("Technical:", results.technical_metrics)"""
                ),
            ),
            (
                "## Step 2 — Manual LCOE cross-check\n\n"
                "**Run the next cell** after computing LCOE from CAPEX, OPEX, and energy independently.\n\n"
                "**Pass if:** manual LCOE within ~10% of `results.financial_metrics['lcoe']` (wider tolerance until cost stack is validated in notebook 06).",
                code(
                    """# TODO: pull capex/opex/energy from results or cost_breakdown and compare LCOE
manual_lcoe = None  # £/MWh from notebook 06 logic
reported = results.financial_metrics["lcoe"]
print(f"Reported LCOE: {reported:.2f} £/MWh")
if manual_lcoe is not None:
    assert_close(reported, manual_lcoe, label="LCOE cross-check", rtol=0.10)"""
                ),
            ),
        ],
    },
}

SITE_DETAILS = {
    "alaska": {
        "place": "Igiugig, Alaska (riverine)",
        "techs": "wind, solar, hydro",
        "resource_note": "Expect synthetic wind, solar irradiance, and temperature. No wave array.",
        "context": "Remote river community — check arctic cost premiums and low capacity limits (2 MW max).",
    },
    "blyth": {
        "place": "Blyth, UK North Sea (offshore)",
        "techs": "wind, solar, wave",
        "resource_note": "Expect wind, solar, **and wave** statistics from the data loader.",
        "context": "Commercial offshore scale — capacity bounds up to hundreds of MW in config.",
    },
    "eastport": {
        "place": "Eastport, Maine (nearshore)",
        "techs": "wind, solar, hydro (tidal / ORPC TidGen)",
        "resource_note": "Wave is disabled in config; hydro represents tidal stream.",
        "context": "Fishing-industry constraints — verify tidal/hydro CF is plausible, not wave.",
    },
}


def site_notebook(meta: dict) -> dict:
    site = meta["site"]
    info = SITE_DETAILS[site]
    return notebook(
        md(
            f"# {info['place']} — site pipeline\n\n"
            f"**Config:** `data/{site}/config.yaml`\n\n"
            f"**Technologies:** {info['techs']}\n\n"
            f"{info['context']}\n\n"
            f"{NOTEBOOK_INTRO}\n\n"
            "**Important:** Do not catch errors and substitute dummy numbers (unlike `notebooks/alaska_analysis.ipynb`)."
        ),
        SETUP,
        md(
            f"## Step 1 — Load and validate config\n\n"
            f"**Run the next cell** to load `data/{site}/config.yaml`.\n\n"
            f"**Pass if:** `validate_config()` succeeds and enabled techs are `{info['techs']}`."
        ),
        code(
            f"""from fleximorpv2.config import load_config, validate_config

config = load_config("{site}")
validate_config(config)
print(f"Site: {{config.name}}")
print(f"Coords: {{config.coordinates}}")
print(f"Techs: {{config.get_enabled_technologies()}}")
print(f"Discount rate: {{config.economic.get('discount_rate')}}")
print(f"Max capacity (config): {{config.optimization.get('constraints', {{}}).get('max_total_capacity', 'not set')}}")"""
        ),
        md(
            f"## Step 2 — Inspect synthetic resource data\n\n"
            f"**Run the next cell.** {info['resource_note']}\n\n"
            f"**Pass if:** means are finite and physically plausible for the site (print values and judge — no API keys required)."
        ),
        code(
            """from fleximorpv2.utils.data_loader import APIDataLoader

loader = APIDataLoader(config)
resource = loader.load_weather_data(
    coordinates=config.coordinates,
    technologies=config.get_enabled_technologies(),
)
print("Wind mean (m/s):", float(resource.wind_speed.mean()))
print("Solar mean (W/m²):", float(resource.solar_irradiance.mean()))
if len(resource.wave_height):
    print("Wave Hs mean (m):", float(resource.wave_height.mean()))
print("Temperature mean (°C):", float(resource.temperature.mean()))"""
        ),
        md(
            "## Step 3 — Baseline optimization\n\n"
            "**Run the next cell.**\n\n"
            "Compare `target_value=200_000` to printed `annual_energy` — confirm whether the engine treats both as kWh or MWh (see notebook 08).\n\n"
            "**Pass if:** optimisation completes, LCOE > 0, and capacity respects config limits."
        ),
        code(
            """from fleximorpv2.baseline_optimization import BaselineOptimization

config.uncertainty["monte_carlo_runs"] = 10
results = BaselineOptimization(config).optimize("production", 200_000, method="scipy")

assert_positive(results.financial_metrics["lcoe"], label="LCOE")
print("Target:", 200_000, "| Annual energy:", results.technical_metrics["annual_energy"])
print("Financial:", results.financial_metrics)
print("Technical:", results.technical_metrics)
print("Capacities:", results.technology_capacities)
optimal_design = results.optimal_design"""
        ),
        md(
            "## Step 4 — Uncertainty (Monte Carlo)\n\n"
            "**Run the next cell** with `n_runs=50` for a quick pass; re-run locally with 500 for convergence.\n\n"
            "**Pass if:** mean LCOE is same order of magnitude as baseline LCOE."
        ),
        code(
            """from fleximorpv2.uncertainty_analysis import UncertaintyAnalysis

analyzer = UncertaintyAnalysis(config)
uncertainty = analyzer.analyze_uncertainty(
    baseline_design=optimal_design,
    sampling_method="monte_carlo",
    reoptimize=False,
)
print("Baseline LCOE:", results.financial_metrics["lcoe"])
print("Mean LCOE under uncertainty:", uncertainty.mean_performance.get("lcoe"))
print("Risk metrics:", uncertainty.risk_metrics)"""
        ),
        md(
            "## Step 5 — Optional extensions\n\n"
            "Run only after Steps 1–4 pass:\n"
            "- `fleximorpv2/flexible_design.py` — real options value should be ≥ 0\n"
            "- `fleximorpv2/sensitivity_analysis.py` — parameter rankings stable across two runs\n"
            "- Save plots to `notebooks/sites/outputs/`"
        ),
        code("# Optional — flexible design and sensitivity\n"),
    )


SITE_NOTEBOOKS = {
    "alaska_pipeline.ipynb": {"site": "alaska"},
    "blyth_pipeline.ipynb": {"site": "blyth"},
    "eastport_pipeline.ipynb": {"site": "eastport"},
}


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
        path.write_text(json.dumps(site_notebook(meta), indent=1) + "\n")
        print(f"Wrote {path.relative_to(REPO)}")


if __name__ == "__main__":
    main()
