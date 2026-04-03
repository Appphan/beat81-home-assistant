"""Config flow for Beat81 — UI setup with token guide."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .client import Beat81Client, user_id_from_token
from .const import (
    CONF_AUTO_PROMOTE,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_SCAN_INTERVAL_SECONDS,
    CONF_TOKEN,
    CONF_USER_ID,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
    SCAN_INTERVAL_CHOICES,
    snap_scan_interval_seconds,
)

_LOGGER = logging.getLogger(__name__)


def _scan_interval_labels(sec: int) -> str:
    if sec < 60:
        return f"{sec} seconds"
    if sec == 60:
        return "1 minute"
    if sec < 3600 and sec % 60 == 0:
        m = sec // 60
        return f"{m} minutes"
    if sec == 3600:
        return "1 hour"
    return f"{sec} seconds"


SCAN_INTERVAL_OPTIONS = [
    selector.SelectOptionDict(value=str(s), label=_scan_interval_labels(s))
    for s in SCAN_INTERVAL_CHOICES
]


def _default_seconds_str(seconds: int) -> str:
    if seconds in SCAN_INTERVAL_CHOICES:
        return str(seconds)
    return str(snap_scan_interval_seconds(seconds))


def _user_schema_defaults(
    *,
    token: str = "",
    user_id: str = "",
    scan_seconds: int = DEFAULT_SCAN_INTERVAL_SECONDS,
) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_TOKEN, default=token): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.PASSWORD,
                    autocomplete="off",
                ),
            ),
            vol.Optional(CONF_USER_ID, default=user_id): selector.TextSelector(),
            vol.Optional(
                CONF_SCAN_INTERVAL_SECONDS,
                default=_default_seconds_str(scan_seconds),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=SCAN_INTERVAL_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )


async def _validate_token(
    token: str,
    user_id: str | None,
) -> str:
    """Call API; return unique_id (Beat81 user id). Closes its own client session."""
    clean_token = (token or "").strip()
    if not clean_token:
        raise ValueError("empty_token")
    client = Beat81Client(
        clean_token,
        user_id_override=(user_id or "").strip() or None,
    )
    try:
        await client.async_load_bookings()
    finally:
        await client.async_close()
    try:
        return user_id_from_token(clean_token)
    except KeyError:
        uid = (user_id or "").strip()
        if len(uid) >= 8:
            return uid
        raise ValueError("no_user_id") from None


class Beat81ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle UI and YAML import."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Prompt for JWT and options (description explains how to obtain the token)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                uid = await _validate_token(
                    user_input[CONF_TOKEN],
                    user_input.get(CONF_USER_ID),
                )
            except ValueError as err:
                key = err.args[0] if err.args else "unknown"
                if key == "empty_token":
                    errors["base"] = "empty_token"
                elif key == "no_user_id":
                    errors["base"] = "no_user_id"
                else:
                    errors["base"] = "unknown"
            except RuntimeError as err:
                msg = str(err).lower()
                if "401" in msg or "invalid" in msg or "expired" in msg:
                    errors["base"] = "invalid_auth"
                else:
                    errors["base"] = "cannot_connect"
                    _LOGGER.exception("Beat81 connection failed")
            except Exception:
                errors["base"] = "cannot_connect"
                _LOGGER.exception("Beat81 connection failed")
            else:
                await self.async_set_unique_id(uid)
                self._abort_if_unique_id_configured()
                seconds = int(user_input[CONF_SCAN_INTERVAL_SECONDS])
                opts: dict[str, Any] = {
                    CONF_SCAN_INTERVAL_SECONDS: seconds,
                    CONF_AUTO_PROMOTE: False,
                }
                return self.async_create_entry(
                    title="Beat81",
                    data={
                        CONF_TOKEN: user_input[CONF_TOKEN].strip(),
                        CONF_USER_ID: (user_input.get(CONF_USER_ID) or "").strip(),
                    },
                    options=opts,
                )

            return self.async_show_form(
                step_id="user",
                data_schema=_user_schema_defaults(
                    token=user_input.get(CONF_TOKEN, ""),
                    user_id=user_input.get(CONF_USER_ID, ""),
                    scan_seconds=int(user_input[CONF_SCAN_INTERVAL_SECONDS]),
                ),
                errors=errors,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema_defaults(),
            errors=errors,
        )

    async def async_step_import(self, import_config: dict[str, Any]) -> ConfigFlowResult:
        """YAML import — same validation as UI."""
        token = import_config[CONF_TOKEN]
        user_id = import_config.get(CONF_USER_ID) or ""
        minutes = int(
            import_config.get(CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES)
        )
        seconds = snap_scan_interval_seconds(max(5, minutes * 60))
        try:
            uid = await _validate_token(token, user_id or None)
        except Exception:
            _LOGGER.exception("Beat81 YAML import failed validation")
            return self.async_abort(reason="import_failed")
        await self.async_set_unique_id(uid)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title="Beat81",
            data={
                CONF_TOKEN: token.strip(),
                CONF_USER_ID: user_id.strip(),
            },
            options={
                CONF_SCAN_INTERVAL_SECONDS: seconds,
                CONF_AUTO_PROMOTE: False,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return Beat81OptionsFlow(config_entry)


class Beat81OptionsFlow(OptionsFlow):
    """Reload integration after changing poll interval or auto-promote."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            merged = dict(self.config_entry.options)
            merged[CONF_SCAN_INTERVAL_SECONDS] = int(
                user_input[CONF_SCAN_INTERVAL_SECONDS]
            )
            merged[CONF_AUTO_PROMOTE] = user_input[CONF_AUTO_PROMOTE]
            merged.pop(CONF_SCAN_INTERVAL_MINUTES, None)
            return self.async_create_entry(title="", data=merged)

        opts = self.config_entry.options
        if CONF_SCAN_INTERVAL_SECONDS in opts:
            current_sec = int(opts[CONF_SCAN_INTERVAL_SECONDS])
        else:
            current_sec = int(opts.get(CONF_SCAN_INTERVAL_MINUTES, 15)) * 60
        scan_default = _default_seconds_str(current_sec)
        auto_default = opts.get(CONF_AUTO_PROMOTE, False)
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL_SECONDS,
                    default=scan_default,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=SCAN_INTERVAL_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_AUTO_PROMOTE, default=auto_default): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
