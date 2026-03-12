"""
Module 3: Supervisor Operations Center
Houston WCR Intelligence Platform

Daily operational nerve center with:
- Daily ops report card (Kronos + Q-Flow simulation)
- Analyst workload grid
- Performance analytics (Plotly charts)
- Capacity intelligence table
- Open records tracker
- GIMS/GeoLink sync status panel
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime, timedelta

from utils.styling import (
    COLORS, render_section_header, render_metric_card, render_alert
)
from utils.sla_engine import generate_daily_metrics, get_compliance_rate
from gis.capacity_analysis import get_utilization_color

ANALYST_COLORS = {
    "Maria Gonzalez":    "#3498db",
    "James Okafor":      "#9b59b6",
    "Sarah Chen":        "#e67e22",
    "David Tran":        "#27ae60",
    "Patricia Williams": "#e74c3c",
    "Robert Martinez":   "#f39c12",
}

ANALYST_INITIALS = {
    "Maria Gonzalez":    "MG",
    "James Okafor":      "JO",
    "Sarah Chen":        "SC",
    "David Tran":        "DT",
    "Patricia Williams": "PW",
    "Robert Martinez":   "RM",
}

MAX_WORKLOAD = 25  # max apps per analyst

OPEN_RECORDS = [
    {"id": "ORR-2025-0112", "type": "Open Records Request", "requestor": "Houston Chronicle",
     "submitted": "2025-12-01", "due": "2025-12-11", "status": "In Progress", "assigned": "Maria Gonzalez"},
    {"id": "ORR-2025-0098", "type": "MUD Boundary Review", "requestor": "Harris County MUD 89",
     "submitted": "2025-11-20", "due": "2025-12-20", "status": "Pending Review", "assigned": "James Okafor"},
    {"id": "ORR-2025-0087", "type": "Special Capacity Study", "requestor": "City Planning Dept",
     "submitted": "2025-11-10", "due": "2026-01-10", "status": "In Progress", "assigned": "Sarah Chen"},
    {"id": "ORR-2025-0074", "type": "Open Records Request", "requestor": "Hines Development LLC",
     "submitted": "2025-10-28", "due": "2025-11-07", "status": "Completed", "assigned": "David Tran"},
    {"id": "ORR-2025-0061", "type": "Interagency Review", "requestor": "TxDOT — District 12",
     "submitted": "2025-10-15", "due": "2025-11-30", "status": "Awaiting Response", "assigned": "Robert Martinez"},
    {"id": "ORR-2025-0055", "type": "MUD Connection Review", "requestor": "Harris County MUD 142",
     "submitted": "2025-10-02", "due": "2025-11-02", "status": "Completed", "assigned": "Patricia Williams"},
    {"id": "ORR-2025-0049", "type": "Special Capacity Study", "requestor": "METRO Planning",
     "submitted": "2025-09-25", "due": "2025-12-31", "status": "In Progress", "assigned": "Maria Gonzalez"},
]

ANALYST_PRESENT = {
    "Maria Gonzalez":    True,
    "James Okafor":      True,
    "Sarah Chen":        False,  # Leave
    "David Tran":        True,
    "Patricia Williams": True,
    "Robert Martinez":   True,
}


def _analyst_card_html(name, stats, present_status):
    initials = ANALYST_INITIALS.get(name, name[:2].upper())
    color = ANALYST_COLORS.get(name, "#3498db")
    open_apps = stats["open"]
    max_cap = MAX_WORKLOAD
    pct = min(100, (open_apps / max_cap) * 100)
    bar_color = "#27ae60" if pct < 60 else ("#f39c12" if pct < 85 else "#e74c3c")

    status_dot = {"present": "🟢", "absent": "🔴", "leave": "🟡"}.get(present_status, "⚫")
    status_label = {"present": "Present", "absent": "Absent (Unplanned)", "leave": "Approved Leave"}.get(present_status, "Unknown")

    overdue_badge = ""
    if stats["overdue"] > 0:
        overdue_badge = f'<span style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700;">{stats["overdue"]} overdue</span>'

    return f"""
    <div style="background:white;border-radius:12px;padding:16px;
                box-shadow:0 2px 8px rgba(0,0,0,0.08);border:1px solid #e5e7eb;
                transition:transform 0.15s;height:100%;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
            <div style="width:44px;height:44px;border-radius:50%;background:{color};
                        display:flex;align-items:center;justify-content:center;
                        color:white;font-weight:800;font-size:1rem;flex-shrink:0;">{initials}</div>
            <div>
                <div style="font-weight:700;color:#2c3e50;font-size:0.95rem;">{name}</div>
                <div style="font-size:12px;color:#666;">{status_dot} {status_label}</div>
            </div>
        </div>
        <div style="margin-bottom:8px;">
            <div style="display:flex;justify-content:space-between;font-size:12px;color:#666;margin-bottom:3px;">
                <span>Workload</span><span><b>{open_apps}</b> / {max_cap}</span>
            </div>
            <div style="background:#e5e7eb;border-radius:4px;height:8px;overflow:hidden;">
                <div style="background:{bar_color};width:{pct:.0f}%;height:100%;border-radius:4px;"></div>
            </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:12px;margin-top:8px;">
            <div>Today's Assigns: <b>{stats['today_assigns']}</b></div>
            <div>30d Compliance: <b>{stats['compliance']:.0f}%</b></div>
            <div>In Review: <b>{stats['in_review']}</b></div>
            <div>{overdue_badge}</div>
        </div>
    </div>
    """


def _get_analyst_stats(df):
    """Compute per-analyst statistics."""
    stats = {}
    for analyst in ANALYST_INITIALS.keys():
        adf = df[df["assigned_analyst"] == analyst]
        open_apps = len(adf[adf["status"].isin(["Pending", "In Review", "On Hold", "Revision Needed"])])
        overdue = len(adf[adf["sla_status"] == "Overdue"])
        in_review = len(adf[adf["status"] == "In Review"])
        compliance = get_compliance_rate(adf, 30) if not adf.empty else 100.0

        # Simulate today's assignments
        today_assigns = np.random.RandomState(abs(hash(analyst)) % 2**31).randint(0, 5)

        stats[analyst] = {
            "open": open_apps,
            "overdue": overdue,
            "in_review": in_review,
            "compliance": compliance,
            "today_assigns": today_assigns,
        }
    return stats


def _sla_trend_chart(df):
    """SLA compliance trend over last 30 days."""
    today = date.today()
    dates = [today - timedelta(days=i) for i in range(29, -1, -1)]

    np.random.seed(42)
    compliance_series = []
    for d in dates:
        base = 88 + np.random.normal(0, 4)
        compliance_series.append(min(100, max(65, base)))

    trend_df = pd.DataFrame({"date": dates, "compliance": compliance_series})

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trend_df["date"], y=trend_df["compliance"],
        mode="lines+markers", name="Compliance %",
        line=dict(color=COLORS["houston_blue"], width=2.5),
        marker=dict(size=4),
        fill="tonexty",
    ))
    # Target reference line
    fig.add_hline(y=90, line_dash="dash", line_color="#e74c3c", line_width=1.5,
                  annotation_text="90% Target", annotation_position="top right")

    # Color area: above target green, below red
    fig.add_hrect(y0=90, y1=100, fillcolor="#d1fae5", opacity=0.2, line_width=0)
    fig.add_hrect(y0=0, y1=90, fillcolor="#fee2e2", opacity=0.1, line_width=0)

    fig.update_layout(
        title="SLA Compliance — 30-Day Trend",
        xaxis_title=None, yaxis_title="Compliance %",
        yaxis=dict(range=[60, 105]),
        height=280, margin=dict(l=0, r=10, t=40, b=10),
        plot_bgcolor="white", paper_bgcolor="white",
        showlegend=False,
    )
    return fig


def _analyst_status_chart(df):
    """Grouped bar: applications by status × analyst."""
    analysts = list(ANALYST_INITIALS.keys())
    statuses = ["Pending", "In Review", "Overdue"]
    colors_map = {"Pending": "#3498db", "In Review": "#9b59b6", "Overdue": "#e74c3c"}

    fig = go.Figure()
    for status in statuses:
        counts = []
        for analyst in analysts:
            adf = df[df["assigned_analyst"] == analyst]
            if status == "Overdue":
                c = len(adf[(adf["sla_status"] == "Overdue") & ~adf["status"].isin(["Approved", "Denied"])])
            else:
                c = len(adf[adf["status"] == status])
            counts.append(c)

        fig.add_trace(go.Bar(
            name=status,
            x=[a.split()[0] for a in analysts],
            y=counts,
            marker_color=colors_map[status],
        ))

    fig.update_layout(
        title="Applications by Analyst",
        barmode="group", height=280,
        margin=dict(l=0, r=10, t=40, b=10),
        plot_bgcolor="white", paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        xaxis_title=None, yaxis_title="Count",
    )
    return fig


def _weekly_heatmap_chart(df):
    """Weekly volume heatmap: day-of-week × week."""
    df2 = df.copy()
    df2["submission_date"] = pd.to_datetime(df2["submission_date"])
    df2["dow"] = df2["submission_date"].dt.dayofweek  # 0=Mon
    df2["week"] = df2["submission_date"].dt.isocalendar().week.astype(int)

    # Last 8 weeks
    today = pd.Timestamp.now()
    cutoff = today - pd.Timedelta(weeks=8)
    df2 = df2[df2["submission_date"] >= cutoff]

    pivot = df2.groupby(["week", "dow"]).size().reset_index(name="count")
    if pivot.empty:
        weeks = sorted(df2["week"].unique())[-8:] if not df2.empty else list(range(1, 9))
        dows = list(range(5))
        data = np.random.randint(0, 8, size=(len(weeks), 5))
    else:
        weeks = sorted(pivot["week"].unique())[-8:]
        dows = [0, 1, 2, 3, 4]
        data = np.zeros((len(weeks), 5))
        for _, row in pivot.iterrows():
            if row["week"] in weeks and row["dow"] < 5:
                wi = weeks.index(row["week"])
                data[wi][int(row["dow"])] = row["count"]

    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    week_labels = [f"Wk {w}" for w in weeks]

    fig = go.Figure(data=go.Heatmap(
        z=data,
        x=day_labels,
        y=week_labels,
        colorscale=[[0, "#f0f9ff"], [0.5, "#60a5fa"], [1, "#1e3a8a"]],
        showscale=True,
        hovertemplate="%{y} %{x}: %{z} applications<extra></extra>",
    ))
    fig.update_layout(
        title="Weekly Application Volume",
        height=280, margin=dict(l=0, r=10, t=40, b=10),
        xaxis_title=None, yaxis_title=None,
        plot_bgcolor="white", paper_bgcolor="white",
    )
    return fig


def _funnel_chart(df):
    """Application type funnel: submission → assignment → review → issued."""
    total = len(df)
    assigned = len(df[df["status"] != "Pending"])
    in_review = len(df[df["status"].isin(["In Review", "Approved", "Denied", "Revision Needed"])])
    issued = len(df[df["status"].isin(["Approved", "Denied"])])

    fig = go.Figure(go.Funnel(
        y=["Submitted", "Assigned", "Under Review", "Letter Issued"],
        x=[total, assigned, in_review, issued],
        textinfo="value+percent initial",
        marker=dict(color=[COLORS["houston_blue"], "#0072CE", "#27ae60", "#2ecc71"]),
        connector=dict(line=dict(color=COLORS["border"], width=1)),
    ))
    fig.update_layout(
        title="Application Processing Funnel",
        height=280, margin=dict(l=0, r=10, t=40, b=10),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    return fig


def _render_ops_report(metrics, today_str, staffing):
    st.subheader("📋 DAILY OPERATIONAL REPORT")
    st.caption(f"Date: {today_str}  |  Supervisor: On Duty  |  Shift: 08:00–17:00")
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**STAFFING (Kronos)**")
        st.metric("Analysts Present", f"{staffing['present']} / 6")
        st.metric("Absent (Unplanned)", staffing["absent_unplanned"])
        st.metric("On Leave (Approved)", staffing["leave"])
    with col2:
        st.markdown("**Q-FLOW QUEUE STATUS**")
        st.metric("New in Queue Today", metrics["new_today"])
        st.metric("Assigned Today", max(0, metrics["new_today"] - metrics["pending_assignment"] // 3))
        st.metric("Pending Assignment", metrics["pending_assignment"])
        st.metric("Queue Depth (Total)", metrics["queue_total"])

    st.divider()
    col3, col4 = st.columns(2)
    with col3:
        st.markdown("**LETTERS & DATA ENTRY**")
        st.metric("Letters Pending Review", metrics["letters_pending_review"])
        st.metric("Letters Pending Signature", metrics["letters_pending_sig"])
        st.metric("WCR Letters Issued Today", metrics["letters_issued_today"])
        st.metric("Accuracy Pass Rate", f"{metrics['accuracy_rate']:.1f}%")
    with col4:
        st.markdown("**SLA PERFORMANCE**")
        st.metric("On Track", metrics["on_track"])
        st.metric("At Risk", metrics["at_risk"])
        st.metric("Overdue", metrics["overdue"])
        st.metric("30-Day Compliance Rate", f"{metrics['compliance_rate']:.1f}%")


def _render_capacity_table(zone_util_df, proj_df):
    if zone_util_df is None or zone_util_df.empty:
        st.info("No capacity data available.")
        return

    display = zone_util_df[["plant_name", "utilization_pct", "status", "reserved_su", "available_su"]].copy()

    if proj_df is not None and not proj_df.empty:
        proj_cols = proj_df[["plant_id", "projected_pct", "risk_level", "pending_pipeline_su"]]
        merged = zone_util_df[["plant_id", "plant_name", "utilization_pct", "status",
                                "reserved_su", "available_su"]].merge(proj_cols, on="plant_id", how="left")
        merged = merged.rename(columns={
            "plant_name": "Plant Name",
            "utilization_pct": "Utilization %",
            "status": "Status",
            "reserved_su": "Reserved SU",
            "available_su": "Available SU",
            "projected_pct": "90-Day Proj. %",
            "risk_level": "Risk Level",
            "pending_pipeline_su": "Pending Pipeline SU",
        })
        display = merged.drop(columns=["plant_id"]).sort_values("Utilization %", ascending=False)
    else:
        display = display.rename(columns={
            "plant_name": "Plant Name",
            "utilization_pct": "Utilization %",
            "status": "Status",
            "reserved_su": "Reserved SU",
            "available_su": "Available SU",
        }).sort_values("Utilization %", ascending=False)

    st.dataframe(display, use_container_width=True, hide_index=True)


def render_supervisor_dashboard(df, zone_util_df, proj_df):
    """Main render function for Module 3."""

    today_str = date.today().strftime("%B %d, %Y")
    week_num = date.today().isocalendar()[1]
    year = date.today().year

    st.markdown(render_section_header("MODULE 3", "Supervisor Operations Center"), unsafe_allow_html=True)

    # Page header
    st.markdown(
        f"""<div style="background:{COLORS['houston_blue']};color:white;padding:14px 20px;
            border-radius:8px;margin-bottom:16px;border-left:5px solid {COLORS['houston_red']};">
            <div style="font-weight:800;font-size:1.1rem;">SUPERVISOR OPERATIONS CENTER</div>
            <div style="font-size:0.82rem;color:#a8c4e8;margin-top:3px;">
                Houston Water — Impact Fee Administration &nbsp;|&nbsp;
                {today_str} &nbsp;|&nbsp; Shift: 8:00 AM – 5:00 PM &nbsp;|&nbsp; Week {week_num} of {year}
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── Section 1: Daily Ops Report Card ─────────────────────────────────────
    st.markdown(render_section_header("SECTION 1", "Daily Operational Report"), unsafe_allow_html=True)

    metrics = generate_daily_metrics(df)

    # Staffing simulation
    present_list = [a for a, p in ANALYST_PRESENT.items() if p]
    absent_unplanned = sum(1 for a, p in ANALYST_PRESENT.items() if not p and a == "Sarah Chen")
    on_leave = sum(1 for a, p in ANALYST_PRESENT.items() if not p) - absent_unplanned
    staffing = {
        "present": len(present_list),
        "absent_unplanned": absent_unplanned,
        "leave": on_leave,
    }

    col_report, col_btn = st.columns([5, 1])
    with col_report:
        _render_ops_report(metrics, today_str, staffing)
    with col_btn:
        st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
        if st.button("📄 Export Daily Report", use_container_width=True, key="btn_daily_report"):
            report_text = (
                f"HOUSTON WATER — IMPACT FEE ADMINISTRATION\n"
                f"DAILY OPERATIONAL REPORT\n"
                f"Date: {today_str}\n"
                f"{'='*50}\n"
                f"Analysts Present: {staffing['present']}/6\n"
                f"Queue Depth: {metrics['queue_total']}\n"
                f"SLA Compliance (30d): {metrics['compliance_rate']:.1f}%\n"
                f"Overdue: {metrics['overdue']}\n"
            )
            st.download_button("Download Report", report_text,
                               "daily_ops_report.txt", "text/plain", key="dl_report")

        if metrics["overdue"] > 0:
            st.markdown(
                f'<div style="background:#fee2e2;border-radius:6px;padding:8px;text-align:center;'
                f'color:#991b1b;font-weight:700;font-size:0.8rem;margin-top:8px;">'
                f'⚠️ {metrics["overdue"]} OVERDUE</div>',
                unsafe_allow_html=True,
            )

    # ── Section 2: Analyst Workload Grid ─────────────────────────────────────
    st.markdown(render_section_header("SECTION 2", "Analyst Workload Grid"), unsafe_allow_html=True)

    analyst_stats = _get_analyst_stats(df)
    analysts = list(ANALYST_INITIALS.keys())

    row1 = st.columns(3)
    row2 = st.columns(3)
    all_cols = row1 + row2

    for i, analyst in enumerate(analysts):
        present_status = "leave" if analyst == "Sarah Chen" else ("absent" if not ANALYST_PRESENT.get(analyst, True) else "present")
        with all_cols[i]:
            st.markdown(
                _analyst_card_html(analyst, analyst_stats[analyst], present_status),
                unsafe_allow_html=True,
            )
            if st.button(f"Reassign", key=f"reassign_{analyst}", use_container_width=True):
                st.info(f"Reassign workflow: This would open the Q-Flow reassignment queue for {analyst}'s applications.")

    # ── Section 3: Performance Analytics ─────────────────────────────────────
    st.markdown(render_section_header("SECTION 3", "Performance Analytics"), unsafe_allow_html=True)

    chart_col1, chart_col2 = st.columns(2)
    chart_col3, chart_col4 = st.columns(2)

    with chart_col1:
        st.plotly_chart(_sla_trend_chart(df), use_container_width=True)
    with chart_col2:
        st.plotly_chart(_analyst_status_chart(df), use_container_width=True)
    with chart_col3:
        st.plotly_chart(_weekly_heatmap_chart(df), use_container_width=True)
    with chart_col4:
        st.plotly_chart(_funnel_chart(df), use_container_width=True)

    # ── Section 4: Capacity Intelligence ─────────────────────────────────────
    st.markdown(render_section_header("SECTION 4", "Capacity Intelligence (GIS-Powered)"), unsafe_allow_html=True)

    critical_zones = []
    if zone_util_df is not None and not zone_util_df.empty:
        critical_zones = zone_util_df[zone_util_df["status"] == "At Limit"]["plant_name"].tolist()

    if critical_zones:
        names = ", ".join(critical_zones[:3])
        st.markdown(
            f'<div style="background:#fee2e2;border:2px solid #fca5a5;border-radius:8px;'
            f'padding:12px 16px;margin-bottom:12px;font-weight:700;color:#991b1b;font-size:0.9rem;">'
            f'⚠️ SUPERVISOR ACTION REQUIRED — AT-LIMIT ZONES: {names}<br>'
            f'<span style="font-weight:400;font-size:0.82rem;">These zones cannot accept new reservations. '
            f'Review pending applications and coordinate with Engineering for capacity expansion timeline.</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    _render_capacity_table(zone_util_df, proj_df)

    # ── Section 5: Open Records & Special Projects ────────────────────────────
    st.markdown(render_section_header("SECTION 5", "Open Records & Special Projects"), unsafe_allow_html=True)

    orr_df = pd.DataFrame(OPEN_RECORDS)
    status_colors = {
        "In Progress": "background-color: #ede9fe",
        "Pending Review": "background-color: #fef9c3",
        "Completed": "background-color: #d1fae5",
        "Awaiting Response": "background-color: #dbeafe",
    }

    def style_orr(row):
        color = status_colors.get(row["status"], "")
        return [color] * len(row)

    orr_styled = orr_df.style.apply(style_orr, axis=1)
    st.dataframe(orr_df, use_container_width=True, hide_index=True, height=260)

    # ── Section 6: GIMS / GeoLink Sync Status ────────────────────────────────
    st.markdown(render_section_header("SECTION 6", "GIMS / GeoLink Integration Status"), unsafe_allow_html=True)

    now_str = datetime.now().strftime("%m/%d/%Y %I:%M %p")
    np.random.seed(int(datetime.now().strftime("%H")))
    apps_synced = np.random.randint(8, 18)
    queue_depth = np.random.randint(20, 55)

    st.markdown(
        f"""<div style="background:#1e293b;color:#e2e8f0;border-radius:8px;padding:20px;
                font-family:'Courier New',monospace;font-size:0.82rem;line-height:2;">
            <div style="color:#60a5fa;font-weight:700;margin-bottom:12px;font-size:0.9rem;">
                &#9632; GIMS / GeoLink SYNC STATUS PANEL
            </div>
            Last GIMS Data Sync: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <span style="color:#4ade80;">{now_str}</span><br>
            Feature Layers Updated:<br>
            &nbsp;&nbsp;&#9492;&#9472; Wastewater Network: &nbsp; <span style="color:#4ade80;">&#10003; CURRENT</span><br>
            &nbsp;&nbsp;&#9492;&#9472; Water Network: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <span style="color:#4ade80;">&#10003; CURRENT</span><br>
            &nbsp;&nbsp;&#9492;&#9472; Parcel Layer: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <span style="color:#4ade80;">&#10003; CURRENT</span><br>
            &nbsp;&nbsp;&#9492;&#9472; Council Districts: &nbsp;&nbsp;&nbsp; <span style="color:#4ade80;">&#10003; CURRENT</span><br>
            Pending Edits: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <span style="color:#fbbf24;">3 records awaiting QA review</span><br>
            iPermits Integration: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <span style="color:#4ade80;">Active</span> &nbsp;|&nbsp; {apps_synced} applications synced today<br>
            Q-Flow Integration: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <span style="color:#4ade80;">Active</span> &nbsp;|&nbsp; Queue depth: {queue_depth}<br>
            Kronos Workforce Mgmt: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <span style="color:#4ade80;">Active</span> &nbsp;|&nbsp; 5/6 analysts clocked in<br>
            ILMS (Permitting): &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <span style="color:#4ade80;">Active</span> &nbsp;|&nbsp; All pending permits synced<br>
            <div style="border-top:1px solid #334155;margin-top:12px;padding-top:10px;color:#64748b;font-size:0.75rem;">
                Spatial Engine: GeoPandas 0.14+ / Shapely 2.0 / EPSG:2278 &#10003; &nbsp;|&nbsp;
                Next full sync: {(datetime.now() + timedelta(hours=1)).strftime("%I:%M %p")}
            </div>
        </div>""",
        unsafe_allow_html=True,
    )
