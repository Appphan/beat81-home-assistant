"""Beat81 calendar — upcoming booked and waitlisted classes."""

from __future__ import annotations

import datetime as dt
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .booking_filters import without_cancelled
from .const import DOMAIN
from .coordinator import Beat81Coordinator
from .entity import Beat81Entity

DEFAULT_DURATION = dt.timedelta(hours=1)


def _parse_utc(iso_s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(iso_s.replace("Z", "+00:00"))


def _event_payload(booking: dict[str, Any]) -> dict[str, Any]:
    ev = booking.get("event")
    return ev if isinstance(ev, dict) else {}


def _raw_event_begin(booking: dict[str, Any]) -> Any:
    """Start time from nested event or top-level API fields."""
    ev = _event_payload(booking)
    raw = ev.get("date_begin")
    if raw:
        return raw
    return booking.get("event_date_begin")


def _event_end(ev: dict[str, Any], start: dt.datetime) -> dt.datetime:
    raw_end = ev.get("date_end")
    if raw_end:
        try:
            return _parse_utc(str(raw_end))
        except ValueError:
            pass
    return start + DEFAULT_DURATION


def _status_title(status: str) -> str:
    s = (status or "unknown").replace("_", " ").strip()
    if not s:
        return "Unknown"
    return s[:1].upper() + s[1:]


def _event_workout_label(ev: dict[str, Any]) -> str | None:
    for key in ("name", "title"):
        v = ev.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    w = ev.get("workout")
    if isinstance(w, dict):
        for key in ("name", "title", "label"):
            v = w.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return None


def _booking_to_all_workouts_event(booking: dict[str, Any]) -> CalendarEvent | None:
    """Every ticket session (cancelled, booked, waitlist, …) for the account."""
    ev = _event_payload(booking)
    raw_begin = _raw_event_begin(booking)
    if not raw_begin:
        return None
    try:
        start = _parse_utc(str(raw_begin))
    except ValueError:
        return None
    end = _event_end(ev, start)
    status = (booking.get("current_status") or {}).get("status_name") or "unknown"
    tag = _status_title(status)
    loc_name = str((ev.get("location") or {}).get("name") or "").strip()
    wlabel = _event_workout_label(ev)
    if wlabel and loc_name:
        summary = f"[{tag}] {wlabel} · {loc_name}"
    elif wlabel:
        summary = f"[{tag}] {wlabel}"
    elif loc_name:
        summary = f"[{tag}] {loc_name}"
    else:
        summary = f"[{tag}] Beat81 session"
    cur = int(ev.get("current_participants_count") or 0)
    maxp = int(ev.get("max_participants") or 0)
    spots = max(0, maxp - cur) if maxp else 0
    lines = [
        f"Status: {status}",
        f"Spots: {cur}/{maxp} ({spots} free)" if maxp else "",
    ]
    if wlabel:
        lines.insert(0, f"Workout: {wlabel}")
    description = "\n".join(line for line in lines if line)
    uid = str(booking.get("id") or "")
    return CalendarEvent(
        uid=uid or None,
        summary=summary,
        start=start,
        end=end,
        description=description or None,
        location=loc_name or None,
    )


def _booking_to_calendar_event(
    booking: dict[str, Any],
    *,
    booked_only_calendar: bool = False,
) -> CalendarEvent | None:
    ev = _event_payload(booking)
    raw_begin = _raw_event_begin(booking)
    if not raw_begin:
        return None
    try:
        start = _parse_utc(str(raw_begin))
    except ValueError:
        return None
    end = _event_end(ev, start)
    status = (booking.get("current_status") or {}).get("status_name") or "unknown"
    loc = ev.get("location") or {}
    loc_name = loc.get("name") or ""
    if booked_only_calendar:
        summary = loc_name.strip() if loc_name else "Beat81 class"
    else:
        tag = "Booked" if status == "booked" else "Waitlist" if status == "waitlisted" else status
        summary = f"[{tag}] {loc_name}".strip() if loc_name else f"[{tag}] Class"
    cur = int(ev.get("current_participants_count") or 0)
    maxp = int(ev.get("max_participants") or 0)
    spots = max(0, maxp - cur) if maxp else 0
    lines = [
        f"Status: {status}",
        f"Spots: {cur}/{maxp} ({spots} free)" if maxp else "",
    ]
    description = "\n".join(line for line in lines if line)
    uid = str(booking.get("id") or "")
    return CalendarEvent(
        uid=uid or None,
        summary=summary,
        start=start,
        end=end,
        description=description or None,
        location=loc_name or None,
    )


def _events_from_bookings(
    bookings: list[dict[str, Any]],
    start_date: dt.datetime,
    end_date: dt.datetime,
    *,
    status_filter: set[str] | None = None,
    booked_only_calendar: bool = False,
    all_workouts_calendar: bool = False,
) -> list[CalendarEvent]:
    out: list[CalendarEvent] = []
    start_utc = dt_util.as_utc(start_date)
    end_utc = dt_util.as_utc(end_date)
    for b in bookings:
        st = (b.get("current_status") or {}).get("status_name")
        if status_filter is not None:
            st_key = str(st or "").lower()
            allowed = {x.lower() for x in status_filter}
            if st_key not in allowed:
                continue
        if all_workouts_calendar:
            ce = _booking_to_all_workouts_event(b)
        else:
            ce = _booking_to_calendar_event(b, booked_only_calendar=booked_only_calendar)
        if ce is None:
            continue
        s = dt_util.as_utc(ce.start) if isinstance(ce.start, dt.datetime) else None
        e = dt_util.as_utc(ce.end) if isinstance(ce.end, dt.datetime) else None
        if s is None or e is None:
            continue
        # HA calendar range: include overlaps (exclusive on window bounds).
        if not (s < end_utc and e > start_utc):
            continue
        out.append(ce)
    out.sort(key=lambda x: x.start if isinstance(x.start, dt.datetime) else dt.datetime.min)
    return out


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Beat81Coordinator = hass.data[DOMAIN]["coordinators"][
        entry.entry_id
    ]
    async_add_entities(
        [
            Beat81ClassesCalendar(coordinator),
            Beat81NextBookingsCalendar(coordinator),
            Beat81AllWorkoutsCalendar(coordinator),
        ]
    )


class Beat81ClassesCalendar(Beat81Entity, CalendarEntity):
    """All upcoming non-cancelled tickets as calendar events."""

    _attr_has_entity_name = True
    _attr_name = "Classes"
    _attr_should_poll = False

    @property
    def unique_id(self) -> str:
        uid = (
            self.coordinator.config_entry.unique_id
            if self.coordinator.config_entry
            else "legacy"
        )
        return f"{DOMAIN}_{uid}_classes"

    @property
    def event(self) -> CalendarEvent | None:
        if self.coordinator.data is None:
            return None
        now = dt_util.now()
        active = without_cancelled(self.coordinator.data.bookings)
        future = _events_from_bookings(
            active, now, now + dt.timedelta(days=365)
        )
        return future[0] if future else None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: dt.datetime,
        end_date: dt.datetime,
    ) -> list[CalendarEvent]:
        if self.coordinator.data is None:
            return []
        return _events_from_bookings(
            without_cancelled(self.coordinator.data.bookings),
            start_date,
            end_date,
        )


class Beat81NextBookingsCalendar(Beat81Entity, CalendarEntity):
    """Confirmed (booked) upcoming classes only — cleaner calendar for your schedule."""

    _attr_has_entity_name = True
    _attr_name = "Next bookings"
    _attr_should_poll = False

    @property
    def unique_id(self) -> str:
        uid = (
            self.coordinator.config_entry.unique_id
            if self.coordinator.config_entry
            else "legacy"
        )
        return f"{DOMAIN}_{uid}_next_bookings"

    @property
    def event(self) -> CalendarEvent | None:
        if self.coordinator.data is None:
            return None
        now = dt_util.now()
        active = without_cancelled(self.coordinator.data.bookings)
        future = _events_from_bookings(
            active,
            now,
            now + dt.timedelta(days=365),
            status_filter={"booked"},
            booked_only_calendar=True,
        )
        return future[0] if future else None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: dt.datetime,
        end_date: dt.datetime,
    ) -> list[CalendarEvent]:
        if self.coordinator.data is None:
            return []
        return _events_from_bookings(
            without_cancelled(self.coordinator.data.bookings),
            start_date,
            end_date,
            status_filter={"booked"},
            booked_only_calendar=True,
        )


class Beat81AllWorkoutsCalendar(Beat81Entity, CalendarEntity):
    """All sessions on your Beat81 account (every ticket status + recent past).

    Only includes classes you have a ticket for — not the full public studio schedule.
    """

    _attr_has_entity_name = True
    _attr_name = "All workouts"
    _attr_should_poll = False

    @property
    def unique_id(self) -> str:
        uid = (
            self.coordinator.config_entry.unique_id
            if self.coordinator.config_entry
            else "legacy"
        )
        return f"{DOMAIN}_{uid}_all_workouts"

    @property
    def event(self) -> CalendarEvent | None:
        if self.coordinator.data is None:
            return None
        now = dt_util.now()
        evs = _events_from_bookings(
            self.coordinator.data.bookings,
            now,
            now + dt.timedelta(days=365),
            all_workouts_calendar=True,
        )
        return evs[0] if evs else None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: dt.datetime,
        end_date: dt.datetime,
    ) -> list[CalendarEvent]:
        if self.coordinator.data is None:
            return []
        return _events_from_bookings(
            self.coordinator.data.bookings,
            start_date,
            end_date,
            all_workouts_calendar=True,
        )
