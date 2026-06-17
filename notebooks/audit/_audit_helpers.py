"""Shared helpers for FlexiMORP calculation audit notebooks."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


def _find_repo_root() -> Path:
    for candidate in [Path.cwd(), *Path.cwd().parents]:
        if (candidate / "fleximorpv2").is_dir() and (candidate / "notebooks").is_dir():
            return candidate
    raise RuntimeError(
        "Could not find fleximorp-project root. "
        "Open Jupyter from the repo or notebooks/ directory."
    )


REPO_ROOT = _find_repo_root()
AUDIT_DIR = REPO_ROOT / "notebooks" / "audit"
OUTPUT_DIR = AUDIT_DIR / "outputs"
SITE_OUTPUT_DIR = REPO_ROOT / "notebooks" / "sites" / "outputs"

for path in (REPO_ROOT, AUDIT_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

OUTPUT_DIR.mkdir(exist_ok=True)
SITE_OUTPUT_DIR.mkdir(exist_ok=True)


def reload_fleximorp() -> None:
    """Clear cached fleximorpv2 modules when iterating on library code."""
    to_remove = [key for key in sys.modules if key.startswith("fleximorpv2")]
    for key in to_remove:
        del sys.modules[key]


def assert_close(actual: float, expected: float, *, label: str, rtol: float = 1e-4) -> None:
    """Assert two floats match within relative tolerance."""
    if not np.isfinite(actual) or not np.isfinite(expected):
        raise AssertionError(f"{label}: non-finite values actual={actual}, expected={expected}")
    if expected == 0:
        if abs(actual) > rtol:
            raise AssertionError(f"{label}: expected 0, got {actual}")
        return
    rel_err = abs(actual - expected) / abs(expected)
    if rel_err > rtol:
        raise AssertionError(
            f"{label}: actual={actual:.6g}, expected={expected:.6g}, rel_err={rel_err:.2e}"
        )
    print(f"PASS {label}: {actual:.6g} ≈ {expected:.6g}")


def assert_energy_balance(
    annual_energy_mwh: float,
    capacity_mw: float,
    capacity_factor: float,
    *,
    label: str = "energy balance",
    tolerance: float = 0.05,
) -> None:
    """annual_energy ≈ CF × capacity × 8760."""
    if capacity_mw <= 0:
        raise AssertionError(f"{label}: capacity must be positive, got {capacity_mw}")
    expected = capacity_factor * capacity_mw * 8760.0
    rel_err = abs(annual_energy_mwh - expected) / expected if expected else float("inf")
    if rel_err > tolerance:
        raise AssertionError(
            f"{label}: annual_energy={annual_energy_mwh}, "
            f"CF×cap×8760={expected}, rel_err={rel_err:.2%}"
        )
    print(f"PASS {label}: {annual_energy_mwh:.1f} MWh/yr")


def assert_cf_bounds(capacity_factor: float, *, label: str = "capacity factor") -> None:
    if not 0 <= capacity_factor <= 1.01:
        raise AssertionError(f"{label}: CF={capacity_factor} outside [0, 1]")
    print(f"PASS {label}: {capacity_factor:.3f}")


def assert_positive(value: float, *, label: str) -> None:
    if value <= 0:
        raise AssertionError(f"{label}: expected > 0, got {value}")
    print(f"PASS {label}: {value:.6g}")
