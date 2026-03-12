"""
Houston WCR Intelligence Platform
Main Streamlit application entry point.

A spatially-intelligent Wastewater Capacity Reservation management tool
built for the City of Houston's Impact Fee Administration team.

Run: streamlit run app.py
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import warnings

warnings.filterwarnings("ignore")

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Houston WCR Intelligence Platform",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Apply global CSS (immediately after page config) ─────────────────────────
from utils.styling import get_main_css, render_header, render_footer, COLORS
st.markdown(get_main_css(), unsafe_allow_html=True)

# ── Import platform modules ───────────────────────────────────────────────────
from data.generate_data import generate_applications
from data.spatial_data import get_plants_gdf, get_city_boundary_gdf, get_council_districts_gdf
from assets.methodology import SPATIAL_OPERATIONS_LIST, render_methodology_expander

from gis.spatial_engine import (
    build_service_zones,
    assign_applications_to_zones,
    buffer_capacity_alert,
    calculate_hotspots,
    council_district_stats,
)
from gis.capacity_analysis import (
    calculate_zone_utilization,
    project_future_demand,
)

from modules.capacity_map import render_capacity_map
from modules.wcr_tracker import render_wcr_tracker
from modules.supervisor_dashboard import render_supervisor_dashboard


@st.cache_data
def load_all_data():
    """Load and cache all platform data. Runs once per session."""
    # Raw application data
    apps_df = generate_applications(250)

    # Spatial layers
    plants_gdf = get_plants_gdf()
    city_gdf = get_city_boundary_gdf()
    districts_gdf = get_council_districts_gdf()

    return apps_df, plants_gdf, city_gdf, districts_gdf


@st.cache_data
def build_spatial_layers(_apps_df, _plants_gdf, _city_gdf, _districts_gdf):
    """
    Build all spatial layers:
    - Voronoi service zones
    - Zone utilization stats
    - Spatially-assigned applications
    - Capacity alert buffers
    - Hotspot grid
    - Demand projections
    """
    # 1. Derive Voronoi service zones (EPSG:2278 → clipped → EPSG:4326)
    zones_gdf = build_service_zones(_plants_gdf, _city_gdf)

    # 2. Calculate zone capacity utilization
    zone_util_df = calculate_zone_utilization(
        pd.DataFrame([dict(row) for _, row in _plants_gdf.iterrows()]),
        _apps_df,
    )

    # 3. Merge utilization into zones GDF for map rendering
    if not zones_gdf.empty and not zone_util_df.empty:
        zones_gdf = zones_gdf.merge(
            zone_util_df[["plant_id", "utilization_pct", "status", "available_su", "reserved_su", "capacity_su"]],
            on="plant_id", how="left",
        )
        zones_gdf["capacity_status"] = zones_gdf["status"].fillna("Available")

    # 4. Spatial join: assign applications → zones
    apps_with_zones = assign_applications_to_zones(_apps_df, zones_gdf)

    # 5. Merge zone capacity status back to applications
    if not zone_util_df.empty and "treatment_plant_id" in apps_with_zones.columns:
        status_map = zone_util_df.set_index("plant_id")["status"].to_dict()
        apps_with_zones["capacity_status"] = apps_with_zones["treatment_plant_id"].map(status_map).fillna(
            apps_with_zones.get("capacity_status", "Available")
        )

    # 6. Capacity alert buffers (0.5-mile around stressed zones)
    buffer_gdf, flagged_app_ids = buffer_capacity_alert(zones_gdf, apps_with_zones)

    # 7. Mark flagged applications
    if flagged_app_ids:
        apps_with_zones["capacity_flag"] = apps_with_zones.apply(
            lambda r: True if r.get("application_id") in flagged_app_ids else r.get("capacity_flag", False),
            axis=1,
        )

    # 8. Hotspot density grid (KDE)
    hotspot_gdf = calculate_hotspots(apps_with_zones)

    # 9. 6-month demand projection
    proj_df = project_future_demand(apps_with_zones, zone_util_df, months_ahead=6)

    return zones_gdf, zone_util_df, apps_with_zones, buffer_gdf, hotspot_gdf, proj_df


# ── Session state initialization ──────────────────────────────────────────────
if "selected_app_id" not in st.session_state:
    st.session_state["selected_app_id"] = None
if "active_module" not in st.session_state:
    st.session_state["active_module"] = "Spatial Capacity Map"


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(render_header(), unsafe_allow_html=True)


# ── Data loading with spinner ─────────────────────────────────────────────────
with st.spinner("Loading spatial data and building service zones…"):
    apps_df, plants_gdf, city_gdf, districts_gdf = load_all_data()

with st.spinner("Running spatial analysis (Voronoi zones, KDE, buffer analysis)…"):
    zones_gdf, zone_util_df, apps_df, buffer_gdf, hotspot_gdf, proj_df = build_spatial_layers(
        apps_df, plants_gdf, city_gdf, districts_gdf
    )


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # Live clock
    clock_placeholder = st.empty()
    clock_placeholder.markdown(
        f'<div style="text-align:center;font-size:0.78rem;color:{COLORS["text_light"]};'
        f'font-family:monospace;padding:4px 0 8px 0;">'
        f'{datetime.now().strftime("%A, %B %d %Y")}<br>'
        f'<span style="font-size:1.1rem;font-weight:700;color:{COLORS["houston_blue"]};">'
        f'{datetime.now().strftime("%I:%M %p")}</span></div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # Navigation
    st.markdown("### Navigation")
    module = st.radio(
        "Select Module",
        options=[
            "🗺️  Spatial Capacity Map",
            "📋  WCR Application Tracker",
            "🏛️  Supervisor Operations",
        ],
        key="nav_module",
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Quick stats widget
    st.markdown("### Quick Stats")
    overdue_count = (apps_df["sla_status"] == "Overdue").sum()
    pending_count = (apps_df["status"] == "Pending").sum()
    at_limit_count = (zone_util_df["status"] == "At Limit").sum() if zone_util_df is not None else 0

    # Queue depth
    st.markdown(
        f'<div style="background:white;border-radius:8px;padding:10px 14px;margin-bottom:8px;'
        f'box-shadow:0 1px 4px rgba(0,0,0,0.08);border-left:4px solid {COLORS["accent_blue"]};">'
        f'<div style="font-size:0.7rem;color:{COLORS["text_light"]};font-weight:600;text-transform:uppercase;letter-spacing:0.6px;">Today\'s Queue Depth</div>'
        f'<div style="font-size:1.6rem;font-weight:800;color:{COLORS["text"]};">{pending_count}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Overdue (red if > 0)
    overdue_color = COLORS["at_limit"] if overdue_count > 0 else COLORS["available"]
    st.markdown(
        f'<div style="background:white;border-radius:8px;padding:10px 14px;margin-bottom:8px;'
        f'box-shadow:0 1px 4px rgba(0,0,0,0.08);border-left:4px solid {overdue_color};">'
        f'<div style="font-size:0.7rem;color:{COLORS["text_light"]};font-weight:600;text-transform:uppercase;letter-spacing:0.6px;">Overdue Applications</div>'
        f'<div style="font-size:1.6rem;font-weight:800;color:{overdue_color};">{overdue_count}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # System status dots
    st.markdown(
        f'<div style="background:#1e293b;border-radius:6px;padding:10px 12px;font-family:monospace;'
        f'font-size:0.72rem;color:#94a3b8;">'
        f'<div style="color:#60a5fa;font-weight:700;margin-bottom:6px;">SYSTEM STATUS</div>'
        f'<span style="color:#4ade80;">&#9679;</span> Q-Flow&nbsp;&nbsp;&nbsp; '
        f'<span style="color:#4ade80;">&#9679;</span> GIMS<br>'
        f'<span style="color:#4ade80;">&#9679;</span> ILMS&nbsp;&nbsp;&nbsp;&nbsp; '
        f'<span style="color:#4ade80;">&#9679;</span> Kronos'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # About section
    with st.expander("About This Platform"):
        st.markdown("""
**Houston WCR Intelligence Platform** is a spatially-intelligent Wastewater Capacity Reservation management tool built for Houston Public Works / Houston Water Impact Fee Administration.

**Systems Integrated:**
- **Q-Flow** — Queue management simulation
- **GIMS/GeoLink** — GIS layer integration
- **ILMS** — Permitting system references
- **Kronos** — Workforce scheduling

**Data:** 250 simulated WCR applications + real Houston WWTP locations
""")

    # Spatial methodology panel
    with st.expander("📐 Spatial Methodology"):
        st.markdown("**Spatial Operations in Use:**")
        for op, desc in SPATIAL_OPERATIONS_LIST:
            st.markdown(f"- **{op}** — {desc}")
        st.markdown(f"""
---
**CRS Pipeline:**
1. Input coordinates: EPSG:4326 (WGS84)
2. Analysis: EPSG:2278 (TX State Plane S. Central, US ft)
3. Display: EPSG:4326 (WGS84)
""")


# ── Module routing ────────────────────────────────────────────────────────────
module_name = module.split("  ", 1)[-1] if "  " in module else module.split(" ", 1)[-1]

if "Spatial Capacity Map" in module:
    render_capacity_map(
        apps_df, zones_gdf, plants_gdf, zone_util_df, proj_df,
        buffer_gdf, hotspot_gdf,
    )

elif "WCR Application Tracker" in module:
    render_wcr_tracker(apps_df, plants_gdf, zones_gdf, zone_util_df)

elif "Supervisor Operations" in module:
    render_supervisor_dashboard(apps_df, zone_util_df, proj_df)


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(render_footer(), unsafe_allow_html=True)
