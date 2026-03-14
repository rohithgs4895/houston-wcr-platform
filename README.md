# Houston WCR Intelligence Platform

## 🌐 Live Application
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://houston-wcr-platform-g83787r9csgfcntczhzino.streamlit.app/)

**Live Demo:** https://houston-wcr-platform-g83787r9csgfcntczhzino.streamlit.app/

---

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32%2B-red)
![GeoPandas](https://img.shields.io/badge/GeoPandas-0.14%2B-green)
![Folium](https://img.shields.io/badge/Folium-0.15%2B-darkgreen)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow)

A spatially-intelligent **Wastewater Capacity Reservation (WCR) management platform** built for the City of Houston's Impact Fee Administration team (Houston Public Works / Houston Water division).

---

## Overview

Houston's WCR team manages hundreds of wastewater capacity reservations annually across a city served by 20+ treatment plants. Currently, they work across **four disconnected systems**:

| System | Function |
|--------|----------|
| **Q-Flow** | Queue management and application assignment |
| **GIMS / GeoLink** | GIS, parcel data, utility network layers |
| **ILMS** | Permitting, letter generation, data entry |
| **Kronos** | Workforce scheduling |

**The Problem:** None of these systems talk to each other. Analysts must manually cross-reference applications against capacity maps, check sewer proximity, and track SLA deadlines across spreadsheets. There is no unified spatial view showing which zones are approaching capacity.

**This Platform:** A unified spatial intelligence layer that connects all four systems into a single operational view — adding GIS-powered capacity analysis that doesn't exist in any current tool.

---

## Real-World Context

- Houston operates **20+ WWTPs** with combined capacity exceeding 500 MGD
- 1 Service Unit (SU) = 250 gallons per day (gpd) of wastewater capacity
- WCR applications must be processed within **10 business days** (5 for expedited)
- Impact fees: **$1,662.17/SU** (wastewater) + **$1,658.56/SU** (water) + $150 admin fee
- Applications trigger spatial capacity checks against treatment plant service zones
- Zones approaching 90% utilization require supervisor review before new reservations

---

## Spatial Methodology

### Coordinate Reference Systems

All spatial analysis uses a **two-CRS pipeline**:

```
Input:    EPSG:4326  (WGS84) — geographic coordinates from applications
Analysis: EPSG:2278  (Texas State Plane South Central, US feet) — accurate distances
Display:  EPSG:4326  (WGS84) — Folium/Leaflet rendering
```

EPSG:2278 provides foot-accurate distance measurements across the Houston metro area, which is critical for buffer analysis and nearest-facility calculations.

### Voronoi Service Zone Derivation

Treatment plant service areas are derived using **Voronoi tessellation**:

1. Plant point locations are loaded in EPSG:4326 and reprojected to EPSG:2278
2. `shapely.ops.voronoi_diagram()` generates regions where each point's region = all locations closer to that plant than any other
3. A 50,000-foot envelope ensures region completeness
4. Regions are clipped to the Houston city boundary polygon
5. Each region is matched back to its source plant via centroid proximity
6. Final zones are reprojected to EPSG:4326 for display

**Why Voronoi?** Unlike fixed-radius buffers, Voronoi zones correctly model real service area logic: every location is served by its nearest plant. This produces non-overlapping, exhaustive coverage of the city.

### Spatial Join: Applications → Zones

```python
gpd.sjoin(applications_gdf, zones_gdf, how="left", predicate="within")
```

Each WCR application point is assigned to the zone it falls within. Applications outside all zones are flagged as "outside city limits." The join runs in EPSG:4326 (since zone geometry is display-CRS) and returns the plant ID, zone status, and capacity check result.

### Buffer Analysis: Capacity Alert Zones

For zones with status "At Limit" or "Near Limit":

1. Zone boundary polygons are reprojected to EPSG:2278
2. `.buffer(2640)` creates a 2,640-foot (0.5-mile) buffer ring
3. Application points (also reprojected to EPSG:2278) are tested for containment
4. Applications within the buffer are flagged as "capacity-adjacent risk"
5. Buffer polygons are reprojected to EPSG:4326 for map display as dashed red overlay

### Kernel Density Estimation (Hotspot Analysis)

Application density is calculated using `numpy.histogram2d()`:

1. Application lat/lon coordinates are binned onto a 0.02-degree grid over Houston's bounding box
2. Each grid cell receives a count of applications
3. Non-zero cells are converted to Shapely box polygons
4. The resulting GeoDataFrame drives the density choropleth layer on the map

### Nearest Treatment Plant Distance

```python
# Reproject to EPSG:2278 → calculate Euclidean distances → return in feet
app_proj.distance(plant_proj) → feet
```

Distances are calculated in the projected CRS (feet), not geographic space (degrees), avoiding the distortion that would result from Euclidean distance on lat/lon coordinates.

### Council District Aggregation

A second spatial join assigns each application to a Houston council district polygon (A–K). District-level aggregations include: application count, average processing days, SLA compliance rate, and total impact fees collected.

---

## Features

### Module 1 — Spatial Capacity Map

- **Voronoi service zone choropleth** — zones colored by utilization % (green/amber/orange/red)
- **Treatment plant markers** — sized by capacity (MGD), colored by utilization
- **WCR application heatmap** — urgency-weighted (overdue apps 3×, at-risk 2×)
- **Individual application markers** — colored by status, sized by service units
- **Capacity alert buffers** — 0.5-mile dashed rings around stressed zones
- **Application density grid** — hexagonal KDE overlay
- **Rich popups** — click any zone or marker for detailed capacity and SLA info
- **Sidebar filters** — capacity status, application status, council district, date range
- **Minimap** — bottom-right orientation reference

### Module 2 — WCR Application Tracker

- **Q-Flow system status bar** — simulated live integration status
- **5-card KPI row** — monthly applications, pending assignment, at-risk/overdue, avg days, impact fees
- **Filterable application table** — row colors by SLA status (white/yellow/red)
- **Application detail panel** — full record with SLA countdown bar, impact fee breakdown, status timeline
- **Mini-map** — property location, zone boundary, nearest plant line
- **Bulk actions** — assign, export CSV, generate letters, mark reviewed
- **Impact fee calculator** — real Houston formula with itemized breakdown

### Module 3 — Supervisor Operations Center

- **Daily Ops Report Card** — Kronos staffing, Q-Flow queue, letters, SLA performance
- **Analyst Workload Grid** — 6-card layout with workload bars, compliance rates, reassign buttons
- **SLA Compliance Trend** — 30-day line chart with 90% target line
- **Applications by Analyst** — grouped bar chart (pending/in-review/overdue)
- **Weekly Volume Heatmap** — day-of-week × week heatmap showing workflow patterns
- **Processing Funnel** — submission → assignment → review → letter issued
- **Capacity Intelligence Table** — all 20 zones with utilization, trend, 90-day projection, risk level
- **Open Records Tracker** — ORR, MUD reviews, interagency requests
- **GIMS/GeoLink Sync Status** — system integration panel

---

## Data Sources

| Layer | Source |
|-------|--------|
| WCR Applications | Simulated (250 records, seed=42) based on real Houston WCR process |
| Treatment Plant Locations | City of Houston / Houston Water (real coordinates, public record) |
| City Boundary | Simplified polygon based on real Houston city limits |
| Council Districts | Approximate boundaries based on Houston City Council district geography |
| Impact Fee Schedule | Houston Public Works FY2024 fee schedule |
| Texas Holidays | `holidays` Python library — `holidays.Texas()` |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Web Framework | Streamlit 1.32+ |
| Spatial Analysis | GeoPandas 0.14+, Shapely 2.0+ |
| Projections | PyProj 3.6+ |
| Map Rendering | Folium 0.15+, streamlit-folium |
| Charts | Plotly 5.18+ |
| Data Processing | Pandas 2.0+, NumPy 1.24+ |
| SLA / Holidays | `holidays` 0.45+ (Texas state holidays) |
| Data Generation | Faker 22+, custom generators |

---

## Setup & Run

### Prerequisites

- Python 3.10+
- Conda or venv
- ~500MB disk space (GeoPandas dependencies)

### Installation

```bash
# Create and activate environment
conda create -n wcr_platform python=3.11
conda activate wcr_platform

# Install GDAL first (required by GeoPandas on Windows)
conda install -c conda-forge geopandas

# Install remaining dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

### Alternative (pip only, Linux/Mac)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

### Windows Notes

On Windows, install GeoPandas via conda rather than pip to avoid GDAL compilation issues:

```bash
conda install -c conda-forge geopandas shapely pyproj fiona
```

---

## Project Structure

```
houston_wcr_platform/
├── app.py                        # Main Streamlit entry point
├── requirements.txt
├── README.md
├── data/
│   ├── generate_data.py          # 250 realistic WCR applications (seed=42)
│   └── spatial_data.py           # GIS layers: plants, boundary, districts
├── gis/
│   ├── __init__.py
│   ├── spatial_engine.py         # Voronoi zones, spatial joins, buffers, KDE
│   └── capacity_analysis.py      # Zone utilization, demand projection, fee calc
├── modules/
│   ├── __init__.py
│   ├── capacity_map.py           # Module 1: Folium spatial map
│   ├── wcr_tracker.py            # Module 2: Q-Flow style tracker
│   └── supervisor_dashboard.py   # Module 3: Operations center
├── utils/
│   ├── __init__.py
│   ├── sla_engine.py             # Business day SLA calculations
│   └── styling.py                # CSS, colors, HTML components
└── assets/
    └── methodology.py            # Spatial methodology documentation
```

---

## Screenshots

*Screenshots to be added after deployment.*

---

## Portfolio Note

This platform was built as a portfolio project demonstrating GIS-focused data analysis and spatial software development skills relevant to a Plan Analyst Supervisor role with Houston Public Works.

Every spatial operation in this codebase uses real geospatial logic:
- Voronoi tessellation in a projected CRS (not arbitrary buffers)
- Proper `gpd.sjoin()` with `predicate="within"` (not table joins on district names)
- Buffer analysis in feet via EPSG:2278 (not degree-based approximations)
- KDE using `numpy.histogram2d()` (not point plotting called "density")

The goal was to build something that Houston's team would recognize as understanding their actual workflow — and that adds spatial intelligence they don't currently have.

---

*Houston WCR Intelligence Platform | MIT License | Built with GeoPandas, Shapely, Folium, Streamlit*
