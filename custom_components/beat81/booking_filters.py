"""Shared filters for ticket rows from the Beat81 API."""

from __future__ import annotations

from typing import Any


def booking_status_name(booking: dict[str, Any]) -> str:
    return str((booking.get("current_status") or {}).get("status_name") or "unknown")


def is_cancelled_booking(booking: dict[str, Any]) -> bool:
    return booking_status_name(booking).lower() == "cancelled"


def without_cancelled(bookings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tickets the user can still act on (promote, attend, etc.)."""
    return [b for b in bookings if not is_cancelled_booking(b)]
