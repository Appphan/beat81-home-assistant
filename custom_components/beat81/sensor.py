"""Beat81 summary sensor."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .booking_filters import without_cancelled
from .const import (
    ATTR_BOOKED_COUNT,
    ATTR_BOOKINGS,
    ATTR_CONFIGURED_IDLE_POLL_SECONDS,
    ATTR_CONFIGURED_WAITLIST_POLL_SECONDS,
    ATTR_LAST_ERROR,
    ATTR_NEXT_POLL_INTERVAL_SECONDS,
    ATTR_POLLING_SUMMARY,
    ATTR_POLL_TIER,
    ATTR_TOKEN_EXPIRES,
    ATTR_WAITLIST,
    ATTR_WAITLIST_COUNT,
    DOMAIN,
)
from .coordinator import Beat81Coordinator, _format_poll_interval
from .entity import Beat81Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Beat81Coordinator = hass.data[DOMAIN]["coordinators"][
        entry.entry_id
    ]
    async_add_entities([Beat81SummarySensor(coordinator)])


class Beat81SummarySensor(Beat81Entity, SensorEntity):
    """Aggregated bookings / waitlist status."""

    _attr_has_entity_name = True
    _attr_name = "Status"
    _attr_icon = "mdi:dumbbell"
    _attr_should_poll = False

    @property
    def unique_id(self) -> str:
        uid = (
            self.coordinator.config_entry.unique_id
            if self.coordinator.config_entry
            else "legacy"
        )
        return f"{DOMAIN}_{uid}_status"

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None:
            return None
        d = self.coordinator.data
        tier = "fast" if d.poll_tier == "aggressive" else "slow"
        return (
            f"{d.booked_count} booked · {d.waitlist_count} waitlist "
            f"· {tier} {_format_poll_interval(d.next_poll_interval_seconds)}"
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self.coordinator.data is None:
            return {}
        d = self.coordinator.data
        err = None
        if self.coordinator.last_update_success is False and self.coordinator.last_exception:
            err = str(self.coordinator.last_exception)
        attrs: dict[str, Any] = {
            ATTR_BOOKED_COUNT: d.booked_count,
            ATTR_WAITLIST_COUNT: d.waitlist_count,
            ATTR_WAITLIST: d.waitlist_rows,
            ATTR_BOOKINGS: without_cancelled(d.bookings),
            ATTR_TOKEN_EXPIRES: d.token_expires_iso,
            ATTR_POLL_TIER: d.poll_tier,
            ATTR_NEXT_POLL_INTERVAL_SECONDS: d.next_poll_interval_seconds,
            ATTR_CONFIGURED_WAITLIST_POLL_SECONDS: d.configured_waitlist_poll_seconds,
            ATTR_CONFIGURED_IDLE_POLL_SECONDS: d.configured_idle_poll_seconds,
            ATTR_POLLING_SUMMARY: d.polling_summary,
        }
        if d.promote_messages:
            attrs["last_promote_log"] = "\n".join(d.promote_messages[-20:])
        if d.last_promote_ok is not None:
            attrs["last_promote_success"] = d.last_promote_ok
        if err:
            attrs[ATTR_LAST_ERROR] = err
        return attrs
