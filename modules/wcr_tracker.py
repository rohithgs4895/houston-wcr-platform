"""
Module 2: WCR Application Tracker
Houston WCR Intelligence Platform

Simulates the Q-Flow + ILMS interface with GIS intelligence.
Features:
- Live system status bar
- KPI cards
- Filterable/sortable application table
- Application detail panel with mini-map
- Bulk action controls
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import date, datetime
import pytz
import plotly.express as px
import plotly.graph_objects as go

from utils.styling import (
    COLORS, render_section_header, render_metric_card,
    render_system_status_bar, render_badge, render_alert
)
from gis.capacity_analysis import get_utilization_color

STATUS_EMOJI = {
    "Pending": "🔵",
    "In Review": "🟣",
    "Approved": "🟢",
    "Denied": "🔴",
    "Revision Needed": "🟠",
    "On Hold": "⚫",
}

SLA_EMOJI = {
    "On Track": "✅",
    "At Risk": "⚠️",
    "Overdue": "🚨",
    "Completed": "✔️",
}


def _render_sla_status(sla_info):
    """Render SLA status using pure Streamlit components."""
    fill = min(100, int(sla_info["percent_elapsed"]))
    status = sla_info["status"]
    deadline = sla_info["deadline"]
    msg = f"SLA {status} — {fill}% of deadline elapsed | Due: {deadline}"
    if status == "On Track":
        st.success(f"✅ {msg}")
    elif status == "At Risk":
        st.warning(f"⚠️ {msg}")
    elif status == "Overdue":
        st.error(f"🚨 {msg}")
    else:
        st.info(f"✔️ {msg}")
    st.progress(fill / 100)


def _render_fee_table(row):
    """Render impact fee breakdown using pure Streamlit components."""
    f1, f2, f3, f4 = st.columns(4)
    f1.metric("Wastewater Fee", f"${row.get('wastewater_impact_fee', 0):,.2f}")
    f2.metric("Water Fee", f"${row.get('water_impact_fee', 0):,.2f}")
    f3.metric("Admin Fee", "$150.00")
    f4.metric("TOTAL", f"${row.get('total_impact_fee', 0):,.2f}")
    st.caption(
        f"{row.get('service_units', 0):.2f} SU × 250 gpd = "
        f"{row.get('service_units', 0) * 250:,.0f} gpd/day"
    )


def _detail_mini_map(app_row, plants_gdf, zones_gdf, zone_util_df):
    """Build a small Folium map for the selected application."""
    lat = float(app_row["lat"])
    lon = float(app_row["lon"])

    m = folium.Map(location=[lat, lon], zoom_start=12, tiles="CartoDB Positron", prefer_canvas=True)

    # Zone layer (light)
    if zones_gdf is not None and not zones_gdf.empty:
        pid = app_row.get("treatment_plant_id")
        zone = zones_gdf[zones_gdf["plant_id"] == pid] if pid else gpd.GeoDataFrame()
        if not zone.empty:
            util_pct = 45
            if zone_util_df is not None and not zone_util_df.empty:
                util_row = zone_util_df[zone_util_df["plant_id"] == pid]
                if not util_row.empty:
                    util_pct = util_row.iloc[0]["utilization_pct"]
            color = get_utilization_color(util_pct)
            try:
                folium.GeoJson(
                    zone.__geo_interface__,
                    style_function=lambda x, c=color: {"fillColor": c, "color": c, "weight": 2, "fillOpacity": 0.25},
                    tooltip=f"Service Zone: {pid}",
                ).add_to(m)
            except Exception:
                pass

    # Application pin
    capacity_status = app_row.get("capacity_status", "Available")
    pin_color = {"Available": "green", "Near Limit": "orange", "At Limit": "red"}.get(capacity_status, "blue")
    folium.Marker(
        location=[lat, lon],
        tooltip=app_row.get("application_id", ""),
        popup=f"<b>{app_row.get('property_address','')}</b><br>Status: {app_row.get('status','')}<br>Zone: {capacity_status}",
        icon=folium.Icon(color=pin_color, icon="home", prefix="fa"),
    ).add_to(m)

    # Nearest treatment plant + line
    if plants_gdf is not None and not plants_gdf.empty:
        pid = app_row.get("treatment_plant_id")
        if pid:
            plant = plants_gdf[plants_gdf["id"] == pid]
            if not plant.empty:
                plant_row = plant.iloc[0]
                folium.Marker(
                    location=[plant_row["lat"], plant_row["lon"]],
                    tooltip=plant_row["name"],
                    icon=folium.Icon(color="blue", icon="tint", prefix="fa"),
                ).add_to(m)
                folium.PolyLine(
                    [[lat, lon], [plant_row["lat"], plant_row["lon"]]],
                    color="#003087",
                    weight=2,
                    dash_array="6 4",
                    tooltip=f"Distance: {app_row.get('nearest_sewer_dist_ft', 0):,.0f} ft",
                ).add_to(m)

    return m


def _build_status_timeline(row):
    """Generate a visual status timeline."""
    stages = [
        ("Submitted", row.get("submission_date"), True),
        ("Assigned", row.get("submission_date"), row.get("status") not in ["Pending"]),
        ("In Review", None, row.get("status") in ["In Review", "Approved", "Denied", "Revision Needed"]),
        ("Letter Issued", None, row.get("status") in ["Approved", "Denied"]),
    ]
    html = '<div style="display:flex;align-items:center;gap:0;margin:12px 0;">'
    for i, (label, dt, done) in enumerate(stages):
        color = COLORS["houston_blue"] if done else "#e5e7eb"
        text_color = "#2c3e50" if done else "#9ca3af"
        dt_str = ""
        if dt is not None and done:
            try:
                dt_str = f'<div style="font-size:10px;color:#9ca3af;">{pd.to_datetime(dt).strftime("%m/%d/%y")}</div>'
            except Exception:
                pass
        html += f"""
        <div style="text-align:center;flex:1;">
            <div style="width:28px;height:28px;border-radius:50%;background:{color};
                        margin:0 auto 4px;display:flex;align-items:center;justify-content:center;
                        color:white;font-size:12px;font-weight:700;">{i+1}</div>
            <div style="font-size:11px;font-weight:600;color:{text_color};">{label}</div>
            {dt_str}
        </div>
        """
        if i < len(stages) - 1:
            line_color = COLORS["houston_blue"] if done else "#e5e7eb"
            html += f'<div style="flex:0 0 20px;height:2px;background:{line_color};margin-top:14px;"></div>'
    html += "</div>"
    return html


import geopandas as gpd


def render_wcr_tracker(df, plants_gdf, zones_gdf, zone_util_df):
    """Main render function for Module 2."""

    # ── System status bar ─────────────────────────────────────────────────────
    st.markdown(render_section_header("MODULE 2", "WCR Application Tracker"), unsafe_allow_html=True)
    now_str = datetime.now(pytz.timezone("America/Chicago")).strftime("%m/%d/%Y %I:%M %p CT")
    st.markdown(render_system_status_bar(now_str), unsafe_allow_html=True)

    # ── KPI row ───────────────────────────────────────────────────────────────
    today = pd.Timestamp.now().normalize()
    month_start = today - pd.Timedelta(days=30)
    this_month = df[df["submission_date"] >= month_start]
    pending_assign = (df["status"] == "Pending").sum()
    at_risk_overdue = ((df["sla_status"].isin(["At Risk", "Overdue"])) & ~df["status"].isin(["Approved", "Denied"])).sum()
    avg_days = df[df["days_open"] > 0]["days_open"].mean()
    total_fees_month = this_month["total_impact_fee"].sum()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(render_metric_card("Applications (30d)", f"{len(this_month):,}", color="blue"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_metric_card("Pending Assignment", f"{pending_assign}", color="amber"), unsafe_allow_html=True)
    with c3:
        color = "red" if at_risk_overdue > 5 else "amber"
        st.markdown(render_metric_card("At Risk / Overdue", f"{at_risk_overdue}", color=color), unsafe_allow_html=True)
    with c4:
        st.markdown(render_metric_card("Avg Processing Days", f"{avg_days:.1f}d", color="blue"), unsafe_allow_html=True)
    with c5:
        fee_str = f"${total_fees_month/1e6:.2f}M" if total_fees_month >= 1e6 else f"${total_fees_month:,.0f}"
        st.markdown(render_metric_card("Impact Fees (30d)", fee_str, color="green"), unsafe_allow_html=True)

    # ── Sidebar filters ───────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("---")
        st.markdown("### Tracker Filters")

        type_filter = st.multiselect(
            "Application Type", df["development_type"].unique().tolist(),
            default=[], key="trk_type", placeholder="All types",
        )
        status_filter = st.multiselect(
            "Status", df["status"].unique().tolist(),
            default=[], key="trk_status", placeholder="All statuses",
        )
        analyst_filter = st.multiselect(
            "Assigned Analyst", sorted(df["assigned_analyst"].unique().tolist()),
            default=[], key="trk_analyst", placeholder="All analysts",
        )
        district_filter = st.multiselect(
            "Council District", sorted(df["council_district"].unique().tolist()),
            default=[], key="trk_district", placeholder="All districts",
        )
        zone_filter = st.multiselect(
            "Treatment Plant Zone", sorted(df["treatment_plant_id"].unique().tolist()),
            default=[], key="trk_zone", placeholder="All zones",
        )
        sla_filter = st.multiselect(
            "SLA Status", ["On Track", "At Risk", "Overdue", "Completed"],
            default=[], key="trk_sla", placeholder="All SLA",
        )
        col1, col2 = st.columns(2)
        with col1:
            flagged_only = st.checkbox("Flagged", key="trk_flagged")
        with col2:
            expedited_only = st.checkbox("Expedited", key="trk_expedited")

    # Apply filters
    filtered = df.copy()
    if type_filter:
        filtered = filtered[filtered["development_type"].isin(type_filter)]
    if status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]
    if analyst_filter:
        filtered = filtered[filtered["assigned_analyst"].isin(analyst_filter)]
    if district_filter:
        filtered = filtered[filtered["council_district"].isin(district_filter)]
    if zone_filter:
        filtered = filtered[filtered["treatment_plant_id"].isin(zone_filter)]
    if sla_filter:
        filtered = filtered[filtered["sla_status"].isin(sla_filter)]
    if flagged_only:
        filtered = filtered[filtered["capacity_flag"] == True]
    if expedited_only:
        filtered = filtered[filtered["expedited"] == True]

    # ── Bulk actions bar ──────────────────────────────────────────────────────
    ba_cols = st.columns([2, 2, 2, 2, 2])
    with ba_cols[0]:
        st.markdown(f"**{len(filtered):,} records**")
    with ba_cols[1]:
        assign_analyst = st.selectbox(
            "Assign To", ["— Select —"] + sorted(df["assigned_analyst"].unique().tolist()),
            key="bulk_assign", label_visibility="collapsed",
        )
    with ba_cols[2]:
        if st.button("📥 Export CSV", use_container_width=True, key="btn_export"):
            csv = filtered.to_csv(index=False).encode("utf-8")
            st.download_button("Download CSV", csv, "wcr_applications.csv", "text/csv", key="dl_csv")
    with ba_cols[3]:
        if st.button("📄 Generate Letters", use_container_width=True, key="btn_letters"):
            st.info("This would trigger the WCR letter generation workflow in ILMS. "
                    f"{len(filtered[filtered['status']=='Approved'])} approved letters ready for generation.")
    with ba_cols[4]:
        if st.button("✔ Mark Reviewed", use_container_width=True, key="btn_reviewed"):
            st.success("Selected applications marked as reviewed in Q-Flow.")

    # ── Application table ─────────────────────────────────────────────────────
    def row_color(row):
        if row["sla_status"] == "Overdue":
            return ["background-color: #fee2e2"] * len(row)
        elif row["sla_status"] == "At Risk":
            return ["background-color: #fef9c3"] * len(row)
        return [""] * len(row)

    display_cols = {
        "application_id": "App ID",
        "property_address": "Address",
        "development_type": "Type",
        "assigned_analyst": "Analyst",
        "treatment_plant_id": "Zone",
        "status": "Status",
        "days_open": "Days Open",
        "sla_status": "SLA",
        "total_impact_fee": "Impact Fee",
        "capacity_flag": "⚠ Flag",
    }

    table_df = filtered[list(display_cols.keys())].rename(columns=display_cols).copy()
    table_df["Impact Fee"] = table_df["Impact Fee"].apply(lambda x: f"${x:,.0f}")
    table_df["⚠ Flag"] = table_df["⚠ Flag"].apply(lambda x: "⚠️" if x else "")

    styled = table_df.style.apply(
        lambda row: row_color(filtered.iloc[table_df.index.get_loc(row.name)] if row.name in table_df.index else row),
        axis=1,
    )

    selection = st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True,
        height=320,
        on_select="rerun",
        selection_mode="single-row",
        key="app_table",
    )

    # ── Application detail panel ──────────────────────────────────────────────
    selected_rows = selection.selection.get("rows", []) if hasattr(selection, "selection") else []

    if selected_rows:
        idx = selected_rows[0]
        app_row = filtered.iloc[idx]
        st.session_state["selected_app_id"] = app_row["application_id"]

    app_id = st.session_state.get("selected_app_id")
    if app_id and app_id in df["application_id"].values:
        app_row = df[df["application_id"] == app_id].iloc[0]

        st.markdown("---")
        st.markdown(render_section_header("DETAIL VIEW", f"Application {app_id}"), unsafe_allow_html=True)

        col_left, col_right = st.columns([6, 4])

        with col_left:
            # Capacity check result
            cap_status = app_row.get("capacity_status", "Available")
            cap_icon = {"Available": "✅ CAPACITY PASS", "Near Limit": "⚠️ NEAR LIMIT", "At Limit": "❌ AT LIMIT"}
            cap_color = {"Available": "#d1fae5", "Near Limit": "#fef9c3", "At Limit": "#fee2e2"}
            cap_text_color = {"Available": "#065f46", "Near Limit": "#713f12", "At Limit": "#991b1b"}

            st.markdown(
                f'<div style="background:{cap_color.get(cap_status,"#dbeafe")};'
                f'border-radius:8px;padding:12px 16px;margin-bottom:12px;'
                f'font-weight:800;font-size:1.1rem;color:{cap_text_color.get(cap_status,"#1e40af")};">'
                f'{cap_icon.get(cap_status, "UNKNOWN")} — {app_row.get("treatment_plant_id","N/A")} Service Zone'
                f'</div>',
                unsafe_allow_html=True,
            )

            # SLA status
            from utils.sla_engine import get_sla_status as get_sla
            sla_info = get_sla(app_row["submission_date"], app_row["status"], app_row.get("expedited", False))
            _render_sla_status(sla_info)

            # Application fields
            info_cols = st.columns(2)
            fields_left = [
                ("Application ID", app_row.get("application_id")),
                ("Applicant / Developer", app_row.get("applicant_name")),
                ("Property Address", app_row.get("property_address")),
                ("Development Type", app_row.get("development_type")),
                ("Use Type", app_row.get("use_type")),
                ("Status", app_row.get("status")),
                ("Assigned Analyst", app_row.get("assigned_analyst")),
            ]
            fields_right = [
                ("Council District", app_row.get("council_district")),
                ("Treatment Plant Zone", app_row.get("treatment_plant_id")),
                ("Submission Date", pd.to_datetime(app_row.get("submission_date")).strftime("%m/%d/%Y")),
                ("SLA Deadline", pd.to_datetime(app_row.get("sla_deadline")).strftime("%m/%d/%Y")),
                ("Days Open", f"{app_row.get('days_open', 0)} business days"),
                ("Nearest Sewer Dist.", f"{app_row.get('nearest_sewer_dist_ft', 0):,} ft"),
                ("Expedited Review", "Yes" if app_row.get("expedited") else "No"),
            ]
            with info_cols[0]:
                for label, val in fields_left:
                    st.markdown(f"**{label}:** {val}")
            with info_cols[1]:
                for label, val in fields_right:
                    st.markdown(f"**{label}:** {val}")

            # System IDs
            st.markdown(
                f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;'
                f'padding:10px 14px;margin:10px 0;font-family:monospace;font-size:12px;color:#1a1a1a;">'
                f'Q-Flow Queue ID: <b>{app_row.get("q_flow_queue_id","N/A")}</b> &nbsp;|&nbsp; '
                f'ILMS Permit ID: <b>{app_row.get("ilms_permit_id","N/A")}</b></div>',
                unsafe_allow_html=True,
            )

            # Status timeline
            st.markdown("**Application Timeline**")
            st.markdown(_build_status_timeline(app_row), unsafe_allow_html=True)

            # Notes
            st.markdown(f"**Procedural Notes:** _{app_row.get('notes','')}_")

            # Impact fee breakdown
            st.markdown("**Impact Fee Breakdown**")
            _render_fee_table(app_row)

        with col_right:
            st.markdown("**Location & Zone Map**")
            mini_m = _detail_mini_map(app_row, plants_gdf, zones_gdf, zone_util_df)
            st_folium(mini_m, width="100%", height=320, returned_objects=[], key=f"mini_map_{app_id}")

            # Capacity status card
            st.markdown("**Zone Capacity Check**")
            cap1, cap2, cap3 = st.columns(3)
            cap1.metric("Service Units", f"{app_row.get('service_units', 0):.1f}")
            cap2.metric("Zone Status", cap_status)
            cap3.metric("Gallons/Day", f"{app_row.get('service_units', 0) * 250:,.0f}")
    else:
        st.info("Select a row in the table above to view application details and mini-map.")
