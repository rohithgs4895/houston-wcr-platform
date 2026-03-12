"""
Styling utilities for the Houston WCR Intelligence Platform.
Color palette, CSS, and HTML helpers.
"""

COLORS = {
    "houston_blue": "#003087",
    "houston_red": "#E31837",
    "accent_blue": "#0072CE",
    "available": "#27ae60",
    "near_limit": "#f39c12",
    "at_limit": "#e74c3c",
    "on_track": "#2ecc71",
    "at_risk": "#f1c40f",
    "overdue": "#e74c3c",
    "bg": "#f0f2f6",
    "card_bg": "#ffffff",
    "border": "#dee2e6",
    "text": "#2c3e50",
    "text_light": "#7f8c8d",
}

STATUS_COLORS = {
    "Pending": "#3498db",
    "In Review": "#9b59b6",
    "Approved": "#27ae60",
    "Denied": "#e74c3c",
    "Revision Needed": "#e67e22",
    "On Hold": "#95a5a6",
}

SLA_COLORS = {
    "On Track": "#2ecc71",
    "At Risk": "#f1c40f",
    "Overdue": "#e74c3c",
    "Completed": "#3498db",
}

CAPACITY_COLORS = {
    "Available": "#27ae60",
    "Near Limit": "#f39c12",
    "At Limit": "#e74c3c",
}


def get_main_css():
    return f"""
    <style>
        /* ── Global ─────────────────────────────────────────── */
        .stApp {{
            background-color: {COLORS['bg']};
        }}

        /* ── Header bar ─────────────────────────────────────── */
        .wcr-header {{
            background: {COLORS['houston_blue']};
            padding: 16px 24px 12px 24px;
            border-bottom: 4px solid {COLORS['houston_red']};
            margin: -1rem -1rem 1.5rem -1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .wcr-header-title {{
            color: white;
            font-size: 1.4rem;
            font-weight: 700;
            letter-spacing: 0.5px;
            margin: 0;
        }}
        .wcr-header-sub {{
            color: #a8c4e8;
            font-size: 0.78rem;
            margin: 2px 0 0 0;
        }}
        .wcr-header-badge {{
            background: {COLORS['houston_red']};
            color: white;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 1px;
        }}

        /* ── Metric cards ────────────────────────────────────── */
        .metric-card {{
            background: {COLORS['card_bg']};
            border-radius: 10px;
            padding: 16px 18px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.07);
            border-left: 5px solid {COLORS['accent_blue']};
            margin-bottom: 12px;
        }}
        .metric-card.green  {{ border-left-color: {COLORS['available']}; }}
        .metric-card.amber  {{ border-left-color: {COLORS['near_limit']}; }}
        .metric-card.red    {{ border-left-color: {COLORS['at_limit']}; }}
        .metric-card.blue   {{ border-left-color: {COLORS['accent_blue']}; }}
        .metric-card.purple {{ border-left-color: #9b59b6; }}

        .metric-label {{
            font-size: 0.72rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: {COLORS['text_light']};
            margin-bottom: 4px;
        }}
        .metric-value {{
            font-size: 1.9rem;
            font-weight: 800;
            color: {COLORS['text']};
            line-height: 1;
        }}
        .metric-delta {{
            font-size: 0.78rem;
            color: {COLORS['text_light']};
            margin-top: 4px;
        }}
        .metric-delta.up   {{ color: {COLORS['available']}; }}
        .metric-delta.down {{ color: {COLORS['at_limit']}; }}

        /* ── Section headers ─────────────────────────────────── */
        .section-header {{
            display: flex;
            align-items: center;
            margin: 1.5rem 0 0.8rem 0;
            gap: 10px;
        }}
        .section-header-bar {{
            width: 5px;
            height: 28px;
            background: {COLORS['houston_blue']};
            border-radius: 3px;
            flex-shrink: 0;
        }}
        .section-header-text {{
            font-size: 1.05rem;
            font-weight: 700;
            color: {COLORS['text']};
        }}
        .section-header-label {{
            font-size: 0.65rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: {COLORS['text_light']};
            margin-bottom: 1px;
        }}

        /* ── Status badges ───────────────────────────────────── */
        .badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.3px;
        }}
        .badge-pending   {{ background: #dbeafe; color: #1e40af; }}
        .badge-review    {{ background: #ede9fe; color: #6d28d9; }}
        .badge-approved  {{ background: #d1fae5; color: #065f46; }}
        .badge-denied    {{ background: #fee2e2; color: #991b1b; }}
        .badge-revision  {{ background: #ffedd5; color: #9a3412; }}
        .badge-ontrack   {{ background: #d1fae5; color: #065f46; }}
        .badge-atrisk    {{ background: #fef9c3; color: #713f12; }}
        .badge-overdue   {{ background: #fee2e2; color: #991b1b; }}
        .badge-hold      {{ background: #f3f4f6; color: #374151; }}

        /* ── Analyst card ────────────────────────────────────── */
        .analyst-card {{
            background: {COLORS['card_bg']};
            border-radius: 12px;
            padding: 18px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.07);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
            height: 100%;
            border: 1px solid {COLORS['border']};
        }}
        .analyst-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.12);
        }}
        .analyst-avatar {{
            width: 48px;
            height: 48px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1rem;
            font-weight: 800;
            color: white;
            margin-bottom: 10px;
        }}
        .workload-bar-bg {{
            background: #e5e7eb;
            border-radius: 4px;
            height: 8px;
            margin: 8px 0;
            overflow: hidden;
        }}
        .workload-bar-fill {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }}

        /* ── Ops report card ─────────────────────────────────── */
        .ops-report {{
            background: {COLORS['card_bg']};
            border: 2px solid {COLORS['houston_blue']};
            border-radius: 8px;
            padding: 24px;
            font-family: 'Courier New', monospace;
            font-size: 0.85rem;
            line-height: 1.8;
            box-shadow: 0 4px 12px rgba(0,48,135,0.1);
        }}
        .ops-report-header {{
            color: {COLORS['houston_blue']};
            font-weight: bold;
            font-size: 1rem;
            border-bottom: 1px solid {COLORS['border']};
            padding-bottom: 8px;
            margin-bottom: 12px;
        }}
        .ops-section-title {{
            color: {COLORS['houston_blue']};
            font-weight: bold;
            margin-top: 12px;
        }}

        /* ── System status bar ───────────────────────────────── */
        .system-status-bar {{
            background: #1e293b;
            color: #94a3b8;
            padding: 6px 16px;
            border-radius: 6px;
            font-size: 0.72rem;
            font-family: monospace;
            margin-bottom: 16px;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}
        .status-dot-green  {{ color: #4ade80; }}
        .status-dot-red    {{ color: #f87171; }}
        .status-dot-yellow {{ color: #fbbf24; }}

        /* ── SLA progress bar ────────────────────────────────── */
        .sla-bar-container {{
            background: #e5e7eb;
            border-radius: 6px;
            height: 12px;
            position: relative;
            overflow: hidden;
        }}
        .sla-bar-fill {{
            height: 100%;
            border-radius: 6px;
            transition: width 0.4s ease;
        }}

        /* ── Table rows ──────────────────────────────────────── */
        .dataframe tbody tr:nth-of-type(odd)  {{ background: #ffffff; }}
        .dataframe tbody tr:nth-of-type(even) {{ background: #f8f9fa; }}
        .dataframe tbody tr:hover {{ background: #e8f4f8 !important; }}

        /* ── Sidebar permanently visible ─────────────────────── */
        section[data-testid="stSidebar"] {{
            display: block !important;
            visibility: visible !important;
            transform: none !important;
            min-width: 300px !important;
            max-width: 300px !important;
            position: relative !important;
        }}

        section[data-testid="stSidebar"] > div {{
            min-width: 300px !important;
        }}

        [data-testid="collapsedControl"] {{
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            pointer-events: none !important;
        }}

        /* ── Sidebar background & readable text ──────────────── */
        [data-testid="stSidebar"] {{
            background-color: #f0f4f8 !important;
        }}
        [data-testid="stSidebar"] .sidebar-section-divider {{
            height: 1px;
            background: {COLORS['border']};
            margin: 12px 0;
        }}
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] div,
        [data-testid="stSidebar"] .stRadio label,
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] small,
        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stMultiSelect label {{
            color: #1a1a1a !important;
            font-weight: 500 !important;
        }}
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] h4 {{
            color: #003087 !important;
            font-weight: 700 !important;
        }}

        /* ── Sidebar filter widget text ──────────────────────── */
        [data-testid="stSidebar"] .stMultiSelect span,
        [data-testid="stSidebar"] .stMultiSelect div,
        [data-testid="stSidebar"] [data-baseweb="select"] span,
        [data-testid="stSidebar"] [data-baseweb="tag"] span {{
            color: #1a1a1a !important;
            background-color: #e8f0fe !important;
        }}
        [data-testid="stSidebar"] .stDateInput label,
        [data-testid="stSidebar"] .stDateInput input {{
            color: #1a1a1a !important;
        }}

        /* ── Alert / warning boxes ───────────────────────────── */
        .alert-box {{
            padding: 12px 16px;
            border-radius: 8px;
            margin: 8px 0;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 0.88rem;
            font-weight: 600;
        }}
        .alert-critical {{
            background: #fee2e2;
            border: 1px solid #fca5a5;
            color: #991b1b;
        }}
        .alert-warning {{
            background: #fef9c3;
            border: 1px solid #fde68a;
            color: #713f12;
        }}
        .alert-info {{
            background: #dbeafe;
            border: 1px solid #93c5fd;
            color: #1e40af;
        }}
        .alert-success {{
            background: #d1fae5;
            border: 1px solid #6ee7b7;
            color: #065f46;
        }}

        /* ── Footer ──────────────────────────────────────────── */
        .wcr-footer {{
            text-align: center;
            color: {COLORS['text_light']};
            font-size: 0.72rem;
            padding: 16px 0 8px 0;
            border-top: 1px solid {COLORS['border']};
            margin-top: 2rem;
        }}

        /* Hide streamlit default header/footer */
        #MainMenu, footer {{ visibility: hidden; }}
        header[data-testid="stHeader"] {{ display: none; }}

        /* ── Targeted dark text (light backgrounds only) ─────── */
        .main .block-container p,
        .main .block-container span,
        .main .block-container label,
        .main .block-container div:not([style*="background"]) {{
            color: #1a1a1a !important;
        }}

        [data-testid="stMetricLabel"] p {{
            color: #444444 !important;
        }}

        [data-testid="stMetricValue"] {{
            color: #003087 !important;
            font-weight: 700 !important;
        }}

        h1, h2, h3, h4, h5, h6 {{
            color: #003087 !important;
        }}

        [data-testid="stDataFrame"] * {{
            color: #1a1a1a !important;
        }}

        [data-testid="stCaptionContainer"] {{
            color: #444444 !important;
        }}

        .stRadio label, .stCheckbox label, .stSelectbox label {{
            color: #1a1a1a !important;
            font-weight: 500 !important;
        }}

        .stTabs [data-baseweb="tab"] {{
            color: #003087 !important;
            font-weight: 600 !important;
        }}

        /* White text on dark Houston blue backgrounds */
        [style*="background:#003087"] *,
        [style*="background: #003087"] *,
        [style*="background-color:#003087"] *,
        [style*="background-color: #003087"] * {{
            color: #ffffff !important;
        }}
    </style>
    """


def render_header():
    return """
    <div class="wcr-header">
        <div>
            <div class="wcr-header-title">&#127961;&#65039; HOUSTON WATER &nbsp;|&nbsp; WCR INTELLIGENCE PLATFORM</div>
            <div class="wcr-header-sub">Infrastructure &amp; Development Services &nbsp;&bull;&nbsp; Impact Fee Administration</div>
        </div>
        <div class="wcr-header-badge">BETA v1.0</div>
    </div>
    """


def render_section_header(label, title):
    return f"""
    <div class="section-header">
        <div class="section-header-bar"></div>
        <div>
            <div class="section-header-label">{label}</div>
            <div class="section-header-text">{title}</div>
        </div>
    </div>
    """


def render_metric_card(label, value, delta=None, delta_dir=None, color="blue"):
    delta_html = ""
    if delta:
        cls = f"metric-delta {delta_dir}" if delta_dir else "metric-delta"
        delta_html = f'<div class="{cls}">{delta}</div>'
    return f"""
    <div class="metric-card {color}">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>
    """


def render_badge(text, status_type):
    cls_map = {
        "Pending": "badge-pending",
        "In Review": "badge-review",
        "Approved": "badge-approved",
        "Denied": "badge-denied",
        "Revision Needed": "badge-revision",
        "On Hold": "badge-hold",
        "On Track": "badge-ontrack",
        "At Risk": "badge-atrisk",
        "Overdue": "badge-overdue",
        "Completed": "badge-approved",
    }
    cls = cls_map.get(status_type, "badge-hold")
    return f'<span class="badge {cls}">{text}</span>'


def render_system_status_bar(last_sync=None):
    if last_sync is None:
        from datetime import datetime
        import pytz
        last_sync = datetime.now(pytz.timezone("America/Chicago")).strftime("%m/%d/%Y %I:%M %p CT")
    return f"""
    <div class="system-status-bar">
        <span><span class="status-dot-green">&#9679;</span> Q-Flow: Connected</span>
        <span><span class="status-dot-green">&#9679;</span> ILMS: Connected</span>
        <span><span class="status-dot-green">&#9679;</span> GIMS/GeoLink: Connected</span>
        <span><span class="status-dot-green">&#9679;</span> Kronos: Connected</span>
        <span>Last Sync: {last_sync}</span>
    </div>
    """


def render_alert(message, level="info"):
    icons = {"critical": "&#10060;", "warning": "&#9888;&#65039;", "info": "&#8505;&#65039;", "success": "&#9989;"}
    icon = icons.get(level, "&#8505;&#65039;")
    return f'<div class="alert-box alert-{level}">{icon} {message}</div>'


def render_footer():
    return """
    <div class="wcr-footer">
        Houston WCR Intelligence Platform &nbsp;|&nbsp;
        Built on City of Houston Open Data + Simulated Records &nbsp;|&nbsp;
        Spatial analysis: GeoPandas/Shapely (EPSG:2278) &nbsp;|&nbsp;
        Visualization: Folium + Plotly
    </div>
    """
