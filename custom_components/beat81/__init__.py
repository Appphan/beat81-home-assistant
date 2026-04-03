"""Beat81 custom integration — config token only, no browser."""

from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv, discovery
from homeassistant.helpers.typing import ConfigType

from .client import Beat81Client
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    CONF_USER_ID,
    DEFAULT_SCAN_INTERVAL,
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


PLATFORMS = ("sensor", "calendar", "button")


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """YAML setup: token from configuration / secrets."""
    conf = config.get(DOMAIN)
    if not conf:
        return True

    token = conf[CONF_TOKEN]
    user_id = conf.get(CONF_USER_ID)
    interval = conf[CONF_SCAN_INTERVAL]

    client = Beat81Client(token, user_id_override=user_id)
    coordinator = Beat81Coordinator(hass, client, interval)

    await coordinator.async_refresh()

    hass.data[DOMAIN] = coordinator

    async def _promote(_call: ServiceCall) -> None:
        coo: Beat81Coordinator = hass.data[DOMAIN]
        await coo.async_promote_waitlist()

    hass.services.async_register(DOMAIN, SERVICE_PROMOTE_WAITLIST, _promote)

    for platform in PLATFORMS:
        hass.async_create_task(
            discovery.async_load_platform(
                hass,
                platform,
                DOMAIN,
                {"coordinator": coordinator},
                config,
            )
        )

    return True
