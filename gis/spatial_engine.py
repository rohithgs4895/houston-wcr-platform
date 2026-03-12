"""
Core GIS operations for the Houston WCR Intelligence Platform.

Spatial operations:
  - Voronoi service zone derivation
  - Spatial join: applications → zones
  - Buffer analysis: 0.5-mile capacity alert zones
  - Kernel density / hotspot analysis
  - Nearest plant distance calculation
  - Council district aggregation

Coordinate systems:
  - EPSG:2278  Texas State Plane South Central (US feet) — distance/area calculations
  - EPSG:4326  WGS84 — display and storage
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point, Polygon, MultiPolygon, box
from shapely.ops import unary_union, voronoi_diagram
import warnings
import streamlit as st

# CRS constants
HOUSTON_CRS = "EPSG:2278"   # Texas State Plane South Central, US feet — accurate distances
DISPLAY_CRS = "EPSG:4326"   # WGS84 — display
HOUSTON_CENTER = (29.7604, -95.3698)
HOUSTON_BBOX = (-95.80, 29.55, -95.07, 30.10)  # (minx, miny, maxx, maxy) in EPSG:4326


@st.cache_data
def build_service_zones(_plants_gdf, _city_boundary_gdf):
    """
    Derive Voronoi-style service area polygons from treatment plant locations.

    Steps:
    1. Collect all plant points in EPSG:4326
    2. Reproject to EPSG:2278 (TX State Plane, feet) for accurate geometry
    3. Build Voronoi diagram: each region = area closer to that plant than any other
    4. Clip zones to Houston city boundary
    5. Reproject back to EPSG:4326 for display

    Returns GeoDataFrame with zone polygons in EPSG:4326.
    """
    try:
        plants = _plants_gdf.copy()
        # Reproject to TX State Plane for accurate Voronoi in projected space
        plants_proj = plants.to_crs(HOUSTON_CRS)

        # Build a large envelope to contain all Voronoi regions
        city_proj = _city_boundary_gdf.to_crs(HOUSTON_CRS)
        city_union = unary_union(city_proj.geometry)

        # Expand envelope for Voronoi completeness
        envelope = city_union.envelope.buffer(50000)  # 50,000 ft buffer

        # Collect plant points as a MultiPoint for voronoi_diagram
        from shapely.geometry import MultiPoint
        plant_points = MultiPoint(list(plants_proj.geometry))

        # Generate Voronoi regions
        voronoi_geoms = voronoi_diagram(plant_points, envelope=envelope)
        voronoi_regions = list(voronoi_geoms.geoms)

        # Match each Voronoi region back to the nearest plant
        zone_records = []
        for region in voronoi_regions:
            # Find which plant this region belongs to (nearest centroid)
            region_centroid = region.centroid
            min_dist = float("inf")
            matched_plant = None
            for _, plant_row in plants_proj.iterrows():
                dist = region_centroid.distance(plant_row.geometry)
                if dist < min_dist:
                    min_dist = dist
                    matched_plant = plant_row

            if matched_plant is not None:
                # Clip to city boundary
                clipped = region.intersection(city_union)
                if not clipped.is_empty:
                    zone_records.append({
                        "plant_id": matched_plant["id"],
                        "plant_name": matched_plant["name"],
                        "capacity_mgd": matched_plant["capacity_mgd"],
                        "capacity_su": matched_plant["capacity_su"],
                        "geometry": clipped,
                    })

        if not zone_records:
            return _fallback_zones(_plants_gdf, _city_boundary_gdf)

        zones_proj = gpd.GeoDataFrame(zone_records, crs=HOUSTON_CRS)

        # Merge duplicate zones for same plant (if Voronoi split one plant's region)
        zones_proj = zones_proj.dissolve(by="plant_id", aggfunc="first").reset_index()

        # Reproject back to WGS84 for display
        zones_gdf = zones_proj.to_crs(DISPLAY_CRS)
        return zones_gdf

    except Exception as e:
        warnings.warn(f"Voronoi zone derivation failed: {e}. Using fallback buffer zones.")
        return _fallback_zones(_plants_gdf, _city_boundary_gdf)


def _fallback_zones(plants_gdf, city_boundary_gdf):
    """Fallback: create buffer zones if Voronoi fails."""
    try:
        plants_proj = plants_gdf.to_crs(HOUSTON_CRS)
        city_proj = city_boundary_gdf.to_crs(HOUSTON_CRS)
        city_union = unary_union(city_proj.geometry)

        records = []
        for _, row in plants_proj.iterrows():
            buf = row.geometry.buffer(35000)  # ~6.6 miles in feet
            clipped = buf.intersection(city_union)
            records.append({
                "plant_id": row["id"],
                "plant_name": row["name"],
                "capacity_mgd": row["capacity_mgd"],
                "capacity_su": row["capacity_su"],
                "geometry": clipped,
            })

        gdf = gpd.GeoDataFrame(records, crs=HOUSTON_CRS).to_crs(DISPLAY_CRS)
        return gdf
    except Exception:
        return gpd.GeoDataFrame(columns=["plant_id", "plant_name", "capacity_mgd", "capacity_su", "geometry"])


def assign_applications_to_zones(applications_df, zones_gdf):
    """
    Spatial join: assign each WCR application to a treatment plant service zone.

    Steps:
    1. Convert application lat/lon to GeoDataFrame (points) in EPSG:4326
    2. Perform spatial join: within predicate
    3. Flag applications outside any zone (outside city limits)

    Returns applications DataFrame with treatment_plant_id, zone assignment.
    """
    try:
        if applications_df.empty or zones_gdf.empty:
            return applications_df

        # Build point GeoDataFrame from application coordinates
        geometry = [Point(row["lon"], row["lat"]) for _, row in applications_df.iterrows()]
        apps_gdf = gpd.GeoDataFrame(applications_df.copy(), geometry=geometry, crs=DISPLAY_CRS)

        # Spatial join: which zone does each application fall in?
        joined = gpd.sjoin(
            apps_gdf,
            zones_gdf[["plant_id", "plant_name", "geometry"]],
            how="left",
            predicate="within",
        )

        # Handle duplicates from overlapping zones (keep first match)
        joined = joined[~joined.index.duplicated(keep="first")]

        # Fill unmatched applications
        joined["plant_id"] = joined.get("plant_id", joined.get("plant_id_right", None))
        joined["outside_city"] = joined["plant_id"].isna()

        # Drop geometry columns added by sjoin
        result = joined.drop(columns=["geometry", "index_right"], errors="ignore")
        return pd.DataFrame(result)

    except Exception as e:
        warnings.warn(f"Spatial join failed: {e}. Applications not zone-assigned.")
        return applications_df


def buffer_capacity_alert(zones_gdf, applications_df, buffer_feet=2640):
    """
    Identify applications within buffer distance of stressed (At Limit) zones.

    Steps:
    1. Select At-Limit zones
    2. Reproject both layers to EPSG:2278
    3. Buffer at-limit zone boundaries by buffer_feet (default 2640 ft = 0.5 miles)
    4. Find applications whose points fall within buffer
    5. Return set of application IDs flagged as capacity-adjacent risk

    Returns: (buffer_gdf in EPSG:4326, set of flagged application IDs)
    """
    try:
        if zones_gdf.empty or applications_df.empty:
            return gpd.GeoDataFrame(), set()

        # Filter to stressed zones
        if "capacity_status" not in zones_gdf.columns:
            return gpd.GeoDataFrame(), set()

        stressed = zones_gdf[zones_gdf["capacity_status"].isin(["At Limit", "Near Limit"])].copy()
        if stressed.empty:
            return gpd.GeoDataFrame(), set()

        # Reproject to TX State Plane for accurate buffering in feet
        stressed_proj = stressed.to_crs(HOUSTON_CRS)
        stressed_proj["geometry"] = stressed_proj.geometry.buffer(buffer_feet)
        buffer_union = unary_union(stressed_proj.geometry)

        # Convert applications to GeoDataFrame
        geom = [Point(row["lon"], row["lat"]) for _, row in applications_df.iterrows()]
        apps_gdf = gpd.GeoDataFrame(applications_df.copy(), geometry=geom, crs=DISPLAY_CRS)
        apps_proj = apps_gdf.to_crs(HOUSTON_CRS)

        # Find applications within buffer
        flagged_ids = set()
        for idx, app_row in apps_proj.iterrows():
            if buffer_union.contains(app_row.geometry):
                flagged_ids.add(app_row.get("application_id", idx))

        # Return buffer GDF in display CRS
        buffer_gdf = gpd.GeoDataFrame(
            geometry=[buffer_union],
            crs=HOUSTON_CRS,
        ).to_crs(DISPLAY_CRS)

        return buffer_gdf, flagged_ids

    except Exception as e:
        warnings.warn(f"Buffer capacity alert failed: {e}.")
        return gpd.GeoDataFrame(), set()


def calculate_hotspots(applications_df, grid_size=0.02):
    """
    Kernel density estimation: calculate application hotspot intensity.

    Steps:
    1. Extract lat/lon arrays
    2. Build 2D histogram grid over Houston bounding box
    3. Return GeoDataFrame with grid cells and density values for choropleth

    Returns GeoDataFrame with hex-grid polygons and density counts.
    """
    try:
        if applications_df.empty:
            return gpd.GeoDataFrame()

        lons = applications_df["lon"].values
        lats = applications_df["lat"].values

        # Define grid over Houston bbox
        minx, miny, maxx, maxy = HOUSTON_BBOX
        x_edges = np.arange(minx, maxx, grid_size)
        y_edges = np.arange(miny, maxy, grid_size)

        # 2D histogram
        H, xedges, yedges = np.histogram2d(lons, lats, bins=[x_edges, y_edges])

        # Build grid cell polygons
        records = []
        for i in range(len(xedges) - 1):
            for j in range(len(yedges) - 1):
                count = int(H[i, j])
                if count > 0:
                    cell = box(xedges[i], yedges[j], xedges[i + 1], yedges[j + 1])
                    records.append({"density": count, "geometry": cell})

        if not records:
            return gpd.GeoDataFrame()

        hotspot_gdf = gpd.GeoDataFrame(records, crs=DISPLAY_CRS)
        return hotspot_gdf

    except Exception as e:
        warnings.warn(f"Hotspot calculation failed: {e}.")
        return gpd.GeoDataFrame()


def nearest_plant_distance(lat, lon, plants_gdf):
    """
    Calculate distance from a point to all treatment plants.
    Reprojects to EPSG:2278 for accurate distance in feet.

    Returns: (nearest_plant_name, distance_feet)
    """
    try:
        app_point = gpd.GeoDataFrame(
            [{"geometry": Point(lon, lat)}], crs=DISPLAY_CRS
        ).to_crs(HOUSTON_CRS)

        plants_proj = plants_gdf.to_crs(HOUSTON_CRS)
        app_geom = app_point.geometry.iloc[0]

        min_dist = float("inf")
        nearest_name = None
        nearest_id = None

        for _, plant_row in plants_proj.iterrows():
            dist = app_geom.distance(plant_row.geometry)
            if dist < min_dist:
                min_dist = dist
                nearest_name = plant_row["name"]
                nearest_id = plant_row["id"]

        return nearest_name, nearest_id, round(min_dist, 0)

    except Exception:
        return "Unknown", None, 0


def council_district_stats(applications_df, districts_gdf):
    """
    Spatial join applications to council districts, then aggregate statistics.

    Returns district-level summary GeoDataFrame with:
    - count, avg_processing_days, sla_compliance_rate, total_impact_fees
    """
    try:
        if applications_df.empty or districts_gdf.empty:
            return districts_gdf

        geom = [Point(row["lon"], row["lat"]) for _, row in applications_df.iterrows()]
        apps_gdf = gpd.GeoDataFrame(applications_df.copy(), geometry=geom, crs=DISPLAY_CRS)

        joined = gpd.sjoin(
            apps_gdf,
            districts_gdf[["district", "label", "geometry"]],
            how="left",
            predicate="within",
        )

        agg = joined.groupby("district").agg(
            app_count=("application_id", "count"),
            avg_days=("days_open", "mean"),
            total_fees=("total_impact_fee", "sum"),
            overdue_count=("sla_status", lambda x: (x == "Overdue").sum()),
        ).reset_index()

        agg["sla_compliance"] = (
            (agg["app_count"] - agg["overdue_count"]) / agg["app_count"] * 100
        ).round(1)

        result = districts_gdf.merge(agg, on="district", how="left")
        result["app_count"] = result["app_count"].fillna(0).astype(int)
        result["avg_days"] = result["avg_days"].fillna(0).round(1)
        result["total_fees"] = result["total_fees"].fillna(0)
        result["sla_compliance"] = result["sla_compliance"].fillna(100.0)

        return result

    except Exception as e:
        warnings.warn(f"Council district stats failed: {e}.")
        return districts_gdf
