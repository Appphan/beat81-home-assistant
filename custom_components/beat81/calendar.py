"""Beat81 calendar — upcoming booked and waitlisted classes."""

from __future__ import annotations

import datetime as dt
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import Beat81Coordinator
from .entity import Beat81Entity

DEFAULT_DURATION = dt.timedelta(hours=1)


def _parse_utc(iso_s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(iso_s.replace("Z", "+00:00"))


def _event_end(ev: dict[str, Any], start: dt.datetime) -> dt.datetime:
    raw_end = ev.get("date_end")
    if raw_end:
        try:
            return _parse_utc(str(raw_end))
        except ValueError:
            pass
    return start + DEFAULT_DURATION


def _booking_to_calendar_event(booking: dict[str, Any]) -> CalendarEvent | None:
    ev = booking.get("event") or {}
    raw_begin = ev.get("date_begin")
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
) -> list[CalendarEvent]:
    out: list[CalendarEvent] = []
    start_utc = dt_util.as_utc(start_date)
    end_utc = dt_util.as_utc(end_date)
    for b in bookings:
        ce = _booking_to_calendar_event(b)
        if ce is None:
            continue
        s = dt_util.as_utc(ce.start) if isinstance(ce.start, dt.datetime) else None
        e = dt_util.as_utc(ce.end) if isinstance(ce.end, dt.datetime) else None
        if s is None or e is None:
            continue
        if e < start_utc or s > end_utc:
            continue
        out.append(ce)
    out.sort(key=lambda x: x.start if isinstance(x.start, dt.datetime) else dt.datetime.min)
    return out


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    if not discovery_info or "coordinator" not in discovery_info:
        return
    coordinator: Beat81Coordinator = discovery_info["coordinator"]
    async_add_entities([Beat81ClassesCalendar(coordinator)])


class Beat81ClassesCalendar(Beat81Entity, CalendarEntity):
    """All upcoming non-cancelled tickets as calendar events."""

    _attr_has_entity_name = True
    _attr_name = "Classes"
    _attr_should_poll = False

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_classes"

    @property
    def event(self) -> CalendarEvent | None:
        if self.coordinator.data is None:
            return None
        now = dt_util.now()
        future = _events_from_bookings(
            self.coordinator.data.bookings, now, now + dt.timedelta(days=365)
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
            self.coordinator.data.bookings, start_date, end_date
        )
