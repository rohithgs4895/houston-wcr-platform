"""
GIS layer generation for Houston WCR Intelligence Platform.
Generates treatment plants, city boundary, and council districts as GeoDataFrames.
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point, Polygon, MultiPolygon
import streamlit as st

# CRS constants
DISPLAY_CRS = "EPSG:4326"
HOUSTON_CRS = "EPSG:2278"

TREATMENT_PLANTS = [
    {"id": "TP001", "name": "69th Street WWTP",       "lat": 29.7358, "lon": -95.3774, "capacity_mgd": 75, "online_year": 1958},
    {"id": "TP002", "name": "Almeda Sims WWTP",        "lat": 29.6421, "lon": -95.3512, "capacity_mgd": 30, "online_year": 1972},
    {"id": "TP003", "name": "Beltway WWTP",            "lat": 29.7890, "lon": -95.5234, "capacity_mgd": 12, "online_year": 1985},
    {"id": "TP004", "name": "Brays Bayou WWTP",        "lat": 29.6912, "lon": -95.4123, "capacity_mgd": 18, "online_year": 1969},
    {"id": "TP005", "name": "Clear Lake WWTP",         "lat": 29.5634, "lon": -95.0987, "capacity_mgd": 22, "online_year": 1978},
    {"id": "TP006", "name": "Cottage Grove WWTP",      "lat": 29.7712, "lon": -95.4012, "capacity_mgd":  8, "online_year": 1991},
    {"id": "TP007", "name": "Greens Bayou WWTP",       "lat": 29.8234, "lon": -95.2456, "capacity_mgd": 35, "online_year": 1975},
    {"id": "TP008", "name": "Highlands WWTP",          "lat": 29.8156, "lon": -95.0534, "capacity_mgd": 10, "online_year": 1988},
    {"id": "TP009", "name": "Intercontinental WWTP",   "lat": 29.9512, "lon": -95.3456, "capacity_mgd": 15, "online_year": 1983},
    {"id": "TP010", "name": "Kingwood WWTP",           "lat": 30.0234, "lon": -95.1987, "capacity_mgd": 20, "online_year": 1990},
    {"id": "TP011", "name": "Lufkin Road WWTP",        "lat": 29.8567, "lon": -95.4678, "capacity_mgd": 14, "online_year": 1986},
    {"id": "TP012", "name": "Meyerland WWTP",          "lat": 29.6987, "lon": -95.4567, "capacity_mgd": 25, "online_year": 1971},
    {"id": "TP013", "name": "North Canal WWTP",        "lat": 29.8012, "lon": -95.3234, "capacity_mgd": 40, "online_year": 1965},
    {"id": "TP014", "name": "Ponderosa WWTP",          "lat": 29.9123, "lon": -95.5012, "capacity_mgd": 18, "online_year": 1987},
    {"id": "TP015", "name": "South Post Oak WWTP",     "lat": 29.6234, "lon": -95.4890, "capacity_mgd": 22, "online_year": 1976},
    {"id": "TP016", "name": "Sims Bayou WWTP",         "lat": 29.6678, "lon": -95.3123, "capacity_mgd": 28, "online_year": 1973},
    {"id": "TP017", "name": "Spring Branch WWTP",      "lat": 29.7890, "lon": -95.5456, "capacity_mgd": 16, "online_year": 1982},
    {"id": "TP018", "name": "Westpark WWTP",           "lat": 29.7234, "lon": -95.5678, "capacity_mgd": 20, "online_year": 1979},
    {"id": "TP019", "name": "White Oak WWTP",          "lat": 29.7789, "lon": -95.3890, "capacity_mgd": 12, "online_year": 1993},
    {"id": "TP020", "name": "Willow Waterhole WWTP",   "lat": 29.6456, "lon": -95.5123, "capacity_mgd": 18, "online_year": 1989},
]

# Approximate Houston city boundary (simplified polygon with real corner coordinates)
HOUSTON_BOUNDARY_COORDS = [
    (-95.789, 29.924), (-95.720, 29.910), (-95.680, 29.870),
    (-95.650, 29.820), (-95.630, 29.780), (-95.640, 29.740),
    (-95.620, 29.700), (-95.600, 29.660), (-95.580, 29.620),
    (-95.530, 29.580), (-95.480, 29.560), (-95.420, 29.555),
    (-95.350, 29.560), (-95.280, 29.580), (-95.200, 29.600),
    (-95.140, 29.630), (-95.090, 29.670), (-95.069, 29.720),
    (-95.069, 29.800), (-95.080, 29.870), (-95.100, 29.940),
    (-95.130, 30.000), (-95.180, 30.060), (-95.240, 30.100),
    (-95.300, 30.117), (-95.380, 30.120), (-95.450, 30.110),
    (-95.520, 30.090), (-95.580, 30.060), (-95.640, 30.020),
    (-95.700, 29.990), (-95.750, 29.970), (-95.789, 29.924),
]

# Council district approximate boundaries
COUNCIL_DISTRICTS = {
    "A": {  # Heights / NW Houston
        "label": "District A — Heights/NW",
        "coords": [(-95.450, 29.800), (-95.380, 29.800), (-95.380, 29.860),
                   (-95.450, 29.860), (-95.450, 29.800)],
    },
    "B": {  # NE Houston
        "label": "District B — Northeast",
        "coords": [(-95.310, 29.790), (-95.200, 29.790), (-95.200, 29.880),
                   (-95.310, 29.880), (-95.310, 29.790)],
    },
    "C": {  # Midtown / Montrose
        "label": "District C — Midtown/Montrose",
        "coords": [(-95.420, 29.730), (-95.360, 29.730), (-95.360, 29.790),
                   (-95.420, 29.790), (-95.420, 29.730)],
    },
    "D": {  # SE Houston
        "label": "District D — Southeast",
        "coords": [(-95.310, 29.660), (-95.200, 29.660), (-95.200, 29.760),
                   (-95.310, 29.760), (-95.310, 29.660)],
    },
    "E": {  # Far East
        "label": "District E — Far East",
        "coords": [(-95.200, 29.720), (-95.069, 29.720), (-95.069, 29.830),
                   (-95.200, 29.830), (-95.200, 29.720)],
    },
    "F": {  # SW Houston
        "label": "District F — Southwest",
        "coords": [(-95.600, 29.650), (-95.450, 29.650), (-95.450, 29.740),
                   (-95.600, 29.740), (-95.600, 29.650)],
    },
    "G": {  # West Houston
        "label": "District G — West",
        "coords": [(-95.650, 29.740), (-95.500, 29.740), (-95.500, 29.820),
                   (-95.650, 29.820), (-95.650, 29.740)],
    },
    "H": {  # East / Near East
        "label": "District H — East",
        "coords": [(-95.350, 29.740), (-95.250, 29.740), (-95.250, 29.800),
                   (-95.350, 29.800), (-95.350, 29.740)],
    },
    "I": {  # Near North
        "label": "District I — Near North",
        "coords": [(-95.420, 29.800), (-95.340, 29.800), (-95.340, 29.870),
                   (-95.420, 29.870), (-95.420, 29.800)],
    },
    "J": {  # Near SW
        "label": "District J — Near Southwest",
        "coords": [(-95.510, 29.700), (-95.420, 29.700), (-95.420, 29.760),
                   (-95.510, 29.760), (-95.510, 29.700)],
    },
    "K": {  # Far North
        "label": "District K — Far North",
        "coords": [(-95.550, 29.880), (-95.380, 29.880), (-95.380, 29.980),
                   (-95.550, 29.980), (-95.550, 29.880)],
    },
}


@st.cache_data
def get_plants_gdf():
    """Return treatment plants as GeoDataFrame in WGS84."""
    records = []
    for p in TREATMENT_PLANTS:
        r = dict(p)
        r["geometry"] = Point(p["lon"], p["lat"])
        # Service unit capacity: MGD × 1_000_000 gal / 250 gpd per SU
        r["capacity_su"] = int(p["capacity_mgd"] * 1_000_000 / 250)
        records.append(r)

    gdf = gpd.GeoDataFrame(records, crs=DISPLAY_CRS)
    return gdf


@st.cache_data
def get_city_boundary_gdf():
    """Return simplified Houston city boundary as GeoDataFrame."""
    coords_xy = [(lon, lat) for lon, lat in HOUSTON_BOUNDARY_COORDS]
    boundary = Polygon(coords_xy)
    gdf = gpd.GeoDataFrame(
        [{"name": "Houston City Limits", "geometry": boundary}],
        crs=DISPLAY_CRS,
    )
    return gdf


@st.cache_data
def get_council_districts_gdf():
    """Return Houston council districts A–K as GeoDataFrame."""
    records = []
    for district_id, info in COUNCIL_DISTRICTS.items():
        coords_xy = [(lon, lat) for lon, lat in info["coords"]]
        records.append({
            "district": district_id,
            "label": info["label"],
            "geometry": Polygon(coords_xy),
        })
    gdf = gpd.GeoDataFrame(records, crs=DISPLAY_CRS)
    return gdf
