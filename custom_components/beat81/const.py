"""Constants for Beat81 integration."""

from collections.abc import Mapping
from datetime import timedelta
from typing import Any

DOMAIN = "beat81"

CONF_TOKEN = "token"
CONF_USER_ID = "user_id"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_SCAN_INTERVAL_MINUTES = "scan_interval_minutes"
CONF_SCAN_INTERVAL_SECONDS = "scan_interval_seconds"
CONF_SCAN_INTERVAL_WAITLIST_SECONDS = "scan_interval_waitlist_seconds"
CONF_SCAN_INTERVAL_IDLE_SECONDS = "scan_interval_idle_seconds"
CONF_AUTO_PROMOTE = "auto_promote"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=15)
DEFAULT_SCAN_INTERVAL_MINUTES = 15

# When at least one ticket is waitlisted vs none — dynamic polling
DEFAULT_WAITLIST_POLL_SECONDS = 5
DEFAULT_IDLE_POLL_SECONDS = 1800  # 30 minutes

WAITLIST_POLL_CHOICES: tuple[int, ...] = (
    5,
    10,
    15,
    30,
    45,
    60,
    90,
    120,
    180,
    300,
)

IDLE_POLL_CHOICES: tuple[int, ...] = (
    60,
    120,
    180,
    300,
    600,
    900,
    1800,
    3600,
)

# Legacy single-interval UI (v1.4.x); migration only
SCAN_INTERVAL_CHOICES: tuple[int, ...] = (
    5,
    10,
    15,
    30,
    45,
    60,
    90,
    120,
    180,
    300,
    600,
    900,
    1800,
    3600,
)


def snap_waitlist_seconds(seconds: int) -> int:
    if seconds in WAITLIST_POLL_CHOICES:
        return seconds
    return min(WAITLIST_POLL_CHOICES, key=lambda x: abs(x - seconds))


def snap_idle_seconds(seconds: int) -> int:
    if seconds in IDLE_POLL_CHOICES:
        return seconds
    return min(IDLE_POLL_CHOICES, key=lambda x: abs(x - seconds))


def snap_scan_interval_seconds(seconds: int) -> int:
    """Legacy single-interval snap (migration)."""
    if seconds in SCAN_INTERVAL_CHOICES:
        return seconds
    return min(SCAN_INTERVAL_CHOICES, key=lambda x: abs(x - seconds))


def dual_poll_intervals(options: Mapping[str, Any]) -> tuple[timedelta, timedelta]:
    """Fast interval when waitlist_count > 0, slow when not. Migrates legacy options."""
    w = options.get(CONF_SCAN_INTERVAL_WAITLIST_SECONDS)
    i = options.get(CONF_SCAN_INTERVAL_IDLE_SECONDS)
    if w is not None and i is not None:
        return (
            timedelta(seconds=max(5, int(w))),
            timedelta(seconds=max(60, int(i))),
        )
    if (legacy := options.get(CONF_SCAN_INTERVAL_SECONDS)) is not None:
        idle_s = snap_idle_seconds(max(60, int(legacy)))
        return timedelta(seconds=DEFAULT_WAITLIST_POLL_SECONDS), timedelta(seconds=idle_s)
    minutes = max(1, int(options.get(CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES)))
    idle_s = snap_idle_seconds(max(60, minutes * 60))
    return timedelta(seconds=DEFAULT_WAITLIST_POLL_SECONDS), timedelta(seconds=idle_s)


BOOKING_URL = "https://api.production.b81.io/api/tickets"

# Wider window + limit so calendars can show recent past and cancelled sessions.
BOOKINGS_API_PAST_DAYS = 14
BOOKINGS_API_LIMIT = 500

ATTR_BOOKINGS = "bookings"
ATTR_WAITLIST = "waitlist"
ATTR_BOOKED_COUNT = "booked_count"
ATTR_WAITLIST_COUNT = "waitlist_count"
ATTR_TOKEN_EXPIRES = "token_expires_iso"
ATTR_LAST_ERROR = "last_error"
ATTR_POLL_TIER = "poll_tier"
ATTR_NEXT_POLL_INTERVAL_SECONDS = "next_poll_interval_seconds"
ATTR_CONFIGURED_WAITLIST_POLL_SECONDS = "configured_waitlist_poll_seconds"
ATTR_CONFIGURED_IDLE_POLL_SECONDS = "configured_idle_poll_seconds"
ATTR_POLLING_SUMMARY = "polling"

SERVICE_PROMOTE_WAITLIST = "promote_waitlist"
