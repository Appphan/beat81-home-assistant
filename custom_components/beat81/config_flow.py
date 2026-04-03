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
    CONF_SCAN_INTERVAL_IDLE_SECONDS,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_SCAN_INTERVAL_SECONDS,
    CONF_SCAN_INTERVAL_WAITLIST_SECONDS,
    CONF_TOKEN,
    CONF_USER_ID,
    DEFAULT_IDLE_POLL_SECONDS,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DEFAULT_WAITLIST_POLL_SECONDS,
    DOMAIN,
    IDLE_POLL_CHOICES,
    WAITLIST_POLL_CHOICES,
    snap_idle_seconds,
    snap_scan_interval_seconds,
    snap_waitlist_seconds,
)

_LOGGER = logging.getLogger(__name__)


def _human_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} seconds"
    if seconds == 60:
        return "1 minute"
    if seconds < 3600 and seconds % 60 == 0:
        m = seconds // 60
        return f"{m} minutes"
    if seconds == 3600:
        return "1 hour"
    return f"{seconds} seconds"


WAITLIST_POLL_OPTIONS = [
    selector.SelectOptionDict(value=str(s), label=_human_duration(s))
    for s in WAITLIST_POLL_CHOICES
]

IDLE_POLL_OPTIONS = [
    selector.SelectOptionDict(value=str(s), label=_human_duration(s))
    for s in IDLE_POLL_CHOICES
]


def _str_choice(seconds: int, choices: tuple[int, ...], snap_fn) -> str:
    if seconds in choices:
        return str(seconds)
    return str(snap_fn(seconds))


def _user_schema_defaults(
    *,
    token: str = "",
    user_id: str = "",
    waitlist_seconds: int = DEFAULT_WAITLIST_POLL_SECONDS,
    idle_seconds: int = DEFAULT_IDLE_POLL_SECONDS,
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
                CONF_SCAN_INTERVAL_WAITLIST_SECONDS,
                default=_str_choice(
                    waitlist_seconds, WAITLIST_POLL_CHOICES, snap_waitlist_seconds
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=WAITLIST_POLL_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_SCAN_INTERVAL_IDLE_SECONDS,
                default=_str_choice(idle_seconds, IDLE_POLL_CHOICES, snap_idle_seconds),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=IDLE_POLL_OPTIONS,
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
                opts: dict[str, Any] = {
                    CONF_SCAN_INTERVAL_WAITLIST_SECONDS: int(
                        user_input[CONF_SCAN_INTERVAL_WAITLIST_SECONDS]
                    ),
                    CONF_SCAN_INTERVAL_IDLE_SECONDS: int(
                        user_input[CONF_SCAN_INTERVAL_IDLE_SECONDS]
                    ),
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
                    waitlist_seconds=int(
                        user_input[CONF_SCAN_INTERVAL_WAITLIST_SECONDS]
                    ),
                    idle_seconds=int(user_input[CONF_SCAN_INTERVAL_IDLE_SECONDS]),
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
        idle_s = snap_idle_seconds(max(60, minutes * 60))
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
                CONF_SCAN_INTERVAL_WAITLIST_SECONDS: DEFAULT_WAITLIST_POLL_SECONDS,
                CONF_SCAN_INTERVAL_IDLE_SECONDS: idle_s,
                CONF_AUTO_PROMOTE: False,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return Beat81OptionsFlow(config_entry)


def _options_defaults(opts: dict[str, Any]) -> tuple[str, str]:
    """Return default strings for waitlist + idle selects (migrates legacy keys)."""
    if CONF_SCAN_INTERVAL_WAITLIST_SECONDS in opts:
        w = int(opts[CONF_SCAN_INTERVAL_WAITLIST_SECONDS])
    else:
        w = DEFAULT_WAITLIST_POLL_SECONDS
    if CONF_SCAN_INTERVAL_IDLE_SECONDS in opts:
        i = int(opts[CONF_SCAN_INTERVAL_IDLE_SECONDS])
    elif CONF_SCAN_INTERVAL_SECONDS in opts:
        i = snap_idle_seconds(max(60, int(opts[CONF_SCAN_INTERVAL_SECONDS])))
    else:
        i = int(opts.get(CONF_SCAN_INTERVAL_MINUTES, 15)) * 60
        i = snap_idle_seconds(max(60, i))
    return (
        _str_choice(w, WAITLIST_POLL_CHOICES, snap_waitlist_seconds),
        _str_choice(i, IDLE_POLL_CHOICES, snap_idle_seconds),
    )


class Beat81OptionsFlow(OptionsFlow):
    """Reload integration after changing poll intervals or auto-promote."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            merged = dict(self.config_entry.options)
            merged[CONF_SCAN_INTERVAL_WAITLIST_SECONDS] = int(
                user_input[CONF_SCAN_INTERVAL_WAITLIST_SECONDS]
            )
            merged[CONF_SCAN_INTERVAL_IDLE_SECONDS] = int(
                user_input[CONF_SCAN_INTERVAL_IDLE_SECONDS]
            )
            merged[CONF_AUTO_PROMOTE] = user_input[CONF_AUTO_PROMOTE]
            merged.pop(CONF_SCAN_INTERVAL_SECONDS, None)
            merged.pop(CONF_SCAN_INTERVAL_MINUTES, None)
            return self.async_create_entry(title="", data=merged)

        w_def, i_def = _options_defaults(dict(self.config_entry.options))
        auto_default = self.config_entry.options.get(CONF_AUTO_PROMOTE, False)
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL_WAITLIST_SECONDS,
                    default=w_def,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=WAITLIST_POLL_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_SCAN_INTERVAL_IDLE_SECONDS,
                    default=i_def,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=IDLE_POLL_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_AUTO_PROMOTE, default=auto_default): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
