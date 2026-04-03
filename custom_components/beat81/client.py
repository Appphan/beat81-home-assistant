"""Async Beat81 API client (configuration-based token only)."""

from __future__ import annotations

import base64
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import aiohttp

from .const import BOOKING_URL

_LOGGER = logging.getLogger(__name__)

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
)


def _jwt_payload_dict(token: str) -> dict[str, Any]:
    parts = (token or "").strip().split(".")
    if len(parts) != 3:
        raise ValueError("invalid jwt shape")
    payload = parts[1]
    raw = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
    return json.loads(raw.decode("utf-8"))


def user_id_from_token(token: str) -> str:
    data = _jwt_payload_dict(token)
    for key in ("userId", "user_id", "sub"):
        v = data.get(key)
        if isinstance(v, str) and len(v.strip()) >= 8:
            return v.strip()
    raise KeyError("userId")


def token_exp_iso(token: str) -> str | None:
    try:
        data = _jwt_payload_dict(token)
    except Exception:
        return None
    exp = data.get("exp")
    if exp is None:
        return None
    try:
        ts = float(exp)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def token_clock_expired(token: str, *, skew_sec: int = 60) -> bool:
    try:
        data = _jwt_payload_dict(token)
    except Exception:
        return False
    exp = data.get("exp")
    if exp is None:
        return False
    try:
        exp_f = float(exp)
    except (TypeError, ValueError):
        return False
    return time.time() >= exp_f - float(skew_sec)


class Beat81Client:
    """Minimal tickets API wrapper."""

    def __init__(
        self,
        token: str,
        *,
        user_id_override: str | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._token = (token or "").strip()
        self._user_id = (user_id_override or "").strip() or None
        self._owns_session = session is None
        self._session = session

    @property
    def token(self) -> str:
        return self._token

    @property
    def user_id(self) -> str:
        if self._user_id:
            return self._user_id
        return user_id_from_token(self._token)

    def _headers(self) -> dict[str, str]:
        return {
            "authorization": f"Bearer {self._token}",
            "user-agent": UA,
            "content-type": "application/json",
        }

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        return self._session

    async def async_close(self) -> None:
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None

    async def async_load_bookings(self) -> list[dict[str, Any]]:
        if token_clock_expired(self._token):
            raise RuntimeError("Beat81 token expired — sign in again with beat81_bot and update secrets.")

        now = datetime.now(timezone.utc)
        params = {
            "user_id": self.user_id,
            "$sort[event_date_begin]": 1,
            "event_date_begin_gte": now.astimezone().isoformat(timespec="milliseconds"),
            "status_ne": "cancelled",
            "$limit": 100,
            "$skip": 0,
        }
        url = f"{BOOKING_URL}?{urlencode(params)}"
        session = await self._ensure_session()
        async with session.get(url, headers=self._headers()) as resp:
            body = await resp.text()
            if resp.status == 401:
                raise RuntimeError("Beat81 API returned 401 — token invalid or expired.")
            if resp.status != 200:
                raise RuntimeError(f"Beat81 API HTTP {resp.status}: {body[:500]}")
            data = json.loads(body)
        raw = data.get("data")
        if not isinstance(raw, list):
            return []
        return raw

    async def async_book_ticket(self, ticket_id: str) -> Any:
        session = await self._ensure_session()
        url = f"{BOOKING_URL}/{ticket_id}/status"
        payload = json.dumps({"status_name": "booked"}).encode("utf-8")
        async with session.post(
            url, data=payload, headers=self._headers()
        ) as resp:
            text = await resp.text()
            if resp.status >= 400:
                raise RuntimeError(f"Book failed HTTP {resp.status}: {text[:500]}")
            if not text.strip():
                return {}
            return json.loads(text)
