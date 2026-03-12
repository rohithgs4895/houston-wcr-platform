"""
Module 1: Spatial Capacity Map
Houston WCR Intelligence Platform

Renders an interactive Folium map with:
- Voronoi service zone choropleth (capacity utilization)
- Treatment plant markers
- WCR application heatmap (urgency-weighted)
- Individual application markers
- Capacity alert buffer zones
- Application density hexbins
"""

import streamlit as st
import folium
from folium.plugins import HeatMap, MiniMap, MarkerCluster
from streamlit_folium import st_folium
import pandas as pd
import geopandas as gpd
import json
import numpy as np
from datetime import date

from utils.styling import (
    COLORS, render_section_header, render_metric_card,
    render_alert, render_badge
)
from gis.capacity_analysis import get_utilization_color, get_trend_arrow

HOUSTON_CENTER = [29.7604, -95.3698]

STATUS_MARKER_COLORS = {
    "Pending": "#3498db",
    "In Review": "#9b59b6",
    "Approved": "#27ae60",
    "Denied": "#e74c3c",
    "Revision Needed": "#e67e22",
    "On Hold": "#95a5a6",
}


def _circle_marker_svg(color, size=12):
    return f"""
    <div style="
        background-color: {color};
        width: {size}px; height: {size}px;
        border-radius: 50%;
        border: 2px solid white;
        box-shadow: 0 1px 4px rgba(0,0,0,0.4);
    "></div>
    """


def _make_zone_popup(row, util_row):
    """Build HTML popup for a service zone polygon."""
    if util_row is None:
        return folium.Popup("Zone data unavailable", max_width=280)

    util_pct = util_row.get("utilization_pct", 0)
    status = util_row.get("status", "Unknown")
    reserved = util_row.get("total_reserved_su", 0)
    available = util_row.get("available_su", 0)
    capacity = util_row.get("capacity_su", 0)
    proj_pct = util_row.get("projected_pct", util_pct)
    trend = get_trend_arrow(util_pct, proj_pct)
    color = get_utilization_color(util_pct)

    status_color = COLORS.get(
        {"Available": "available", "Near Limit": "near_limit", "At Limit": "at_limit"}.get(status, "text_light"),
        "#7f8c8d"
    )

    html = f"""
    <div style="font-family: Arial, sans-serif; font-size: 13px; min-width: 260px;">
        <div style="background:{COLORS['houston_blue']}; color:white; padding:8px 12px;
                    margin:-12px -12px 10px -12px; border-radius:4px 4px 0 0; font-weight:700;">
            {row.get('plant_name', 'Unknown Zone')}
        </div>
        <table style="width:100%; border-collapse:collapse;">
            <tr><td style="color:#666; padding:3px 0;">Utilization</td>
                <td style="font-weight:700; color:{color}; text-align:right;">{util_pct:.1f}% {trend}</td></tr>
            <tr><td style="color:#666; padding:3px 0;">Status</td>
                <td style="font-weight:700; color:{status_color}; text-align:right;">{status}</td></tr>
            <tr><td style="color:#666; padding:3px 0;">Reserved SUs</td>
                <td style="font-weight:600; text-align:right;">{reserved:,}</td></tr>
            <tr><td style="color:#666; padding:3px 0;">Available SUs</td>
                <td style="font-weight:600; color:{COLORS['available']}; text-align:right;">{available:,}</td></tr>
            <tr><td style="color:#666; padding:3px 0;">Capacity (SUs)</td>
                <td style="font-weight:600; text-align:right;">{capacity:,}</td></tr>
            <tr><td style="color:#666; padding:3px 0;">6-Mo Projection</td>
                <td style="font-weight:700; color:{get_utilization_color(proj_pct)}; text-align:right;">{proj_pct:.1f}%</td></tr>
        </table>
        <div style="margin-top:8px; font-size:11px; color:#999; border-top:1px solid #eee; padding-top:6px;">
            Click application markers for detail
        </div>
    </div>
    """
    return folium.Popup(html, max_width=300)


def _make_plant_popup(plant_row, util_row):
    """Build HTML popup for a treatment plant marker."""
    util_pct = util_row.get("utilization_pct", 0) if util_row is not None else 0
    proj_pct = util_row.get("projected_pct", util_pct) if util_row is not None else 0
    status = util_row.get("status", "Unknown") if util_row is not None else "Unknown"
    capacity_su = int(plant_row.get("capacity_su", 0))
    active_res = util_row.get("total_reserved_su", 0) if util_row is not None else 0

    color = get_utilization_color(util_pct)

    html = f"""
    <div style="font-family: Arial, sans-serif; font-size: 13px; min-width: 280px;">
        <div style="background:{COLORS['houston_blue']}; color:white; padding:10px 14px;
                    margin:-12px -12px 10px -12px; border-radius:4px 4px 0 0;">
            <div style="font-weight:700; font-size:14px;">{plant_row['name']}</div>
            <div style="font-size:11px; color:#a8c4e8;">ID: {plant_row['id']} &nbsp;|&nbsp; Online: {plant_row['online_year']}</div>
        </div>
        <table style="width:100%; border-collapse:collapse;">
            <tr><td style="color:#666; padding:4px 0;">Design Capacity</td>
                <td style="font-weight:700; text-align:right;">{plant_row['capacity_mgd']} MGD ({capacity_su:,} SU)</td></tr>
            <tr><td style="color:#666; padding:4px 0;">Current Utilization</td>
                <td style="font-weight:700; color:{color}; text-align:right;">{util_pct:.1f}%</td></tr>
            <tr><td style="color:#666; padding:4px 0;">Zone Status</td>
                <td style="font-weight:700; text-align:right;">{status}</td></tr>
            <tr><td style="color:#666; padding:4px 0;">Active Reservations</td>
                <td style="font-weight:600; text-align:right;">{int(active_res):,} SU</td></tr>
            <tr style="background:#fff8e7;">
                <td style="color:#666; padding:4px 0;">6-Mo Projected</td>
                <td style="font-weight:700; color:{get_utilization_color(proj_pct)}; text-align:right;">{proj_pct:.1f}%</td></tr>
        </table>
        <div style="margin-top:10px;">
            <div style="background:#e5e7eb; border-radius:4px; height:10px; overflow:hidden;">
                <div style="background:{color}; width:{min(util_pct,100):.0f}%; height:100%; border-radius:4px;"></div>
            </div>
            <div style="font-size:10px; color:#999; margin-top:3px;">{min(util_pct,100):.0f}% utilized</div>
        </div>
    </div>
    """
    return folium.Popup(html, max_width=320)


def _make_app_popup(row):
    """Build HTML popup for a WCR application marker."""
    fee_str = f"${row['total_impact_fee']:,.0f}"
    sla_color = {"On Track": "#27ae60", "At Risk": "#f1c40f", "Overdue": "#e74c3c", "Completed": "#3498db"}.get(
        row.get("sla_status", "On Track"), "#27ae60"
    )
    flag_html = " &#9888;&#65039;" if row.get("capacity_flag") else ""

    html = f"""
    <div style="font-family: Arial, sans-serif; font-size: 12px; min-width: 240px;">
        <div style="background:{COLORS['accent_blue']}; color:white; padding:8px 12px;
                    margin:-12px -12px 8px -12px; border-radius:4px 4px 0 0; font-weight:700;">
            {row['application_id']}{flag_html}
        </div>
        <div style="margin-bottom:6px;">
            <div style="font-weight:600; color:#2c3e50;">{row.get('applicant_name','N/A')}</div>
            <div style="color:#666; font-size:11px;">{row.get('property_address','N/A')}</div>
        </div>
        <table style="width:100%; border-collapse:collapse; font-size:12px;">
            <tr><td style="color:#666; padding:2px 0;">Type</td>
                <td style="text-align:right; font-weight:600;">{row.get('development_type','N/A')}</td></tr>
            <tr><td style="color:#666; padding:2px 0;">Status</td>
                <td style="text-align:right; font-weight:600; color:{STATUS_MARKER_COLORS.get(row.get('status',''), '#666')};">{row.get('status','N/A')}</td></tr>
            <tr><td style="color:#666; padding:2px 0;">SLA</td>
                <td style="text-align:right; font-weight:700; color:{sla_color};">{row.get('sla_status','N/A')}</td></tr>
            <tr><td style="color:#666; padding:2px 0;">Service Units</td>
                <td style="text-align:right; font-weight:600;">{row.get('service_units', 0):.1f} SU</td></tr>
            <tr><td style="color:#666; padding:2px 0;">Impact Fee</td>
                <td style="text-align:right; font-weight:700; color:{COLORS['houston_blue']};">{fee_str}</td></tr>
            <tr><td style="color:#666; padding:2px 0;">Analyst</td>
                <td style="text-align:right;">{row.get('assigned_analyst','N/A')}</td></tr>
            <tr><td style="color:#666; padding:2px 0;">Days Open</td>
                <td style="text-align:right;">{row.get('days_open',0)} days</td></tr>
        </table>
    </div>
    """
    return folium.Popup(html, max_width=280)


def build_folium_map(df, zones_gdf, plants_gdf, zone_util_df, proj_df,
                     buffer_gdf=None, hotspot_gdf=None,
                     show_buffers=True, show_heatmap=True,
                     show_hexbins=False, show_applications=True):
    """Build and return the main Folium map."""

    m = folium.Map(
        location=HOUSTON_CENTER,
        zoom_start=10,
        tiles=None,
        prefer_canvas=True,
    )

    # Base tiles
    folium.TileLayer(
        tiles="CartoDB Positron",
        name="Light (CartoDB Positron)",
        attr="&copy; OpenStreetMap contributors &copy; CartoDB",
    ).add_to(m)

    folium.TileLayer(
        tiles="CartoDB dark_matter",
        name="Dark Mode",
        attr="&copy; OpenStreetMap contributors &copy; CartoDB",
    ).add_to(m)

    # ── Layer 1: Service Zone Choropleth ──────────────────────────────────────
    if not zones_gdf.empty:
        zone_layer = folium.FeatureGroup(name="Service Zones (Capacity)", show=True)

        util_lookup = {}
        proj_lookup = {}
        if zone_util_df is not None and not zone_util_df.empty:
            util_lookup = zone_util_df.set_index("plant_id").to_dict("index")
        if proj_df is not None and not proj_df.empty:
            proj_lookup = proj_df.set_index("plant_id").to_dict("index")

        for _, zone_row in zones_gdf.iterrows():
            pid = zone_row.get("plant_id")
            util_row = util_lookup.get(pid)
            proj_row = proj_lookup.get(pid)
            if util_row and proj_row:
                util_row = dict(util_row)
                util_row["projected_pct"] = proj_row.get("projected_pct", util_row.get("utilization_pct", 0))

            util_pct = util_row.get("utilization_pct", 45) if util_row else 45

            if util_pct >= 90:
                fill_color = "#e74c3c"
            elif util_pct >= 75:
                fill_color = "#e67e22"
            elif util_pct >= 60:
                fill_color = "#f39c12"
            else:
                fill_color = "#2ecc71"

            try:
                geojson_data = gpd.GeoDataFrame([zone_row], crs="EPSG:4326").__geo_interface__
                folium.GeoJson(
                    geojson_data,
                    style_function=lambda x, fc=fill_color: {
                        "fillColor": fc,
                        "color": "#2c3e50",
                        "weight": 2,
                        "fillOpacity": 0.35,
                    },
                    tooltip=folium.Tooltip(
                        f"{zone_row.get('plant_name', 'Zone')}: {util_pct:.0f}% utilized",
                        sticky=True,
                    ),
                    popup=_make_zone_popup(zone_row, util_row),
                ).add_to(zone_layer)
            except Exception:
                pass

        zone_layer.add_to(m)

    # ── Layer 2: Treatment Plant Markers ──────────────────────────────────────
    plant_layer = folium.FeatureGroup(name="Treatment Plants", show=True)
    util_lookup = {}
    proj_lookup = {}
    if zone_util_df is not None and not zone_util_df.empty:
        util_lookup = zone_util_df.set_index("plant_id").to_dict("index")
    if proj_df is not None and not proj_df.empty:
        proj_lookup = proj_df.set_index("plant_id").to_dict("index")

    for _, plant in plants_gdf.iterrows():
        pid = plant["id"]
        util_row = util_lookup.get(pid)
        proj_row = proj_lookup.get(pid)
        if util_row and proj_row:
            util_row = dict(util_row)
            util_row["projected_pct"] = proj_row.get("projected_pct", util_row.get("utilization_pct", 0))

        util_pct = util_row.get("utilization_pct", 45) if util_row else 45
        color = get_utilization_color(util_pct)
        # Size by capacity (MGD)
        radius = max(8, min(22, plant["capacity_mgd"] / 4))

        folium.CircleMarker(
            location=[plant["lat"], plant["lon"]],
            radius=radius,
            color="white",
            weight=2,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            tooltip=folium.Tooltip(
                f"<b>{plant['name']}</b><br>{plant['capacity_mgd']} MGD | {util_pct:.0f}% utilized",
                sticky=True,
            ),
            popup=_make_plant_popup(plant, util_row),
        ).add_to(plant_layer)

        # Plant name label
        folium.Marker(
            location=[plant["lat"] + 0.008, plant["lon"]],
            icon=folium.DivIcon(
                html=f'<div style="font-size:9px; font-weight:600; color:{COLORS["houston_blue"]}; '
                     f'white-space:nowrap; text-shadow: 1px 1px 0 white, -1px -1px 0 white;">'
                     f'{plant["name"].replace(" WWTP","")}</div>',
                icon_size=(120, 20),
                icon_anchor=(60, 10),
            ),
        ).add_to(plant_layer)

    plant_layer.add_to(m)

    # ── Layer 3: Application Heatmap (urgency-weighted) ───────────────────────
    if show_heatmap and not df.empty:
        heat_layer = folium.FeatureGroup(name="Application Density Heatmap", show=True)
        heat_data = []
        for _, row in df.iterrows():
            weight = {"Overdue": 3.0, "At Risk": 2.0}.get(row.get("sla_status", ""), 1.0)
            heat_data.append([row["lat"], row["lon"], weight])

        HeatMap(
            heat_data,
            min_opacity=0.3,
            radius=18,
            blur=15,
            gradient={"0.2": "blue", "0.5": "cyan", "0.75": "lime", "1.0": "red"},
        ).add_to(heat_layer)
        heat_layer.add_to(m)

    # ── Layer 4: Individual WCR Application Markers ───────────────────────────
    if show_applications and not df.empty:
        app_layer = folium.FeatureGroup(name="WCR Applications", show=True)

        for _, row in df.iterrows():
            color = STATUS_MARKER_COLORS.get(row.get("status", ""), "#3498db")
            su = row.get("service_units", 1)
            radius = max(5, min(14, 4 + su * 0.4))

            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=radius,
                color="white",
                weight=1.5,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                popup=_make_app_popup(row),
                tooltip=folium.Tooltip(
                    f"{row['application_id']} | {row.get('status','')} | {row.get('sla_status','')}",
                    sticky=False,
                ),
            ).add_to(app_layer)

        app_layer.add_to(m)

    # ── Layer 5: Capacity Alert Buffers ───────────────────────────────────────
    if show_buffers and buffer_gdf is not None and not buffer_gdf.empty:
        buffer_layer = folium.FeatureGroup(name="Capacity Alert Zones (0.5mi buffer)", show=True)
        try:
            folium.GeoJson(
                buffer_gdf.__geo_interface__,
                style_function=lambda x: {
                    "fillColor": "#e74c3c",
                    "color": "#e74c3c",
                    "weight": 2,
                    "fillOpacity": 0.12,
                    "dashArray": "6 4",
                },
                tooltip=folium.Tooltip("⚠️ Capacity Alert Zone — 0.5mi buffer from stressed zone", sticky=True),
            ).add_to(buffer_layer)
        except Exception:
            pass
        buffer_layer.add_to(m)

    # ── Layer 6: Application Density Hexbins ──────────────────────────────────
    if show_hexbins and hotspot_gdf is not None and not hotspot_gdf.empty:
        hex_layer = folium.FeatureGroup(name="Application Density Grid", show=False)
        max_density = hotspot_gdf["density"].max() if "density" in hotspot_gdf.columns else 1

        def hex_color(count, max_c):
            ratio = count / max(max_c, 1)
            if ratio < 0.2:
                return "#dbeafe"
            elif ratio < 0.5:
                return "#60a5fa"
            elif ratio < 0.8:
                return "#2563eb"
            else:
                return "#1e3a8a"

        for _, hrow in hotspot_gdf.iterrows():
            try:
                hc = hex_color(hrow["density"], max_density)
                folium.GeoJson(
                    gpd.GeoDataFrame([hrow], crs="EPSG:4326").__geo_interface__,
                    style_function=lambda x, c=hc: {
                        "fillColor": c,
                        "color": "none",
                        "fillOpacity": 0.55,
                    },
                    tooltip=folium.Tooltip(f"{int(hrow['density'])} applications", sticky=True),
                ).add_to(hex_layer)
            except Exception:
                pass
        hex_layer.add_to(m)

    # ── Map controls ──────────────────────────────────────────────────────────
    folium.LayerControl(collapsed=False, position="topright").add_to(m)
    MiniMap(position="bottomright", width=150, height=120, zoom_level_offset=-5).add_to(m)

    return m


def render_capacity_map(df, zones_gdf, plants_gdf, zone_util_df, proj_df,
                         buffer_gdf, hotspot_gdf):
    """Main render function for Module 1."""

    # ── Sidebar filters ───────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("---")
        st.markdown("### Map Filters")

        cap_filter = st.multiselect(
            "Capacity Status",
            ["Available", "Near Limit", "At Limit"],
            default=["Available", "Near Limit", "At Limit"],
            key="map_cap_filter",
        )

        status_filter = st.multiselect(
            "Application Status",
            df["status"].unique().tolist(),
            default=df["status"].unique().tolist(),
            key="map_status_filter",
        )

        district_filter = st.multiselect(
            "Council District",
            sorted(df["council_district"].unique().tolist()),
            default=[],
            key="map_district_filter",
            placeholder="All districts",
        )

        col1, col2 = st.columns(2)
        with col1:
            show_buffers = st.checkbox("Alert Buffers", value=True, key="map_show_buffers")
        with col2:
            show_heatmap = st.checkbox("Heatmap", value=True, key="map_show_heatmap")

        show_hexbins = st.checkbox("Density Grid", value=False, key="map_show_hexbins")
        flagged_only = st.checkbox("Flagged Only", value=False, key="map_flagged_only")

        # Date range
        min_date = df["submission_date"].min().date()
        max_date = df["submission_date"].max().date()
        date_range = st.slider(
            "Submission Date Range",
            min_value=min_date,
            max_value=max_date,
            value=(min_date, max_date),
            key="map_date_range",
        )

    # Apply filters
    filtered = df.copy()
    filtered = filtered[filtered["capacity_status"].isin(cap_filter)]
    filtered = filtered[filtered["status"].isin(status_filter)]
    if district_filter:
        filtered = filtered[filtered["council_district"].isin(district_filter)]
    if flagged_only:
        filtered = filtered[filtered["capacity_flag"] == True]
    filtered = filtered[
        (filtered["submission_date"].dt.date >= date_range[0]) &
        (filtered["submission_date"].dt.date <= date_range[1])
    ]

    # ── Top metrics row ───────────────────────────────────────────────────────
    st.markdown(render_section_header("MODULE 1", "Spatial Capacity Map"), unsafe_allow_html=True)

    total_apps = len(filtered)
    stressed_zones = zone_util_df[zone_util_df["status"].isin(["Near Limit", "At Limit"])]["plant_id"].tolist() if zone_util_df is not None else []
    apps_in_stressed = len(filtered[filtered["treatment_plant_id"].isin(stressed_zones)])
    avg_days = filtered["days_open"].mean() if not filtered.empty else 0
    sla_compliance = (filtered["sla_status"].isin(["On Track", "Completed"]).sum() / max(len(filtered), 1)) * 100

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(render_metric_card("Total Active Applications", f"{total_apps:,}",
                                       f"Filtered from 250 total", color="blue"), unsafe_allow_html=True)
    with c2:
        color = "red" if apps_in_stressed > 30 else "amber"
        st.markdown(render_metric_card("Apps in Stressed Zones", f"{apps_in_stressed:,}",
                                       "Near/At-Limit zones", color=color), unsafe_allow_html=True)
    with c3:
        delta_dir = "down" if avg_days > 8 else "up"
        st.markdown(render_metric_card("Avg Processing Days", f"{avg_days:.1f}",
                                       "SLA target: 10 biz days", delta_dir=delta_dir, color="blue"), unsafe_allow_html=True)
    with c4:
        color = "green" if sla_compliance >= 90 else ("amber" if sla_compliance >= 75 else "red")
        st.markdown(render_metric_card("SLA Compliance", f"{sla_compliance:.0f}%",
                                       "30-day rolling rate", color=color), unsafe_allow_html=True)

    # ── Alert banners ─────────────────────────────────────────────────────────
    at_limit_zones = zone_util_df[zone_util_df["status"] == "At Limit"] if zone_util_df is not None else pd.DataFrame()
    overdue_count = (filtered["sla_status"] == "Overdue").sum()

    if not at_limit_zones.empty:
        names = ", ".join(at_limit_zones["plant_name"].head(3).tolist())
        st.markdown(
            f'<div style="background:#fee2e2;border:1px solid #fca5a5;border-radius:8px;padding:10px 16px;'
            f'margin:8px 0;color:#991b1b;font-weight:600;font-size:0.88rem;">'
            f'&#10060; AT-LIMIT ZONES: {names} — New reservations restricted pending capacity review</div>',
            unsafe_allow_html=True,
        )

    if overdue_count > 0:
        st.markdown(
            f'<div style="background:#fef9c3;border:1px solid #fde68a;border-radius:8px;padding:10px 16px;'
            f'margin:4px 0;color:#713f12;font-weight:600;font-size:0.88rem;">'
            f'&#9888; {overdue_count} OVERDUE APPLICATIONS in current view — Supervisor attention required</div>',
            unsafe_allow_html=True,
        )

    # ── Main map ──────────────────────────────────────────────────────────────
    m = build_folium_map(
        filtered, zones_gdf, plants_gdf, zone_util_df, proj_df,
        buffer_gdf=buffer_gdf if show_buffers else None,
        hotspot_gdf=hotspot_gdf if show_hexbins else None,
        show_buffers=show_buffers,
        show_heatmap=show_heatmap,
        show_hexbins=show_hexbins,
        show_applications=True,
    )

    map_data = st_folium(m, width="100%", height=580, returned_objects=[], key="main_map")

    # ── Spatial insights panel ────────────────────────────────────────────────
    st.markdown(render_section_header("SPATIAL INSIGHTS", "Zone Analysis"), unsafe_allow_html=True)

    col_a, col_b = st.columns(2)

    with col_a:
        if zone_util_df is not None and not zone_util_df.empty:
            import plotly.express as px
            zone_counts = filtered.groupby("treatment_plant_id").size().reset_index(name="count")
            zone_counts = zone_counts.merge(
                zone_util_df[["plant_id", "plant_name", "utilization_pct", "status"]],
                left_on="treatment_plant_id", right_on="plant_id", how="left",
            ).sort_values("count", ascending=True)

            color_map = {"Available": "#27ae60", "Near Limit": "#f39c12", "At Limit": "#e74c3c"}
            zone_counts["color"] = zone_counts["status"].map(color_map).fillna("#3498db")

            fig = px.bar(
                zone_counts.tail(15),
                x="count",
                y="plant_name",
                orientation="h",
                color="status",
                color_discrete_map=color_map,
                title="Applications by Treatment Plant Zone",
                labels={"count": "Applications", "plant_name": "Plant Zone"},
            )
            fig.update_layout(
                height=380, margin=dict(l=0, r=10, t=40, b=10),
                showlegend=True, legend_title="Zone Status",
                plot_bgcolor="white", paper_bgcolor="white",
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        import plotly.express as px
        if not filtered.empty:
            scatter_df = filtered[filtered["days_to_complete"].notna()].copy()
            if not scatter_df.empty:
                fig2 = px.scatter(
                    scatter_df,
                    x="submission_date",
                    y="days_to_complete",
                    color="capacity_status",
                    color_discrete_map={
                        "Available": "#27ae60",
                        "Near Limit": "#f39c12",
                        "At Limit": "#e74c3c",
                    },
                    title="Processing Time vs Submission Date",
                    labels={"submission_date": "Submission Date", "days_to_complete": "Days to Complete"},
                    hover_data=["application_id", "status", "assigned_analyst"],
                    opacity=0.7,
                )
                fig2.add_hline(y=10, line_dash="dash", line_color="#e74c3c",
                               annotation_text="10-day SLA target")
                fig2.update_layout(
                    height=380, margin=dict(l=0, r=10, t=40, b=10),
                    plot_bgcolor="white", paper_bgcolor="white",
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No completed applications in current filter for scatter plot.")
