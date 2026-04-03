"""Binary sensors for Beat81 waitlist state."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
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
    async_add_entities([Beat81WaitlistPromoteReady(coordinator)])


class Beat81WaitlistPromoteReady(Beat81Entity, BinarySensorEntity):
    """True when at least one waitlisted class has a free spot and same-day rule allows booking."""

    _attr_has_entity_name = True
    _attr_name = "Waitlist promote ready"
    _attr_icon = "mdi:seat-passenger"
    _attr_should_poll = False

    @property
    def unique_id(self) -> str:
        uid = (
            self.coordinator.config_entry.unique_id
            if self.coordinator.config_entry
            else "legacy"
        )
        return f"{DOMAIN}_{uid}_waitlist_promote_ready"

    @property
    def is_on(self) -> bool:
        d = self.coordinator.data
        if d is None:
            return False
        return any(row.get("can_promote_now") for row in d.waitlist_rows)
