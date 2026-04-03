"""Data update coordinator and waitlist promotion."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import Beat81Client, token_exp_iso
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class Beat81CoordinatorData:
    """Coordinator payload."""

    bookings: list[dict[str, Any]] = field(default_factory=list)
    waitlist_rows: list[dict[str, Any]] = field(default_factory=list)
    booked_count: int = 0
    waitlist_count: int = 0
    promote_messages: list[str] = field(default_factory=list)
    last_promote_ok: bool | None = None
    token_expires_iso: str | None = None


def _parse_event_dt(iso_s: str) -> datetime:
    return datetime.fromisoformat(iso_s.replace("Z", "+00:00"))


def _build_waitlist_rows(bookings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    booked_dates: set[date] = set()
    for b in bookings:
        if b.get("current_status", {}).get("status_name") != "booked":
            continue
        ev = b.get("event") or {}
        db = ev.get("date_begin")
        if not db:
            continue
        booked_dates.add(_parse_event_dt(str(db)).date())

    rows: list[dict[str, Any]] = []
    for booking in bookings:
        if booking.get("current_status", {}).get("status_name") != "waitlisted":
            continue
        ev = booking.get("event") or {}
        db = ev.get("date_begin")
        if not db:
            continue
        booking_date = _parse_event_dt(str(db)).date()
        loc = ev.get("location") or {}
        loc_name = loc.get("name") or "—"
        cur = int(ev.get("current_participants_count") or 0)
        maxp = int(ev.get("max_participants") or 0)
        spots_open = max(0, maxp - cur)
        is_bookable = cur < maxp if maxp else False
        same_day = booking_date in booked_dates
        rows.append(
            {
                "ticket_id": booking.get("id"),
                "date_begin": ev.get("date_begin"),
                "location_name": loc_name,
                "participants_current": cur,
                "participants_max": maxp,
                "spots_open": spots_open,
                "class_has_spot": is_bookable,
                "same_day_blocked": same_day,
                "can_promote_now": is_bookable and not same_day,
            }
        )
    return rows


class Beat81Coordinator(DataUpdateCoordinator[Beat81CoordinatorData]):
    """Poll Beat81 tickets and expose structured data."""

    def __init__(
        self,
        hass,
        client: Beat81Client,
        update_interval: timedelta,
        config_entry: ConfigEntry | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.client = client
        self.config_entry = config_entry

    async def _async_update_data(self) -> Beat81CoordinatorData:
        try:
            bookings = await self.client.async_load_bookings()
        except Exception as err:
            raise UpdateFailed(f"Beat81 update failed: {err}") from err

        booked = sum(
            1
            for b in bookings
            if b.get("current_status", {}).get("status_name") == "booked"
        )
        waitlisted = sum(
            1
            for b in bookings
            if b.get("current_status", {}).get("status_name") == "waitlisted"
        )
        return Beat81CoordinatorData(
            bookings=bookings,
            waitlist_rows=_build_waitlist_rows(bookings),
            booked_count=booked,
            waitlist_count=waitlisted,
            promote_messages=[],
            last_promote_ok=None,
            token_expires_iso=token_exp_iso(self.client.token),
        )

    async def async_promote_waitlist(self) -> list[str]:
        """Try to book the first promotable waitlisted class (same rules as beat81_bot)."""
        messages: list[str] = []
        promoted_any = False

        try:
            bookings = await self.client.async_load_bookings()
        except Exception as e:
            messages.append(str(e))
            prev = self.data or Beat81CoordinatorData()
            self.async_set_updated_data(
                Beat81CoordinatorData(
                    bookings=prev.bookings,
                    waitlist_rows=prev.waitlist_rows,
                    booked_count=prev.booked_count,
                    waitlist_count=prev.waitlist_count,
                    promote_messages=messages,
                    last_promote_ok=False,
                    token_expires_iso=token_exp_iso(self.client.token),
                )
            )
            return messages

        booked_count = sum(
            1
            for b in bookings
            if b.get("current_status", {}).get("status_name") == "booked"
        )
        waitlist_count = sum(
            1
            for b in bookings
            if b.get("current_status", {}).get("status_name") == "waitlisted"
        )
        booked_dates = {
            _parse_event_dt(b["event"]["date_begin"]).date()
            for b in bookings
            if b.get("current_status", {}).get("status_name") == "booked"
            and b.get("event", {}).get("date_begin")
        }
        messages.append(
            f"{datetime.now(timezone.utc).astimezone().isoformat()}  "
            f"Checking {len(bookings)} upcoming bookings ({booked_count} booked, {waitlist_count} waitlisted)."
        )

        for booking in bookings:
            ev = booking.get("event") or {}
            db = ev.get("date_begin")
            if not db:
                continue
            booking_date = _parse_event_dt(str(db)).date()
            is_waitlist = (
                booking.get("current_status", {}).get("status_name") == "waitlisted"
            )
            cur = int(ev.get("current_participants_count") or 0)
            maxp = int(ev.get("max_participants") or 0)
            is_bookable = maxp > 0 and cur < maxp

            if is_waitlist and is_bookable and booking_date not in booked_dates:
                loc = ev.get("location") or {}
                loc_name = loc.get("name") or "—"
                messages.append(
                    f"Trying to book: {db}  {loc_name}  ({cur}/{maxp} spots)"
                )
                tid = booking.get("id")
                if not tid:
                    messages.append("Missing ticket id — skip.")
                    continue
                try:
                    res = await self.client.async_book_ticket(str(tid))
                    messages.append(
                        json.dumps(res, indent=2)
                        if isinstance(res, (dict, list))
                        else str(res)
                    )
                    booked_dates.add(booking_date)
                    promoted_any = True
                except Exception as ex:
                    messages.append(str(ex))

        if not promoted_any:
            messages.append(
                "No waitlisted class was booked. "
                "Usually the class is still full, or you already have another booking that day."
            )

        fresh = await self.client.async_load_bookings()
        data = Beat81CoordinatorData(
            bookings=fresh,
            waitlist_rows=_build_waitlist_rows(fresh),
            booked_count=sum(
                1
                for b in fresh
                if b.get("current_status", {}).get("status_name") == "booked"
            ),
            waitlist_count=sum(
                1
                for b in fresh
                if b.get("current_status", {}).get("status_name") == "waitlisted"
            ),
            promote_messages=messages,
            last_promote_ok=promoted_any,
            token_expires_iso=token_exp_iso(self.client.token),
        )
        self.async_set_updated_data(data)
        return messages
