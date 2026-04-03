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
CONF_AUTO_PROMOTE = "auto_promote"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=15)
DEFAULT_SCAN_INTERVAL_MINUTES = 15
DEFAULT_SCAN_INTERVAL_SECONDS = 900

# UI + stored options; minimum 5s enforced in scan_interval_timedelta
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


def snap_scan_interval_seconds(seconds: int) -> int:
    """Map arbitrary seconds to the nearest configured poll option."""
    if seconds in SCAN_INTERVAL_CHOICES:
        return seconds
    return min(SCAN_INTERVAL_CHOICES, key=lambda x: abs(x - seconds))


def scan_interval_timedelta(options: Mapping[str, Any]) -> timedelta:
    """Build poll interval from config entry options (seconds preferred, legacy minutes)."""
    raw_sec = options.get(CONF_SCAN_INTERVAL_SECONDS)
    if raw_sec is not None:
        sec = max(5, int(raw_sec))
        return timedelta(seconds=sec)
    minutes = max(1, int(options.get(CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES)))
    return timedelta(minutes=minutes)

BOOKING_URL = "https://api.production.b81.io/api/tickets"

ATTR_BOOKINGS = "bookings"
ATTR_WAITLIST = "waitlist"
ATTR_BOOKED_COUNT = "booked_count"
ATTR_WAITLIST_COUNT = "waitlist_count"
ATTR_TOKEN_EXPIRES = "token_expires_iso"
ATTR_LAST_ERROR = "last_error"

SERVICE_PROMOTE_WAITLIST = "promote_waitlist"
