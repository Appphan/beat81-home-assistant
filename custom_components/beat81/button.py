"""Button to promote waitlisted classes."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from .const import DOMAIN
from .coordinator import Beat81Coordinator
from .entity import Beat81Entity


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    if not discovery_info or "coordinator" not in discovery_info:
        return
    coordinator: Beat81Coordinator = discovery_info["coordinator"]
    async_add_entities([Beat81PromoteButton(coordinator)])


class Beat81PromoteButton(Beat81Entity, ButtonEntity):
    """Run waitlist promotion (same rules as beat81_bot)."""

    _attr_has_entity_name = True
    _attr_name = "Promote waitlist"
    _attr_icon = "mdi:seat-passenger"
    _attr_should_poll = False

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_promote_waitlist"

    async def async_press(self) -> None:
        await self.coordinator.async_promote_waitlist()
