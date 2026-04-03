# Beat81 Home Assistant integration

**Public repository:** [github.com/Appphan/beat81-home-assistant](https://github.com/Appphan/beat81-home-assistant)

Unofficial Home Assistant custom integration for Beat81 class bookings. This integration does **not** use a browser on your Home Assistant host: you paste a Beat81 **Bearer JWT** in the UI. The config flow includes step-by-step hints on where to find that token. When the token expires, remove the integration and add it again with a new JWT (or update options if you only change the poll interval).

## Contents

| Path | Purpose |
|------|---------|
| `hacs.json` | HACS metadata (only for GitHub / HACS; not copied into `/config`) |
| `custom_components/beat81/` | Custom integration (copy into HA `/config/custom_components/`) |
| `configuration.example.yaml` | Optional legacy YAML import (prefer UI setup) |
| `lovelace/beat81-dashboard.yaml` | Lovelace layout: calendar, waitlist, one-tap promote |

## Features

- **UI setup** with a guided description for obtaining the JWT, optional user-id override, and poll interval.
- **Upcoming classes** as a **calendar** (booked and waitlisted, non-cancelled).
- **Status sensor** with counts and structured waitlist rows (spots open, same-day block, can promote).
- **Button** “Promote waitlist” plus service **`beat81.promote_waitlist`**.
- **Options**: change API poll interval without re-entering the token; optional **auto-promote** after each poll when a waitlisted class becomes bookable.

## Requirements

- Home Assistant **2024.1** or newer.
- Network access from HA to `https://api.production.b81.io`.

## Installation

1. Copy the folder `custom_components/beat81` into your Home Assistant configuration directory:

   `/config/custom_components/beat81/`

2. **Restart Home Assistant.**

3. Go to **Settings → Devices & services → Add integration** and search for **Beat81**. Follow the form; the description explains how to obtain the JWT.

4. Optional: add the dashboard from `lovelace/beat81-dashboard.yaml`. Entity IDs look like `sensor.beat81_<your_user_id>_status` — pick the real entities from **Developer tools → States** or the device page.

### HACS

1. **HACS** → **Integrations** → **⋮** → **Custom repositories** → add `https://github.com/Appphan/beat81-home-assistant` as category **Integration**.
2. **Download** a **release** (e.g. **v1.3.0** or newer) when offered.
3. **Restart Home Assistant**, then add **Beat81** from the UI as above.

The repo root includes **`hacs.json`** so the default branch works with HACS; tagged **releases** are still recommended.

### Legacy YAML (import only)

If you already use a `beat81:` block in `configuration.yaml`, it will be **imported once** into a config entry on restart. After a successful import, **remove** the YAML block to avoid log noise. New setups should use the UI only. See `configuration.example.yaml`.

## Configuration (UI)

| Field | Required | Description |
|-------|----------|-------------|
| JWT | Yes | Full Bearer token (paste without the word `Bearer`). |
| User ID | No | Only if the JWT has no usable user id (rare). |
| Refresh interval | No | How often to poll the API (default 15 minutes). Options can be changed later under **Configure** on the integration card. |
| Auto-promote | No | Under **Configure**: when on, each successful poll runs the same promotion logic as the button if any waitlisted class has a free spot and is not same-day blocked. Shorter intervals react faster when spots open. |

### Automation alternative

You can leave auto-promote off and use an automation instead, for example when `binary_sensor.…_waitlist_promote_ready` turns **on** or on a time pattern, with action `beat81.promote_waitlist`.

## Token lifecycle

Beat81 tokens are JWTs with an expiry. When the API returns **401** or logs show auth errors, sign in again in a browser, copy a new JWT, **remove** the Beat81 integration and **add it again** with the new token.

## Service

- **`beat81.promote_waitlist`** — same logic as the button (first configured Beat81 entry).

## Support

This integration is unofficial and uses the same public API endpoints as the Beat81 web app. It is not affiliated with Beat81.
