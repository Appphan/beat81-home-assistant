"""Beat81 summary sensor."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import (
    ATTR_BOOKED_COUNT,
    ATTR_LAST_ERROR,
    ATTR_TOKEN_EXPIRES,
    ATTR_WAITLIST,
    ATTR_WAITLIST_COUNT,
    DOMAIN,
)
from .coordinator import Beat81Coordinator
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
        return f"{d.booked_count} booked · {d.waitlist_count} waitlist"

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
            ATTR_TOKEN_EXPIRES: d.token_expires_iso,
        }
        if d.promote_messages:
            attrs["last_promote_log"] = "\n".join(d.promote_messages[-20:])
        if d.last_promote_ok is not None:
            attrs["last_promote_success"] = d.last_promote_ok
        if err:
            attrs[ATTR_LAST_ERROR] = err
        return attrs
