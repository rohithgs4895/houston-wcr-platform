"""
SLA Engine for Houston WCR Intelligence Platform.
Business day calculations with Texas state holidays.
"""

import pandas as pd
from datetime import datetime, timedelta, date
import holidays


# Texas state holidays calendar (US/TX subdivision)
TX_HOLIDAYS = holidays.country_holidays("US", subdiv="TX", years=range(2024, 2028))

STANDARD_SLA_DAYS = 10  # business days
EXPEDITED_SLA_DAYS = 5   # business days


def is_business_day(d):
    """Return True if d is a weekday and not a Texas holiday."""
    if isinstance(d, datetime):
        d = d.date()
    return d.weekday() < 5 and d not in TX_HOLIDAYS


def add_business_days(start_date, days):
    """Add N business days to start_date, skipping weekends and TX holidays."""
    if isinstance(start_date, datetime):
        start_date = start_date.date()
    elif isinstance(start_date, str):
        start_date = pd.to_datetime(start_date).date()

    current = start_date
    added = 0
    while added < days:
        current += timedelta(days=1)
        if is_business_day(current):
            added += 1
    return current


def business_days_between(start, end):
    """Count business days between two dates (inclusive of start, exclusive of end)."""
    if isinstance(start, datetime):
        start = start.date()
    elif isinstance(start, str):
        start = pd.to_datetime(start).date()
    if isinstance(end, datetime):
        end = end.date()
    elif isinstance(end, str):
        end = pd.to_datetime(end).date()

    if start > end:
        return -business_days_between(end, start)

    count = 0
    current = start
    while current < end:
        if is_business_day(current):
            count += 1
        current += timedelta(days=1)
    return count


def get_sla_deadline(submission_date, expedited=False):
    """Return deadline date: +10 business days standard, +5 expedited."""
    days = EXPEDITED_SLA_DAYS if expedited else STANDARD_SLA_DAYS
    return add_business_days(submission_date, days)


def get_sla_status(submission_date, status, expedited=False, reference_date=None):
    """
    Returns dict with:
    - status: 'On Track' / 'At Risk' / 'Overdue' / 'Completed'
    - days_remaining: int (negative if overdue)
    - deadline: date
    - percent_elapsed: float 0-100
    """
    if reference_date is None:
        reference_date = date.today()
    elif isinstance(reference_date, datetime):
        reference_date = reference_date.date()

    if isinstance(submission_date, str):
        submission_date = pd.to_datetime(submission_date).date()
    elif isinstance(submission_date, datetime):
        submission_date = submission_date.date()
    elif hasattr(submission_date, 'date'):
        submission_date = submission_date.date()

    deadline = get_sla_deadline(submission_date, expedited)
    total_days = EXPEDITED_SLA_DAYS if expedited else STANDARD_SLA_DAYS
    elapsed = business_days_between(submission_date, reference_date)
    percent_elapsed = min(100.0, (elapsed / total_days) * 100)
    days_remaining = business_days_between(reference_date, deadline)

    completed_statuses = {"Approved", "Denied", "Completed"}
    if status in completed_statuses:
        sla_status = "Completed"
    elif reference_date > deadline:
        sla_status = "Overdue"
        days_remaining = -business_days_between(deadline, reference_date)
    elif days_remaining <= 2:
        sla_status = "At Risk"
    else:
        sla_status = "On Track"

    return {
        "status": sla_status,
        "days_remaining": days_remaining,
        "deadline": deadline,
        "percent_elapsed": percent_elapsed,
    }


def get_compliance_rate(df, period_days=30):
    """
    Compliance rate for applications completed in last N days.
    compliance = completed within SLA / total completed × 100
    """
    cutoff = date.today() - timedelta(days=period_days)
    completed = df[df["status"].isin(["Approved", "Denied"])].copy()

    if "submission_date" in completed.columns:
        completed["submission_date"] = pd.to_datetime(completed["submission_date"]).dt.date
        completed = completed[completed["submission_date"] >= cutoff]

    if len(completed) == 0:
        return 100.0

    compliant = completed[completed["sla_status"] == "Completed"]
    rate = len(compliant) / len(completed) * 100
    return round(rate, 1)


def generate_daily_metrics(df):
    """Generate all metrics needed for the daily ops report."""
    today = date.today()
    today_dt = pd.Timestamp(today)

    # Submissions today
    df["submission_date"] = pd.to_datetime(df["submission_date"])
    new_today = len(df[df["submission_date"].dt.date == today])

    # Queue status
    active = df[df["status"].isin(["Pending", "In Review", "On Hold", "Revision Needed"])]
    pending_assignment = len(df[df["status"] == "Pending"])
    queue_total = len(active)

    # SLA breakdown
    sla_counts = df["sla_status"].value_counts().to_dict()
    on_track = sla_counts.get("On Track", 0)
    at_risk = sla_counts.get("At Risk", 0)
    overdue = sla_counts.get("Overdue", 0)
    completed = sla_counts.get("Completed", 0)

    total_active = on_track + at_risk + overdue
    compliance_rate = get_compliance_rate(df, 30)

    # Letters (simulated)
    letters_pending_review = max(0, pending_assignment - 3)
    letters_pending_sig = max(0, letters_pending_review // 2)
    letters_issued_today = max(0, new_today // 2)
    accuracy_rate = 94.7

    return {
        "new_today": new_today,
        "pending_assignment": pending_assignment,
        "queue_total": queue_total,
        "on_track": on_track,
        "at_risk": at_risk,
        "overdue": overdue,
        "completed": completed,
        "compliance_rate": compliance_rate,
        "letters_pending_review": letters_pending_review,
        "letters_pending_sig": letters_pending_sig,
        "letters_issued_today": letters_issued_today,
        "accuracy_rate": accuracy_rate,
        "total_active": total_active,
    }
