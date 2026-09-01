"""Pure date arithmetic for chore recurrence. No database access.

Config shapes
-------------
fixed, weekly:   {"freq": "weekly", "weekdays": [0, 3]}   # Mon=0 .. Sun=6
fixed, monthly:  {"freq": "monthly", "day": 15}           # 1..31, clamped
interval:        {"days": 3}
"""

from calendar import monthrange
from datetime import date, timedelta

FIXED = "fixed"
INTERVAL = "interval"


def _clamp_day(year, month, day):
    last = monthrange(year, month)[1]
    return date(year, month, min(day, last))


def _next_weekly(weekdays, after):
    if not weekdays:
        return None
    d = after + timedelta(days=1)
    for _ in range(14):
        if d.weekday() in weekdays:
            return d
        d += timedelta(days=1)
    return None


def _next_monthly(day, after):
    candidate = _clamp_day(after.year, after.month, day)
    if candidate <= after:
        year = after.year + (1 if after.month == 12 else 0)
        month = 1 if after.month == 12 else after.month + 1
        candidate = _clamp_day(year, month, day)
    return candidate


def next_fixed(config, after):
    """First date matching a fixed schedule strictly after ``after``."""
    if config.get("freq") == "weekly":
        return _next_weekly(config.get("weekdays", []), after)
    if config.get("freq") == "monthly":
        return _next_monthly(int(config["day"]), after)
    return None


def next_interval(config, completed_on):
    """``completed_on`` plus N days."""
    return completed_on + timedelta(days=int(config["days"]))


def next_due_after(recurrence_type, config, completed_on):
    """Next due date after a chore was completed on ``completed_on``."""
    if recurrence_type == FIXED:
        return next_fixed(config, completed_on)
    if recurrence_type == INTERVAL:
        return next_interval(config, completed_on)
    return None


def compute_initial_due(recurrence_type, config, today):
    """Due date for a freshly created chore that has never been completed."""
    if recurrence_type == FIXED:
        # first matching date on or after today
        return next_fixed(config, today - timedelta(days=1))
    if recurrence_type == INTERVAL:
        return today
    return None
