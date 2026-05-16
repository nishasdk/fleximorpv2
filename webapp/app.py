"""
FlexiMORP v2 web application.

Streamlit interface for configuring offshore renewable platform studies,
reviewing scenario assumptions, and exploring analysis outputs.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from html import escape
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))


@dataclass(frozen=True)
class SiteProfile:
    key: str
    label: str
    coordinates: tuple[float, float]
    description: str
    environment_type: str
    water_depth: float
    distance_to_shore: float
    enabled_technologies: tuple[str, ...]
    constraints: tuple[str, ...]
    config: dict[str, Any]


TECH_LABELS = {
    "wind": "Wind",
    "solar": "Solar",
    "wave": "Wave",
    "hydro": "Hydro",
}

TECH_COLORS = {
    "wind": "#2563eb",
    "solar": "#f59e0b",
    "wave": "#0891b2",
    "hydro": "#10b981",
}


def main() -> None:
    st.set_page_config(
        page_title="FlexiMORP v2",
        page_icon="FM",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_styles()

    profiles = load_site_profiles()
    ensure_session_state(profiles)

    render_sidebar(profiles)
    render_header()

    if st.session_state.results is None:
        render_workspace(profiles[st.session_state.site_key])
    else:
        render_dashboard()


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --fm-ink: #172033;
            --fm-muted: #5b667a;
            --fm-line: #d7dde8;
            --fm-panel: #f7f9fc;
            --fm-blue: #1d4ed8;
            --fm-teal: #0f766e;
            --fm-amber: #b45309;
        }
        .block-container {
            padding-top: 3.75rem;
            padding-bottom: 2rem;
            max-width: 1420px;
        }
        [data-testid="stSidebar"] {
            border-right: 1px solid var(--fm-line);
        }
        h1, h2, h3 {
            letter-spacing: 0;
            color: var(--fm-ink);
        }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid var(--fm-line);
            border-radius: 8px;
            color: var(--fm-ink);
            padding: 14px 16px;
            min-height: 104px;
            overflow: hidden;
        }
        div[data-testid="stMetric"] * {
            color: var(--fm-ink) !important;
        }
        div[data-testid="stMetric"] label,
        div[data-testid="stMetric"] [data-testid="stMetricLabel"] * {
            color: var(--fm-muted);
        }
        div[data-testid="stMetricValue"] {
            font-size: clamp(1.25rem, 2vw, 1.85rem);
            line-height: 1.15;
            white-space: normal;
            overflow-wrap: anywhere;
        }
        .fm-hero {
            border-bottom: 1px solid var(--fm-line);
            margin-bottom: 1.1rem;
            padding: .3rem 0 1rem;
        }
        .fm-eyebrow {
            color: var(--fm-teal);
            font-size: .78rem;
            font-weight: 800;
            letter-spacing: .08em;
            text-transform: uppercase;
        }
        .fm-lede {
            color: var(--fm-muted);
            font-size: 1rem;
            max-width: 860px;
        }
        .fm-panel {
            background: var(--fm-panel);
            border: 1px solid var(--fm-line);
            border-radius: 8px;
            color: var(--fm-ink);
            padding: 16px;
        }
        .fm-card {
            background: #ffffff;
            border: 1px solid var(--fm-line);
            border-radius: 8px;
            color: var(--fm-ink);
            padding: 14px 16px;
            height: 100%;
        }
        .fm-panel *,
        .fm-card *,
        .fm-chip,
        .fm-status * {
            color: inherit;
        }
        .fm-card strong {
            color: var(--fm-ink);
        }
        .fm-small {
            color: var(--fm-muted);
            font-size: .86rem;
            line-height: 1.42;
        }
        .fm-chip {
            display: inline-block;
            border: 1px solid var(--fm-line);
            border-radius: 999px;
            padding: 3px 9px;
            margin: 2px 4px 2px 0;
            font-size: .78rem;
            color: var(--fm-ink);
            background: #ffffff;
        }
        .fm-status {
            border-left: 4px solid var(--fm-blue);
            padding: 8px 12px;
            background: #eff6ff;
            color: var(--fm-ink);
            border-radius: 6px;
        }
        .fm-map-wrap,
        .fm-map-wrap > div,
        div[data-testid="stPlotlyChart"],
        div[data-testid="stPlotlyChart"] > div {
            width: 100% !important;
            max-width: none !important;
        }
        .fm-overview-metric {
            background: #ffffff;
            border: 1px solid var(--fm-line);
            border-radius: 8px;
            color: var(--fm-ink);
            min-height: 104px;
            overflow: hidden;
            padding: 14px 16px;
        }
        .fm-overview-metric.warning {
            background: #fff7ed;
            border-color: #f59e0b;
            box-shadow: inset 0 0 0 1px #fed7aa;
        }
        .fm-overview-label {
            align-items: center;
            color: var(--fm-muted);
            display: flex;
            font-size: .88rem;
            font-weight: 600;
            gap: 6px;
            line-height: 1.25;
        }
        .fm-overview-value {
            color: var(--fm-ink);
            font-size: clamp(1.25rem, 2vw, 1.85rem);
            font-weight: 700;
            line-height: 1.15;
            margin-top: 8px;
            overflow-wrap: anywhere;
        }
        .fm-warning-icon {
            color: #b45309;
            cursor: help;
            display: inline-flex;
            font-size: .95rem;
            line-height: 1;
            position: relative;
        }
        .fm-warning-icon::after {
            background: #172033;
            border-radius: 6px;
            bottom: calc(100% + 8px);
            color: #ffffff;
            content: attr(data-tooltip);
            display: none;
            font-size: .78rem;
            font-weight: 500;
            left: 50%;
            line-height: 1.25;
            max-width: 220px;
            min-width: 180px;
            padding: 8px 10px;
            position: absolute;
            transform: translateX(-50%);
            white-space: normal;
            z-index: 9999;
        }
        .fm-warning-icon::before {
            border: 6px solid transparent;
            border-top-color: #172033;
            bottom: calc(100% - 4px);
            content: "";
            display: none;
            left: 50%;
            position: absolute;
            transform: translateX(-50%);
            z-index: 9999;
        }
        .fm-warning-icon:hover::after,
        .fm-warning-icon:hover::before {
            display: block;
        }
        .stButton > button {
            border-radius: 8px;
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def ensure_session_state(profiles: dict[str, SiteProfile]) -> None:
    defaults = {
        "site_key": next(iter(profiles)),
        "results": None,
        "last_run_settings": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def load_site_profiles() -> dict[str, SiteProfile]:
    profiles: dict[str, SiteProfile] = {}
    for key in ("alaska", "blyth", "eastport"):
        raw_config = read_yaml(PROJECT_ROOT / "data" / key / "config.yaml")
        site = raw_config.get("site", {})
        technologies = raw_config.get("technologies", {})
        enabled = tuple(
            name
            for name, data in technologies.items()
            if isinstance(data, dict) and data.get("enabled", False)
        )
        profiles[key] = SiteProfile(
            key=key,
            label=site.get("name", key.title()),
            coordinates=tuple(site.get("coordinates", [0.0, 0.0])),
            description=site.get(
                "description", "Offshore renewable energy study area."
            ),
            environment_type=site.get("environment_type", "marine"),
            water_depth=float(site.get("water_depth", 0.0)),
            distance_to_shore=float(site.get("distance_to_shore", 0.0)),
            enabled_technologies=enabled or ("wind",),
            constraints=extract_constraints(raw_config),
            config=raw_config,
        )

    profiles["custom"] = SiteProfile(
        key="custom",
        label="Custom site",
        coordinates=(55.0, -1.5),
        description="User-defined marine or nearshore development area.",
        environment_type="custom",
        water_depth=30.0,
        distance_to_shore=5.0,
        enabled_technologies=("wind", "solar", "wave"),
        constraints=("User-defined screening", "Early-stage assumptions"),
        config={},
    )
    return profiles


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    return loaded if isinstance(loaded, dict) else {}


def extract_constraints(config: dict[str, Any]) -> tuple[str, ...]:
    location = (
        config.get("design_variables", {}).get("location", {}).get("constraints", {})
    )
    zones = location.get("exclusion_zones", [])
    constraints: list[str] = []
    for zone in zones[:4]:
        if not isinstance(zone, dict):
            continue
        label = zone.get("description") or zone.get("name") or zone.get("type")
        if label:
            constraints.append(str(label))
    return tuple(constraints or ("No major exclusion zones listed",))


def render_sidebar(profiles: dict[str, SiteProfile]) -> None:
    with st.sidebar:
        site_options = list(profiles.keys())
        selected_site = st.session_state.site_key
        st.subheader("Study Setup")
        for site_key in site_options:
            is_selected = site_key == selected_site
            st.button(
                profiles[site_key].label,
                key=f"site_button_{site_key}",
                type="primary" if is_selected else "secondary",
                use_container_width=True,
                on_click=select_site,
                args=(site_key,),
            )

        profile = profiles[selected_site]

        with st.expander("Location", expanded=selected_site == "custom"):
            if selected_site == "custom":
                if st.button(
                    "Default", key="default_location", use_container_width=True
                ):
                    st.session_state.custom_latitude = profile.coordinates[0]
                    st.session_state.custom_longitude = profile.coordinates[1]
                    st.session_state.custom_water_depth = profile.water_depth
                    st.session_state.custom_distance_to_shore = (
                        profile.distance_to_shore
                    )
                    clear_results()

                location_query = st.text_input(
                    "Search coastal/ocean area",
                    placeholder="e.g. Moray Firth, Scotland",
                    key="custom_location_query",
                )
                st.caption(
                    "Beta: search and coastal validation are approximate and need refinement."
                )
                if st.button(
                    "Find coordinates",
                    key="resolve_custom_location",
                    use_container_width=True,
                ):
                    if not location_query.strip():
                        st.warning("Enter a location to search.")
                    else:
                        resolved = resolve_custom_location(location_query.strip())
                        if not resolved["ok"]:
                            st.error(str(resolved["message"]))
                        elif not resolved["is_ocean_coastal"]:
                            st.warning(str(resolved["message"]))
                            st.caption(
                                "Pick a point in the sea near the coast (not inland)."
                            )
                        else:
                            st.session_state.custom_latitude = resolved["latitude"]
                            st.session_state.custom_longitude = resolved["longitude"]
                            st.success(
                                f"Set to {resolved['label']} "
                                f"({resolved['latitude']:.4f}, {resolved['longitude']:.4f})"
                            )
                            clear_results()

                latitude = st.number_input(
                    "Latitude",
                    -90.0,
                    90.0,
                    profile.coordinates[0],
                    key="custom_latitude",
                )
                longitude = st.number_input(
                    "Longitude",
                    -180.0,
                    180.0,
                    profile.coordinates[1],
                    key="custom_longitude",
                )
                water_depth = st.number_input(
                    "Water depth (m)",
                    1.0,
                    250.0,
                    profile.water_depth,
                    key="custom_water_depth",
                )
                distance_to_shore = st.number_input(
                    "Distance to shore (km)",
                    0.1,
                    150.0,
                    profile.distance_to_shore,
                    key="custom_distance_to_shore",
                )
            else:
                latitude, longitude = profile.coordinates
                water_depth = profile.water_depth
                distance_to_shore = profile.distance_to_shore
                st.caption(f"{latitude:.3f}, {longitude:.3f}")
                st.caption(
                    f"{water_depth:.0f} m depth, {distance_to_shore:.1f} km offshore"
                )

        with st.expander("Technology Mix", expanded=False):
            technology_options = sorted(
                set(profile.enabled_technologies) | {"wind", "solar", "wave"}
            )
            tech_key = f"techs_{selected_site}"
            if st.button("Default", key="default_technology", use_container_width=True):
                st.session_state[tech_key] = list(profile.enabled_technologies)
                clear_results()

            selected_techs = st.multiselect(
                "Enabled technologies",
                options=technology_options,
                default=list(profile.enabled_technologies),
                format_func=lambda tech: TECH_LABELS.get(tech, tech.title()),
                key=tech_key,
            )

        with st.expander("Objective", expanded=False):
            if st.button("Default", key="default_objective", use_container_width=True):
                st.session_state.objective_type = "Capacity"
                st.session_state.target_capacity = default_capacity(profile)
                st.session_state.target_production = 300
                st.session_state.target_investment = 250
                clear_results()

            objective = st.radio(
                "Optimization target",
                ["Capacity", "Production", "Investment"],
                horizontal=False,
                key="objective_type",
            )
            if objective == "Capacity":
                target_value = st.slider(
                    "Target capacity (MW)",
                    1,
                    500,
                    default_capacity(profile),
                    key="target_capacity",
                )
                target_type = "capacity"
            elif objective == "Production":
                target_value = st.slider(
                    "Target production (GWh/year)",
                    10,
                    3000,
                    300,
                    key="target_production",
                )
                target_type = "production"
            else:
                target_value = st.slider(
                    "Investment budget ($M)",
                    10,
                    2000,
                    250,
                    key="target_investment",
                )
                target_type = "investment"

        with st.expander("Risk & Flexibility", expanded=False):
            if st.button("Default", key="default_risk", use_container_width=True):
                st.session_state.risk_confidence = 95
                st.session_state.scenario_samples = 800
                st.session_state.include_flexibility = True
                clear_results()

            confidence = st.slider(
                "Risk confidence level (%)", 80, 99, 95, key="risk_confidence"
            )
            simulations = st.slider(
                "Scenario samples", 100, 2500, 800, step=100, key="scenario_samples"
            )
            include_flexibility = st.toggle(
                "Include phased expansion option",
                value=True,
                key="include_flexibility",
            )

        run_clicked = st.button(
            "Run analysis", type="primary", use_container_width=True
        )
        if run_clicked:
            if not selected_techs:
                st.error("Select at least one technology.")
            else:
                settings = {
                    "site_key": selected_site,
                    "latitude": latitude,
                    "longitude": longitude,
                    "water_depth": water_depth,
                    "distance_to_shore": distance_to_shore,
                    "technologies": selected_techs,
                    "target_type": target_type,
                    "target_value": target_value,
                    "confidence": confidence,
                    "simulations": simulations,
                    "include_flexibility": include_flexibility,
                }
                run_analysis(profile, settings)


def clear_results() -> None:
    st.session_state.results = None
    st.session_state.last_run_settings = None


def select_site(site_key: str) -> None:
    st.session_state.site_key = site_key
    clear_results()


def default_capacity(profile: SiteProfile) -> int:
    if profile.key == "alaska":
        return 2
    if profile.key == "eastport":
        return 60
    return 120


def render_header() -> None:
    st.markdown(
        """
        <section class="fm-hero">
            <div class="fm-eyebrow">FlexiMORP v2</div>
            <h1>Offshore Renewable Platform Planner</h1>
            <p class="fm-lede">
            Configure a marine energy scenario, compare technology mixes, and review
            economic, risk, flexibility, and environmental indicators in one workspace.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def resolve_custom_location(query: str) -> dict[str, Any]:
    # TODO: Improve geocoding/coastal validation reliability (offline fallback,
    # stricter sea-vs-land classification, and clearer candidate selection).
    search_url = "https://nominatim.openstreetmap.org/search"
    try:
        response = requests.get(
            search_url,
            params={"q": query, "format": "jsonv2", "limit": 5},
            headers={"User-Agent": "fleximorpv2/1.0"},
            timeout=7,
        )
        response.raise_for_status()
        results = response.json()
    except requests.RequestException:
        return {
            "ok": False,
            "message": "Location search unavailable right now. Try manual coordinates.",
        }

    if not isinstance(results, list) or not results:
        return {"ok": False, "message": "No matching location found."}

    candidates = []
    for result in results:
        try:
            lat = float(result.get("lat"))
            lon = float(result.get("lon"))
        except (TypeError, ValueError):
            continue
        label = str(result.get("display_name", "Selected location"))
        suitability = ocean_coastal_suitability(lat, lon, label)
        candidates.append((suitability["score"], lat, lon, label, suitability))

    if not candidates:
        return {"ok": False, "message": "Could not parse location coordinates."}

    candidates.sort(key=lambda item: item[0], reverse=True)
    _, lat, lon, label, suitability = candidates[0]

    return {
        "ok": True,
        "latitude": lat,
        "longitude": lon,
        "label": label,
        "is_ocean_coastal": suitability["is_ocean_coastal"],
        "message": suitability["message"],
    }


def ocean_coastal_suitability(lat: float, lon: float, label: str) -> dict[str, Any]:
    text = label.lower()
    marine_words = ("sea", "ocean", "gulf", "bay", "channel", "strait", "coast")
    inland_words = ("county", "district", "village", "city", "town", "province")
    marine_hint = any(word in text for word in marine_words)
    inland_hint = any(word in text for word in inland_words)

    coastline_nearby = has_nearby_coastline(lat, lon)
    score = 0
    if marine_hint:
        score += 2
    if coastline_nearby:
        score += 2
    if inland_hint:
        score -= 1

    if marine_hint and coastline_nearby:
        return {
            "score": score,
            "is_ocean_coastal": True,
            "message": "Location is offshore/coastal and suitable.",
        }
    if coastline_nearby and not marine_hint:
        return {
            "score": score,
            "is_ocean_coastal": False,
            "message": "Location is near coast but may be on land. Move point offshore.",
        }
    return {
        "score": score,
        "is_ocean_coastal": False,
        "message": "Location does not look coastal/oceanic.",
    }


def has_nearby_coastline(lat: float, lon: float) -> bool:
    # Fast fallback based on known case-study geography if network is unavailable.
    case_sites = [(59.32, -155.90), (55.13, 1.48), (44.90, -66.98)]
    for site_lat, site_lon in case_sites:
        if haversine_km(lat, lon, site_lat, site_lon) <= 250:
            return True

    overpass_url = "https://overpass-api.de/api/interpreter"
    query = (
        "[out:json][timeout:10];"
        f'way["natural"="coastline"](around:30000,{lat},{lon});'
        "out ids;"
    )
    try:
        response = requests.get(
            overpass_url,
            params={"data": query},
            headers={"User-Agent": "fleximorpv2/1.0"},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        return False

    elements = payload.get("elements", []) if isinstance(payload, dict) else []
    return len(elements) > 0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return 2 * radius_km * math.asin(math.sqrt(a))


def render_workspace(profile: SiteProfile) -> None:
    left, right = st.columns([1.35, 1], gap="large")
    with left:
        st.subheader("Case Study Context")
        st.markdown(
            f"""
            <div class="fm-panel">
                <strong>{profile.label}</strong>
                <p class="fm-small">{profile.description}</p>
                <span class="fm-chip">{profile.environment_type.title()}</span>
                <span class="fm-chip">{profile.water_depth:.0f} m depth</span>
                <span class="fm-chip">{profile.distance_to_shore:.1f} km from shore</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="fm-map-wrap">', unsafe_allow_html=True)
        st.plotly_chart(site_map(profile), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.subheader("Screening Constraints")
        for constraint in profile.constraints:
            st.markdown(
                f"<div class='fm-card fm-small'>{constraint}</div>",
                unsafe_allow_html=True,
            )

        st.subheader("Available Technologies")
        tech_rows = technology_table(profile)
        st.dataframe(tech_rows, use_container_width=True, hide_index=True)

    st.subheader("Workflow")
    columns = st.columns(4)
    steps = [
        ("1. Baseline", "Size the platform and estimate cost of energy."),
        ("2. Uncertainty", "Sample resource, price, CAPEX, and OPEX variability."),
        ("3. Flexibility", "Value phased expansion and decision triggers."),
        ("4. Constraints", "Screen environmental and stakeholder exposure."),
    ]
    for column, (title, body) in zip(columns, steps):
        with column:
            st.markdown(
                f"<div class='fm-card'><strong>{title}</strong><p class='fm-small'>{body}</p></div>",
                unsafe_allow_html=True,
            )


def site_map(profile: SiteProfile) -> go.Figure:
    lat, lon = profile.coordinates
    fig = go.Figure(
        go.Scattergeo(
            lat=[lat],
            lon=[lon],
            text=[profile.label],
            mode="markers+text",
            textposition="top center",
            marker={
                "size": 14,
                "color": "#0f766e",
                "line": {"width": 1, "color": "#ffffff"},
            },
        )
    )
    fig.update_geos(
        projection_type="natural earth",
        showcountries=True,
        showland=True,
        landcolor="#e7edf4",
        showocean=True,
        oceancolor="#d7eef8",
        lataxis_range=[lat - 18, lat + 18],
        lonaxis_range=[lon - 30, lon + 30],
    )
    fig.update_layout(
        autosize=True,
        height=360,
        margin={"l": 0, "r": 0, "t": 10, "b": 0},
    )
    return fig


def technology_table(profile: SiteProfile) -> pd.DataFrame:
    rows = []
    for tech in profile.enabled_technologies:
        data = profile.config.get("technologies", {}).get(tech, {})
        rows.append(
            {
                "Technology": TECH_LABELS.get(tech, tech.title()),
                "CAPEX $M/MW": round(data.get("cost_per_mw", 0) / 1_000_000, 2),
                "Capacity factor": f"{data.get('capacity_factor', 0):.0%}",
                "Impact": str(data.get("environmental_impact", "unknown")).title(),
            }
        )
    return pd.DataFrame(rows)


def run_analysis(profile: SiteProfile, settings: dict[str, Any]) -> None:
    progress = st.progress(0)
    status = st.empty()
    stages = [
        "Sizing baseline technology mix",
        "Sampling uncertainty scenarios",
        "Evaluating phased expansion option",
        "Scoring constraints and recommendations",
    ]
    for index, stage in enumerate(stages, start=1):
        status.markdown(f"<div class='fm-status'>{stage}</div>", unsafe_allow_html=True)
        progress.progress(index / len(stages))

    st.session_state.results = build_results(profile, settings)
    st.session_state.last_run_settings = settings
    status.empty()
    progress.empty()
    st.rerun()


def build_results(profile: SiteProfile, settings: dict[str, Any]) -> dict[str, Any]:
    rng = np.random.default_rng(42)
    technologies = settings["technologies"]
    target_capacity = derive_capacity(settings)
    capacities = allocate_capacity(profile, technologies, target_capacity)
    tech_metrics = calculate_technology_metrics(profile, capacities)

    annual_production = sum(row["Annual production (GWh)"] for row in tech_metrics)
    capex = sum(row["CAPEX ($M)"] for row in tech_metrics)
    opex = capex * opex_ratio(profile)
    weighted_cf = annual_production * 1000 / (target_capacity * 8760)
    lcoe = calculate_lcoe(capex, opex, annual_production, profile)
    npv = calculate_npv(capex, opex, annual_production, profile, lcoe)

    samples = scenario_samples(rng, lcoe, settings["simulations"], profile, settings)
    environmental = environmental_scores(profile, technologies)
    flexibility = flexibility_plan(capacities, settings, profile, lcoe)

    return {
        "site": profile.label,
        "settings": settings,
        "baseline": {
            "lcoe": lcoe,
            "total_capacity": target_capacity,
            "capacity_factor": weighted_cf,
            "annual_production": annual_production,
            "capex": capex,
            "opex": opex,
            "npv": npv,
            "technology_rows": tech_metrics,
        },
        "uncertainty": samples,
        "flexibility": flexibility,
        "environmental": environmental,
        "recommendations": recommendations(
            lcoe, environmental, flexibility, profile, technologies
        ),
    }


def derive_capacity(settings: dict[str, Any]) -> float:
    target_type = settings["target_type"]
    target_value = float(settings["target_value"])
    if target_type == "capacity":
        return target_value
    if target_type == "production":
        return max(1.0, target_value * 1000 / (0.38 * 8760))
    return max(1.0, target_value / 3.2)


def allocate_capacity(
    profile: SiteProfile, technologies: list[str], target_capacity: float
) -> dict[str, float]:
    raw_weights = {}
    for tech in technologies:
        tech_config = profile.config.get("technologies", {}).get(tech, {})
        capacity_factor = float(
            tech_config.get("capacity_factor", default_capacity_factor(tech))
        )
        cost = float(tech_config.get("cost_per_mw", default_cost_per_mw(tech)))
        raw_weights[tech] = max(0.05, capacity_factor / (cost / 1_000_000))
    total_weight = sum(raw_weights.values())
    return {
        tech: round(target_capacity * weight / total_weight, 2)
        for tech, weight in raw_weights.items()
    }


def calculate_technology_metrics(
    profile: SiteProfile, capacities: dict[str, float]
) -> list[dict[str, Any]]:
    rows = []
    for tech, capacity in capacities.items():
        tech_config = profile.config.get("technologies", {}).get(tech, {})
        capacity_factor = float(
            tech_config.get("capacity_factor", default_capacity_factor(tech))
        )
        cost_per_mw = float(tech_config.get("cost_per_mw", default_cost_per_mw(tech)))
        annual_production = capacity * capacity_factor * 8760 / 1000
        capex = capacity * cost_per_mw / 1_000_000
        rows.append(
            {
                "Technology": TECH_LABELS.get(tech, tech.title()),
                "Capacity (MW)": capacity,
                "Capacity factor": capacity_factor,
                "Annual production (GWh)": annual_production,
                "CAPEX ($M)": capex,
                "LCOE contribution ($/MWh)": (capex * 1_000_000 * 0.085)
                / max(annual_production * 1000, 1),
            }
        )
    return rows


def default_capacity_factor(tech: str) -> float:
    return {"wind": 0.42, "solar": 0.17, "wave": 0.28, "hydro": 0.30}.get(tech, 0.30)


def default_cost_per_mw(tech: str) -> float:
    return {
        "wind": 3_600_000,
        "solar": 2_000_000,
        "wave": 5_000_000,
        "hydro": 3_500_000,
    }.get(tech, 3_000_000)


def opex_ratio(profile: SiteProfile) -> float:
    return {"riverine": 0.052, "nearshore": 0.044, "offshore": 0.038}.get(
        profile.environment_type, 0.04
    )


def calculate_lcoe(
    capex: float, opex: float, production_gwh: float, profile: SiteProfile
) -> float:
    economic = profile.config.get("economic", {})
    discount_rate = float(economic.get("discount_rate", 0.07))
    lifetime = int(economic.get("project_lifetime", 25))
    capital_recovery = discount_rate * (1 + discount_rate) ** lifetime
    capital_recovery /= (1 + discount_rate) ** lifetime - 1
    annualized_cost = capex * 1_000_000 * capital_recovery + opex * 1_000_000
    return round(annualized_cost / max(production_gwh * 1000, 1), 1)


def calculate_npv(
    capex: float, opex: float, production_gwh: float, profile: SiteProfile, lcoe: float
) -> float:
    economic = profile.config.get("economic", {})
    price = float(economic.get("electricity_price", max(lcoe * 1.28 / 1000, 0.12)))
    discount_rate = float(economic.get("discount_rate", 0.07))
    lifetime = int(economic.get("project_lifetime", 25))
    annual_cash = production_gwh * 1_000_000 * price - opex * 1_000_000
    discounted = sum(
        annual_cash / (1 + discount_rate) ** year for year in range(1, lifetime + 1)
    )
    return round((discounted - capex * 1_000_000) / 1_000_000, 1)


def scenario_samples(
    rng: np.random.Generator,
    lcoe: float,
    simulations: int,
    profile: SiteProfile,
    settings: dict[str, Any],
) -> dict[str, Any]:
    exposure = 0.12
    if profile.environment_type == "riverine":
        exposure += 0.05
    if "wave" in settings["technologies"]:
        exposure += 0.04
    values = rng.normal(lcoe, lcoe * exposure, simulations)
    values = np.clip(values, lcoe * 0.55, lcoe * 1.9)
    confidence = settings["confidence"]
    lower = (100 - confidence) / 2
    upper = 100 - lower
    threshold = lcoe * 1.15
    return {
        "values": values,
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
        "p_low": float(np.percentile(values, lower)),
        "p_high": float(np.percentile(values, upper)),
        "var": float(np.percentile(values, confidence)),
        "success_probability": float(np.mean(values <= threshold)),
        "threshold": threshold,
    }


def environmental_scores(
    profile: SiteProfile, technologies: list[str]
) -> dict[str, Any]:
    base = {"riverine": 78, "nearshore": 72, "offshore": 76, "custom": 74}.get(
        profile.environment_type, 74
    )
    if "wave" in technologies:
        base -= 4
    if "hydro" in technologies:
        base -= 3
    if "solar" in technologies:
        base += 2

    technology_scores = []
    for tech in technologies:
        impact = (
            profile.config.get("technologies", {})
            .get(tech, {})
            .get("environmental_impact", "medium")
        )
        impact_penalty = {"low": 4, "medium": 10, "high": 18}.get(
            str(impact).lower(), 10
        )
        technology_scores.append(
            {
                "Technology": TECH_LABELS.get(tech, tech.title()),
                "Resource": round(score_for(tech, profile.environment_type), 1),
                "Constraint": round(max(40, base - impact_penalty), 1),
                "Stakeholder": round(max(35, base - stakeholder_penalty(profile)), 1),
                "Climate": round(max(45, base + climate_adjustment(tech, profile)), 1),
            }
        )

    constraints = [
        {"Constraint": item, "Exposure": exposure_for_constraint(item, profile)}
        for item in profile.constraints
    ]
    return {
        "overall_score": max(0, min(100, base)),
        "technology_scores": technology_scores,
        "constraints": constraints,
    }


def score_for(tech: str, environment_type: str) -> float:
    base = {"wind": 84, "solar": 68, "wave": 62, "hydro": 70}.get(tech, 65)
    if environment_type == "offshore" and tech == "wind":
        base += 6
    if environment_type == "riverine" and tech == "hydro":
        base += 10
    if environment_type == "nearshore" and tech == "wave":
        base -= 8
    return min(100, base)


def stakeholder_penalty(profile: SiteProfile) -> float:
    if profile.key == "eastport":
        return 18
    if profile.key == "alaska":
        return 10
    return 8


def climate_adjustment(tech: str, profile: SiteProfile) -> float:
    if profile.key == "alaska" and tech == "solar":
        return -12
    if tech == "wind":
        return 4
    return 0


def exposure_for_constraint(item: str, profile: SiteProfile) -> str:
    text = item.lower()
    if "fishing" in text or "salmon" in text or "shipping" in text:
        return "High"
    if profile.key == "eastport" and ("lobster" in text or "whale" in text):
        return "High"
    if "visual" in text or "tourism" in text:
        return "Medium"
    return "Medium"


def flexibility_plan(
    capacities: dict[str, float],
    settings: dict[str, Any],
    profile: SiteProfile,
    lcoe: float,
) -> dict[str, Any]:
    total_capacity = sum(capacities.values())
    enabled = settings["include_flexibility"]
    option_value = total_capacity * (0.16 if enabled else 0.04) * 1_000_000
    premium = 0.14 if enabled else 0.03
    stages = [
        {
            "Year": 0,
            "Action": "Initial build",
            "Capacity (MW)": round(
                total_capacity * 0.55 if enabled else total_capacity, 1
            ),
        }
    ]
    if enabled:
        stages.extend(
            [
                {
                    "Year": 3,
                    "Action": "Resource review",
                    "Capacity (MW)": round(total_capacity * 0.25, 1),
                },
                {
                    "Year": 7,
                    "Action": "Expansion option",
                    "Capacity (MW)": round(total_capacity * 0.20, 1),
                },
            ]
        )
    return {
        "real_options_value": option_value,
        "flexibility_premium": premium,
        "stages": stages,
        "triggers": {
            "Power price": f">= ${round(lcoe * 1.12, 0):.0f}/MWh",
            "CAPEX reduction": ">= 12%",
            "Capacity utilization": ">= 82%",
            "Permit risk": "No material escalation",
        },
    }


def recommendations(
    lcoe: float,
    environmental: dict[str, Any],
    flexibility: dict[str, Any],
    profile: SiteProfile,
    technologies: list[str],
) -> list[str]:
    recs = []
    if lcoe <= 95:
        recs.append("Advance to feasibility with detailed resource validation.")
    else:
        recs.append("Run cost-down cases before committing to engineering spend.")
    if environmental["overall_score"] < 75:
        recs.append(
            "Prioritize stakeholder and exclusion-zone screening in the next phase."
        )
    if flexibility["flexibility_premium"] >= 0.10:
        recs.append("Use phased deployment as the base commercial structure.")
    if profile.key == "eastport":
        recs.append("Treat fishing coordination as a primary design constraint.")
    if "wave" in technologies:
        recs.append("Keep wave capacity modular until reliability data improves.")
    return recs


def render_overview_metric(
    column: Any,
    label: str,
    value: str,
    warning: bool = False,
    warning_text: str = "This value is high compared to the average.",
) -> None:
    warning_icon = ""
    warning_class = " warning" if warning else ""
    if warning:
        warning_icon = (
            f'<span class="fm-warning-icon" data-tooltip="{escape(warning_text)}">'
            "&#9888;</span>"
        )

    column.markdown(
        f"""
        <div class="fm-overview-metric{warning_class}">
            <div class="fm-overview-label">
                <span>{escape(label)}</span>{warning_icon}
            </div>
            <div class="fm-overview-value">{escape(value)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard() -> None:
    results = st.session_state.results
    baseline = results["baseline"]
    uncertainty = results["uncertainty"]
    environmental = results["environmental"]

    st.caption(f"Current run: {results['site']}")
    metric_cols = st.columns(5)
    render_overview_metric(
        metric_cols[0],
        "LCOE ($/MWh)",
        f"{baseline['lcoe']:.1f}",
        warning=baseline["lcoe"] > 95,
    )
    render_overview_metric(
        metric_cols[1], "Capacity (MW)", f"{baseline['total_capacity']:.1f}"
    )
    render_overview_metric(
        metric_cols[2],
        "Production (GWh)",
        f"{baseline['annual_production']:.1f}",
    )
    render_overview_metric(
        metric_cols[3],
        "NPV",
        f"${baseline['npv']:.1f}M",
        warning=baseline["npv"] < 0,
        warning_text="This value is low compared to the average.",
    )
    render_overview_metric(
        metric_cols[4],
        "Constraint Score",
        f"{environmental['overall_score']}",
        warning=environmental["overall_score"] < 75,
        warning_text="This value is low compared to the average.",
    )

    tabs = st.tabs(
        ["Portfolio", "Risk", "Flexibility", "Constraints", "Decision Brief"]
    )
    with tabs[0]:
        render_portfolio_tab(results)
    with tabs[1]:
        render_risk_tab(results)
    with tabs[2]:
        render_flexibility_tab(results)
    with tabs[3]:
        render_constraints_tab(results)
    with tabs[4]:
        render_decision_tab(results)


def render_portfolio_tab(results: dict[str, Any]) -> None:
    rows = pd.DataFrame(results["baseline"]["technology_rows"])
    left, right = st.columns([1.1, 1], gap="large")
    with left:
        fig = px.bar(
            rows,
            x="Technology",
            y="Capacity (MW)",
            color="Technology",
            color_discrete_sequence=list(TECH_COLORS.values()),
            title="Optimized Capacity Allocation",
        )
        fig.update_layout(showlegend=False, height=380)
        st.plotly_chart(fig, use_container_width=True)
    with right:
        fig = px.pie(
            rows,
            values="Annual production (GWh)",
            names="Technology",
            title="Annual Production Share",
            hole=0.48,
        )
        fig.update_layout(height=380)
        st.plotly_chart(fig, use_container_width=True)
    rows["Capacity factor"] = rows["Capacity factor"].map(lambda value: f"{value:.0%}")
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_risk_tab(results: dict[str, Any]) -> None:
    uncertainty = results["uncertainty"]
    values = uncertainty["values"]
    left, right = st.columns([1.25, 0.9], gap="large")
    with left:
        fig = px.histogram(values, nbins=42, title="LCOE Scenario Distribution")
        fig.add_vline(
            x=uncertainty["threshold"],
            line_dash="dash",
            line_color="#b45309",
            annotation_text="success threshold",
        )
        fig.update_layout(
            xaxis_title="LCOE ($/MWh)", yaxis_title="Scenarios", height=410
        )
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.metric("Mean LCOE ($/MWh)", f"{uncertainty['mean']:.1f}")
        st.metric("Scenario Volatility ($/MWh)", f"{uncertainty['std']:.1f}")
        st.metric("Value at Risk ($/MWh)", f"{uncertainty['var']:.1f}")
        st.metric("Success probability", f"{uncertainty['success_probability']:.0%}")
        st.caption(
            f"Confidence interval: ${uncertainty['p_low']:.1f} to ${uncertainty['p_high']:.1f}/MWh"
        )


def render_flexibility_tab(results: dict[str, Any]) -> None:
    flexibility = results["flexibility"]
    left, right = st.columns([1.05, 1], gap="large")
    with left:
        st.metric(
            "Real options value",
            f"${flexibility['real_options_value'] / 1_000_000:.1f}M",
        )
        st.metric("Flexibility premium", f"{flexibility['flexibility_premium']:.0%}")
        st.dataframe(
            pd.DataFrame(flexibility["stages"]),
            use_container_width=True,
            hide_index=True,
        )
    with right:
        trigger_df = pd.DataFrame(
            [
                {"Trigger": key, "Condition": value}
                for key, value in flexibility["triggers"].items()
            ]
        )
        st.dataframe(trigger_df, use_container_width=True, hide_index=True)


def render_constraints_tab(results: dict[str, Any]) -> None:
    environmental = results["environmental"]
    scores = pd.DataFrame(environmental["technology_scores"])
    constraints = pd.DataFrame(environmental["constraints"])
    left, right = st.columns([1.2, 0.95], gap="large")
    with left:
        fig = go.Figure()
        dimensions = ["Resource", "Constraint", "Stakeholder", "Climate"]
        for _, row in scores.iterrows():
            fig.add_trace(
                go.Scatterpolar(
                    r=[row[dimension] for dimension in dimensions]
                    + [row[dimensions[0]]],
                    theta=dimensions + [dimensions[0]],
                    fill="toself",
                    name=row["Technology"],
                )
            )
        fig.update_layout(
            polar={"radialaxis": {"visible": True, "range": [0, 100]}},
            height=430,
            title="Technology Suitability",
        )
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.dataframe(constraints, use_container_width=True, hide_index=True)


def render_decision_tab(results: dict[str, Any]) -> None:
    st.subheader("Recommendations")
    for index, item in enumerate(results["recommendations"], start=1):
        st.markdown(f"{index}. {item}")

    st.subheader("Next Actions")
    next_actions = pd.DataFrame(
        [
            {
                "Workstream": "Resource",
                "Action": "Validate wind, solar, and marine datasets against site measurements.",
            },
            {
                "Workstream": "Engineering",
                "Action": "Refine foundations, cable route, and installation assumptions.",
            },
            {
                "Workstream": "Commercial",
                "Action": "Stress test revenue, CAPEX, OPEX, and financing assumptions.",
            },
            {
                "Workstream": "Permitting",
                "Action": "Map exclusion zones and stakeholder review gates.",
            },
        ]
    )
    st.dataframe(next_actions, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
