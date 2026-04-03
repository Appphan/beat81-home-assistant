"""Button to promote waitlisted classes."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
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
    async_add_entities([Beat81PromoteButton(coordinator)])


class Beat81PromoteButton(Beat81Entity, ButtonEntity):
    """Run waitlist promotion (same rules as beat81_bot)."""

    _attr_has_entity_name = True
    _attr_name = "Promote waitlist"
    _attr_icon = "mdi:seat-passenger"
    _attr_should_poll = False

    @property
    def unique_id(self) -> str:
        uid = (
            self.coordinator.config_entry.unique_id
            if self.coordinator.config_entry
            else "legacy"
        )
        return f"{DOMAIN}_{uid}_promote_waitlist"

    async def async_press(self) -> None:
        await self.coordinator.async_promote_waitlist()
