"""Constants for Beat81 integration."""

from datetime import timedelta

DOMAIN = "beat81"

CONF_TOKEN = "token"
CONF_USER_ID = "user_id"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_SCAN_INTERVAL_MINUTES = "scan_interval_minutes"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=15)
DEFAULT_SCAN_INTERVAL_MINUTES = 15

BOOKING_URL = "https://api.production.b81.io/api/tickets"

ATTR_BOOKINGS = "bookings"
ATTR_WAITLIST = "waitlist"
ATTR_BOOKED_COUNT = "booked_count"
ATTR_WAITLIST_COUNT = "waitlist_count"
ATTR_TOKEN_EXPIRES = "token_expires_iso"
ATTR_LAST_ERROR = "last_error"

SERVICE_PROMOTE_WAITLIST = "promote_waitlist"
