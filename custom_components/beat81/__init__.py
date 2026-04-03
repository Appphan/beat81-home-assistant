"""Beat81 custom integration — UI config flow (YAML imports into a config entry)."""

from __future__ import annotations

import logging
from datetime import timedelta

import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .client import Beat81Client
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_TOKEN,
    CONF_USER_ID,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    SERVICE_PROMOTE_WAITLIST,
)
from .coordinator import Beat81Coordinator

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_TOKEN): cv.string,
                vol.Optional(CONF_USER_ID): cv.string,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=DEFAULT_SCAN_INTERVAL,
                ): cv.positive_time_period,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.CALENDAR,
    Platform.BUTTON,
    Platform.BINARY_SENSOR,
]


def _coordinators(hass: HomeAssistant) -> dict[str, Beat81Coordinator]:
    return hass.data.setdefault(DOMAIN, {}).setdefault("coordinators", {})


def _register_service(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_PROMOTE_WAITLIST):
        return

    async def _promote(_call: ServiceCall) -> None:
        coords = _coordinators(hass)
        if not coords:
            return
        coord = next(iter(coords.values()))
        await coord.async_promote_waitlist()

    hass.services.async_register(DOMAIN, SERVICE_PROMOTE_WAITLIST, _promote)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """YAML `beat81:` block migrates into a config entry (no duplicate platform setup)."""
    hass.data.setdefault(DOMAIN, {"coordinators": {}})
    conf = config.get(DOMAIN)
    if conf:
        interval = conf[CONF_SCAN_INTERVAL]
        minutes = max(1, int(interval.total_seconds() / 60))
        _LOGGER.warning(
            "YAML configuration for Beat81 is deprecated; this import will create a UI entry. "
            "Remove the `beat81:` block from configuration.yaml after setup."
        )
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data={
                    CONF_TOKEN: conf[CONF_TOKEN],
                    CONF_USER_ID: (conf.get(CONF_USER_ID) or "").strip(),
                    CONF_SCAN_INTERVAL_MINUTES: minutes,
                },
            )
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Beat81 from a config entry."""
    token = entry.data[CONF_TOKEN]
    user_id = (entry.data.get(CONF_USER_ID) or "").strip() or None
    minutes = entry.options.get(
        CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
    )
    interval = timedelta(minutes=minutes)

    client = Beat81Client(token, user_id_override=user_id)
    coordinator = Beat81Coordinator(hass, client, interval, config_entry=entry)
    await coordinator.async_config_entry_first_refresh()

    _coordinators(hass)[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _register_service(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    coord = _coordinators(hass).pop(entry.entry_id, None)
    if coord:
        await coord.client.async_close()

    if not _coordinators(hass) and hass.services.has_service(
        DOMAIN, SERVICE_PROMOTE_WAITLIST
    ):
        hass.services.async_remove(DOMAIN, SERVICE_PROMOTE_WAITLIST)

    return True
