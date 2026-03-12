"""
Capacity zone analysis for Houston WCR Intelligence Platform.
Zone utilization, demand projection, and impact fee calculations.
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta
import streamlit as st


# Houston impact fee rates (current schedule)
WASTEWATER_FEE_PER_SU = 1662.17
WATER_FEE_PER_SU = 1658.56
ADMIN_FEE = 150.00
GALLONS_PER_SU = 250  # gallons per day per service unit

# Service unit multipliers by use type
USE_TYPE_MULTIPLIERS = {
    "Single Family Residential": 1.0,
    "Multi-Family Residential": 0.75,
    "Office/Commercial": 0.004,       # per sq ft
    "Restaurant - Full Service": 0.05, # per seat
    "Retail/Shopping Center": 0.003,   # per sq ft
    "Hotel/Motel": 0.5,               # per room
    "Industrial/Warehouse": 0.002,     # per sq ft
}

CAPACITY_THRESHOLDS = {
    "Available": (0, 70),
    "Near Limit": (70, 90),
    "At Limit": (90, 101),
}


def mgd_to_service_units(mgd):
    """Convert plant capacity in MGD to service units."""
    return int(mgd * 1_000_000 / GALLONS_PER_SU)


def calculate_zone_utilization(plants_df, reservations_df):
    """
    For each plant zone:
    - Sum all approved/active WCR service units in that zone
    - Compare to plant design capacity (converted to service units)
    - Calculate utilization % = reserved_SU / total_capacity_SU × 100
    - Return status: Available (<70%), Near Limit (70-89%), At Limit (>=90%)

    Returns DataFrame with plant_id, utilization_pct, status, reserved_su, available_su.
    """
    results = []

    active_statuses = {"Approved", "In Review", "Pending", "On Hold", "Revision Needed"}

    for _, plant in plants_df.iterrows():
        plant_id = plant.get("id", plant.get("plant_id"))
        capacity_su = mgd_to_service_units(plant["capacity_mgd"])

        # Sum service units for active reservations in this zone
        zone_apps = reservations_df[
            (reservations_df.get("treatment_plant_id", pd.Series()) == plant_id) &
            (reservations_df["status"].isin(active_statuses))
        ] if "treatment_plant_id" in reservations_df.columns else pd.DataFrame()

        reserved_su = int(zone_apps["service_units"].sum()) if not zone_apps.empty else 0

        # Add a realistic baseline utilization (existing non-WCR connections)
        # Based on plant age and capacity: older/larger plants are more utilized
        age = date.today().year - plant.get("online_year", 1980)
        base_utilization = min(0.65, 0.3 + (age / 100))
        baseline_su = int(capacity_su * base_utilization)

        total_reserved = reserved_su + baseline_su
        utilization_pct = min(100.0, (total_reserved / capacity_su) * 100) if capacity_su > 0 else 0.0
        available_su = max(0, capacity_su - total_reserved)

        # Determine status
        if utilization_pct >= 90:
            status = "At Limit"
        elif utilization_pct >= 70:
            status = "Near Limit"
        else:
            status = "Available"

        results.append({
            "plant_id": plant_id,
            "plant_name": plant["name"],
            "capacity_mgd": plant["capacity_mgd"],
            "capacity_su": capacity_su,
            "baseline_su": baseline_su,
            "reserved_su": reserved_su,
            "total_reserved_su": total_reserved,
            "available_su": available_su,
            "utilization_pct": round(utilization_pct, 1),
            "status": status,
        })

    return pd.DataFrame(results)


def project_future_demand(applications_df, zone_util_df, months_ahead=6):
    """
    Project utilization X months forward based on:
    - Current pending/in-review applications (certain near-term demand)
    - Historical submission rate (trend-based demand)
    - Returns projection DataFrame with risk flags

    Returns DataFrame with plant_id, projected_utilization, risk_flag.
    """
    results = []

    # Calculate monthly submission rate by zone (last 90 days)
    apps = applications_df.copy()
    apps["submission_date"] = pd.to_datetime(apps["submission_date"])
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=90)
    recent = apps[apps["submission_date"] >= cutoff]

    monthly_rate_by_zone = {}
    if "treatment_plant_id" in recent.columns:
        zone_rates = recent.groupby("treatment_plant_id").agg(
            count=("service_units", "count"),
            total_su=("service_units", "sum"),
        )
        for pid, row in zone_rates.iterrows():
            monthly_rate_by_zone[pid] = row["total_su"] / 3  # per month avg

    for _, zone in zone_util_df.iterrows():
        plant_id = zone["plant_id"]
        capacity_su = zone["capacity_su"]
        current_reserved = zone["total_reserved_su"]

        # Pending applications already in pipeline
        if "treatment_plant_id" in applications_df.columns:
            pending_su = applications_df[
                (applications_df["treatment_plant_id"] == plant_id) &
                (applications_df["status"].isin(["Pending", "In Review"]))
            ]["service_units"].sum()
        else:
            pending_su = 0

        # Trend-based new demand over projection period
        monthly_rate = monthly_rate_by_zone.get(plant_id, 0)
        trend_su = monthly_rate * months_ahead

        projected_reserved = current_reserved + pending_su + trend_su
        projected_pct = min(100.0, (projected_reserved / capacity_su) * 100) if capacity_su > 0 else 0

        will_hit_limit = projected_pct >= 90
        months_to_limit = None
        if not will_hit_limit and monthly_rate > 0:
            remaining_capacity = capacity_su * 0.90 - current_reserved
            if remaining_capacity > 0:
                months_to_limit = remaining_capacity / monthly_rate
            else:
                months_to_limit = 0

        results.append({
            "plant_id": plant_id,
            "plant_name": zone["plant_name"],
            "current_pct": zone["utilization_pct"],
            "projected_pct": round(projected_pct, 1),
            "pending_pipeline_su": int(pending_su),
            "trend_su": int(trend_su),
            "will_hit_limit": will_hit_limit,
            "months_to_limit": round(months_to_limit, 1) if months_to_limit is not None else None,
            "risk_level": "Critical" if projected_pct >= 90 else ("High" if projected_pct >= 80 else ("Medium" if projected_pct >= 70 else "Low")),
        })

    return pd.DataFrame(results)


def impact_fee_calculator(sq_footage=None, num_units=None, num_rooms=None,
                           num_seats=None, use_type="Single Family Residential"):
    """
    Calculate Houston impact fees based on use type and size.

    Real Houston impact fee logic:
    - 1 SU = 250 gallons/day
    - Single family <= 3000 sqft = 1.0 SU
    - Apply use-type multipliers from Houston's actual fee schedule
    - Wastewater: $1,662.17/SU
    - Water: $1,658.56/SU
    - Admin fee: $150.00 flat

    Returns dict with itemized fee breakdown.
    """
    # Calculate service units
    if use_type == "Single Family Residential":
        if sq_footage and sq_footage > 3000:
            # Larger homes get slightly more SUs
            su = 1.0 + (sq_footage - 3000) / 10000
        else:
            su = 1.0
        if num_units:
            su *= num_units
    elif use_type == "Multi-Family Residential":
        su = 0.75 * (num_units or 1)
    elif use_type == "Hotel/Motel":
        su = 0.5 * (num_rooms or 1)
    elif use_type == "Restaurant - Full Service":
        su = 0.05 * (num_seats or 50)
    elif use_type in ("Office/Commercial", "Industrial/Warehouse"):
        su = USE_TYPE_MULTIPLIERS.get(use_type, 0.003) * (sq_footage or 0)
    elif use_type == "Retail/Shopping Center":
        su = 0.003 * (sq_footage or 0)
    else:
        su = 1.0

    su = max(0.5, round(su, 2))  # minimum 0.5 SU

    wastewater_fee = round(su * WASTEWATER_FEE_PER_SU, 2)
    water_fee = round(su * WATER_FEE_PER_SU, 2)
    total_fee = round(wastewater_fee + water_fee + ADMIN_FEE, 2)

    return {
        "service_units": su,
        "wastewater_fee": wastewater_fee,
        "water_fee": water_fee,
        "admin_fee": ADMIN_FEE,
        "total_fee": total_fee,
        "gpd": round(su * GALLONS_PER_SU, 0),
    }


def get_utilization_color(pct):
    """Return hex color for utilization percentage."""
    if pct >= 90:
        return "#e74c3c"
    elif pct >= 75:
        return "#e67e22"
    elif pct >= 60:
        return "#f39c12"
    else:
        return "#2ecc71"


def get_trend_arrow(current, projected):
    """Return trend arrow string based on current vs projected utilization."""
    delta = projected - current
    if delta > 5:
        return "↑"
    elif delta < -2:
        return "↓"
    else:
        return "→"
