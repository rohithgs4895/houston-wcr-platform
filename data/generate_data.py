"""
Generate realistic WCR application data for Houston WCR Intelligence Platform.
250 applications with full spatial coordinates, realistic Houston addresses,
proper impact fee calculations, and Q-Flow/ILMS system references.
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
import random
import streamlit as st

from utils.sla_engine import get_sla_deadline, get_sla_status, add_business_days
from gis.capacity_analysis import impact_fee_calculator

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# ── Houston addresses ────────────────────────────────────────────────────────
STREETS = [
    "Main St", "Westheimer Rd", "Bellaire Blvd", "Kirby Dr", "Richmond Ave",
    "Holcombe Blvd", "Fannin St", "Travis St", "Washington Ave", "Shepherd Dr",
    "Montrose Blvd", "Yale St", "Heights Blvd", "TC Jester Blvd", "Gessner Rd",
    "Fondren Rd", "Bissonnet St", "Southwest Fwy", "Westpark Dr", "Beechnut St",
    "Post Oak Blvd", "Memorial Dr", "San Felipe St", "Briar Forest Dr",
    "Wilcrest Dr", "Eldridge Pkwy", "Voss Rd", "Dairy Ashford Rd",
]

ZIP_CODES = [
    "77002", "77003", "77004", "77005", "77006", "77007", "77008", "77009",
    "77010", "77011", "77019", "77025", "77030", "77036", "77040", "77042",
    "77045", "77056", "77057", "77079", "77080", "77081", "77082", "77084",
    "77090", "77096", "77098",
]

ANALYSTS = [
    "Maria Gonzalez", "James Okafor", "Sarah Chen",
    "David Tran", "Patricia Williams", "Robert Martinez",
]

DEVELOPERS = [
    "Hines Development LLC", "Camden Property Trust", "Midway Companies",
    "Hanover Company", "Greystar Real Estate", "Alliance Residential",
    "Wolff Companies", "Boxer Property", "PM Realty Group",
    "Transwestern Development", "Weingarten Realty", "Lionstone Investments",
    "Patrinely Group", "Coventry Development", "Stonelake Capital",
    "Bridgeland Development", "Trammell Crow Company", "JMB Realty",
    "Novak Brothers Inc", "Gulf Coast Properties LLC",
]

APPLICATION_TYPES = [
    ("New Development", 0.40),
    ("Shopping Center Approval", 0.15),
    ("Name Transfer", 0.20),
    ("Site-to-Site Transfer", 0.10),
    ("Revision Request", 0.10),
    ("Expedited Reservation", 0.05),
]

USE_TYPES = [
    ("Single Family Residential", 0.28),
    ("Multi-Family Residential", 0.25),
    ("Office/Commercial", 0.15),
    ("Restaurant - Full Service", 0.10),
    ("Retail/Shopping Center", 0.10),
    ("Hotel/Motel", 0.07),
    ("Industrial/Warehouse", 0.05),
]

STATUSES = [
    ("Pending", 0.20),
    ("In Review", 0.30),
    ("Approved", 0.30),
    ("Denied", 0.08),
    ("Revision Needed", 0.07),
    ("On Hold", 0.05),
]

COUNCIL_DISTRICTS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"]

TREATMENT_PLANT_IDS = [f"TP{str(i).zfill(3)}" for i in range(1, 21)]

PROCEDURAL_NOTES = [
    "Application received and logged in Q-Flow. Pending initial review.",
    "GIMS parcel lookup completed. Sewer main confirmed within 150 ft.",
    "Capacity check performed against 69th Street zone. Status: Available.",
    "Developer contacted for revised site plan — see ILMS note ILM-2025-0344.",
    "SLA extension granted per supervisor approval. New deadline updated.",
    "Letter issued and recorded in ILMS. Q-Flow ticket closed.",
    "Pending confirmation of acreage from applicant's engineer.",
    "Revision required: incorrect service unit calculation submitted.",
    "Expedited review requested. Supervisor approved 5-day SLA track.",
    "GeoLink parcel verified. Easement confirmed. Proceeding to letter.",
    "On hold pending MUD service area boundary clarification.",
    "Water and wastewater available per GIMS network layer check.",
    "Annual report filed. Reservation active — no action required.",
    "Name transfer verified against HCAD ownership records.",
    "Site-to-site transfer: original reservation ILM-2024-1123 attached.",
    "Accuracy review complete. Letter pending supervisor final signature.",
    "GIMS shows parcel within floodplain overlay — additional review needed.",
    "Impact fee calculated per current fee schedule. Payment pending.",
    "Q-Flow queue ID assigned: expedited queue priority.",
    "Applicant notified of denial — capacity at limit for assigned zone.",
]

# Houston lat/lon bounds for coordinate generation
LAT_BOUNDS = (29.55, 30.05)
LON_BOUNDS = (-95.80, -95.07)


def _weighted_choice(choices):
    """Select from (value, weight) pairs."""
    values, weights = zip(*choices)
    return random.choices(values, weights=weights, k=1)[0]


def _rand_lat():
    return round(random.uniform(*LAT_BOUNDS), 6)


def _rand_lon():
    return round(random.uniform(*LON_BOUNDS), 6)


def _make_address(i):
    number = random.randint(100, 9999)
    street = random.choice(STREETS)
    zip_code = random.choice(ZIP_CODES)
    return f"{number} {street}", f"Houston, TX {zip_code}"


def _calc_service_units(use_type, sq_footage, num_units, num_rooms, num_seats):
    result = impact_fee_calculator(
        sq_footage=sq_footage,
        num_units=num_units,
        num_rooms=num_rooms,
        num_seats=num_seats,
        use_type=use_type,
    )
    return result


@st.cache_data
def generate_applications(n=250):
    """
    Generate n realistic WCR application records.
    Returns a pandas DataFrame with all fields.
    """
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    today = date.today()
    records = []

    for i in range(n):
        app_id = f"WCR-2025-{str(10000 + i).zfill(5)}"

        # Application type and expedited flag
        app_type = _weighted_choice(APPLICATION_TYPES)
        expedited = (app_type == "Expedited Reservation") or (random.random() < 0.06)

        # Use type and sizing
        use_type = _weighted_choice(USE_TYPES)
        sq_footage = None
        num_units = None
        num_rooms = None
        num_seats = None

        if use_type == "Single Family Residential":
            num_units = random.randint(1, 80)
            sq_footage = random.randint(1400, 5500) if num_units == 1 else None
        elif use_type == "Multi-Family Residential":
            num_units = random.randint(24, 400)
        elif use_type in ("Office/Commercial", "Industrial/Warehouse"):
            sq_footage = random.randint(5000, 250000)
        elif use_type == "Retail/Shopping Center":
            sq_footage = random.randint(8000, 180000)
        elif use_type == "Restaurant - Full Service":
            num_seats = random.randint(30, 250)
        elif use_type == "Hotel/Motel":
            num_rooms = random.randint(60, 350)

        fee_calc = _calc_service_units(use_type, sq_footage, num_units, num_rooms, num_seats)
        service_units = fee_calc["service_units"]
        ww_fee = fee_calc["wastewater_fee"]
        w_fee = fee_calc["water_fee"]
        total_fee = fee_calc["total_fee"]

        # Submission date: last 8 months
        days_ago = random.randint(0, 240)
        submission_date = today - timedelta(days=days_ago)

        # Status
        status = _weighted_choice(STATUSES)
        # Older apps more likely to be completed
        if days_ago > 120 and status in ("Pending", "In Review"):
            status = random.choice(["Approved", "Approved", "Denied", "In Review"])

        # SLA
        sla_info = get_sla_status(submission_date, status, expedited)
        sla_status = sla_info["status"]
        sla_deadline = sla_info["deadline"]

        # Processing days
        if status in ("Approved", "Denied"):
            days_to_complete = random.randint(3, 18)
        else:
            days_to_complete = None

        days_open = (today - submission_date).days

        # Location
        lat = _rand_lat()
        lon = _rand_lon()

        # Address
        street_addr, city_state = _make_address(i)
        full_address = f"{street_addr}, {city_state}"

        # Assignment
        analyst = random.choice(ANALYSTS)
        developer = random.choice(DEVELOPERS)

        # Treatment plant (assigned via spatial logic in the app)
        treatment_plant_id = random.choice(TREATMENT_PLANT_IDS)

        # Council district
        council_district = random.choice(COUNCIL_DISTRICTS)

        # Capacity status (will be overridden by spatial join)
        capacity_status = random.choices(
            ["Available", "Near Limit", "At Limit"],
            weights=[0.60, 0.28, 0.12],
        )[0]
        capacity_flag = (capacity_status == "At Limit") or (
            capacity_status == "Near Limit" and random.random() < 0.3
        )

        # System IDs
        q_flow_id = f"QF-{random.randint(1000000, 9999999)}"
        ilms_id = f"ILM-{random.randint(100000, 999999)}"

        # Nearest sewer distance (simulated)
        nearest_sewer_ft = random.randint(30, 2000)

        # Notes
        note = random.choice(PROCEDURAL_NOTES)

        records.append({
            "application_id": app_id,
            "applicant_name": developer,
            "property_address": full_address,
            "lat": lat,
            "lon": lon,
            "development_type": app_type,
            "use_type": use_type,
            "sq_footage": sq_footage,
            "num_units": num_units,
            "num_rooms": num_rooms,
            "num_seats": num_seats,
            "service_units": round(service_units, 2),
            "wastewater_impact_fee": ww_fee,
            "water_impact_fee": w_fee,
            "total_impact_fee": total_fee,
            "submission_date": submission_date,
            "sla_deadline": sla_deadline,
            "expedited": expedited,
            "status": status,
            "assigned_analyst": analyst,
            "treatment_plant_id": treatment_plant_id,
            "council_district": council_district,
            "nearest_sewer_dist_ft": nearest_sewer_ft,
            "capacity_status": capacity_status,
            "capacity_flag": capacity_flag,
            "days_open": days_open,
            "days_to_complete": days_to_complete,
            "sla_status": sla_status,
            "q_flow_queue_id": q_flow_id,
            "ilms_permit_id": ilms_id,
            "notes": note,
        })

    df = pd.DataFrame(records)
    df["submission_date"] = pd.to_datetime(df["submission_date"])
    df["sla_deadline"] = pd.to_datetime(df["sla_deadline"])
    return df
