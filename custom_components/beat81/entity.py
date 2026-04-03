"""Shared device info for Beat81 entities."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Beat81Coordinator


class Beat81Entity(CoordinatorEntity[Beat81Coordinator]):
    """Base entity attached to one Beat81 device."""

    @property
    def device_info(self) -> DeviceInfo:
        entry = self.coordinator.config_entry
        ident = (
            (DOMAIN, entry.entry_id) if entry else (DOMAIN, "hub")
        )
        return DeviceInfo(
            identifiers={ident},
            name="Beat81",
            manufacturer="Beat81",
            model="Waitlist & bookings",
        )
