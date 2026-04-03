# Beat81 Home Assistant integration

**Public repository:** [github.com/Appphan/beat81-home-assistant](https://github.com/Appphan/beat81-home-assistant)

Unofficial Home Assistant custom integration for Beat81 class bookings. This integration does **not** use a browser on your Home Assistant host: you paste a Beat81 **Bearer JWT** in the UI. The config flow includes step-by-step hints on where to find that token. When the token expires, remove the integration and add it again with a new JWT (or update options if you only change the poll interval).

## Contents

| Path | Purpose |
|------|---------|
| `hacs.json` | HACS metadata (only for GitHub / HACS; not copied into `/config`) |
| `custom_components/beat81/` | Custom integration (copy into HA `/config/custom_components/`, includes `booking_filters.py`) |
| `configuration.example.yaml` | Optional legacy YAML import (prefer UI setup) |
| `lovelace/beat81-dashboard.yaml` | Lovelace layout: calendar, waitlist, one-tap promote |
| `automations.example.yaml` | Example YAML for forced refresh + auto-promote |

## Features

- **UI setup** with a guided description for obtaining the JWT, optional user-id override, and poll interval.
- **Calendars:** **Classes** (active booked + waitlist), **Next bookings** (confirmed only), **All workouts** (every ticket status including cancelled, plus ~14 days of past sessions — still **your** tickets only, not the full public schedule).
- **Status sensor** with counts, structured waitlist rows, and **polling feedback** (`poll_tier` aggressive vs idle, next interval seconds, human `polling` summary).
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

4. Optional: add the dashboard from `lovelace/beat81-dashboard.yaml`. Entity IDs look like `sensor.beat81_<your_user_id>_status` and `calendar.beat81_<id>_all_workouts` — pick the real entities from **Developer tools → States** or the device page.

### HACS

1. **HACS** → **Integrations** → **⋮** → **Custom repositories** → add `https://github.com/Appphan/beat81-home-assistant` as category **Integration**.
2. **Download** a **release** (e.g. **v1.6.1** or newer) when offered.
3. **Restart Home Assistant**, then add **Beat81** from the UI as above.

The repo root includes **`hacs.json`** so the default branch works with HACS; tagged **releases** are still recommended.

### Legacy YAML (import only)

If you already use a `beat81:` block in `configuration.yaml`, it will be **imported once** into a config entry on restart. After a successful import, **remove** the YAML block to avoid log noise. New setups should use the UI only. See `configuration.example.yaml`.

## Configuration (UI)

| Field | Required | Description |
|-------|----------|-------------|
| JWT | Yes | Full Bearer token (paste without the word `Bearer`). |
| User ID | No | Only if the JWT has no usable user id (rare). |
| Refresh | No | **Two intervals** under **Configure**: one while you have **any waitlist** (default **5 s**), one when **no waitlist** (default **30 min**). The integration switches automatically after each poll. |
| Auto-promote | No | Under **Configure**: see *How promotion works* below. |

### How refresh works

On each poll the integration calls Beat81’s tickets API (same list as the app), then updates the sensor, calendars, and binary sensor. **Waitlist interval** applies when `waitlist_count > 0`; **idle interval** when you have no waitlisted classes. After promotion clears your last waitlist entry, the next scheduled poll uses the slower idle interval until you join a waitlist again.

### How promotion works

- **Manual:** **Promote waitlist** button or service **`beat81.promote_waitlist`**.
- **Auto-promote (option):** After a **successful** poll, if **any** waitlisted row has `can_promote_now` (free spot **and** no other **booked** class on that **same calendar day**), the integration runs the **same** booking logic as the button: it walks waitlisted classes in API order and **books the first** that still qualifies. One successful promotion may add that day to “already booked,” so another waitlisted class the same day is skipped until the next poll. If nothing qualifies, **no** book request is sent.

### Automation alternative

You can leave auto-promote off and use an automation instead, for example when `binary_sensor.…_waitlist_promote_ready` turns **on** or on a time pattern, with action `beat81.promote_waitlist`.

## Token lifecycle

Beat81 tokens are JWTs with an expiry. When the API returns **401** or logs show auth errors, sign in again in a browser, copy a new JWT, **remove** the Beat81 integration and **add it again** with the new token.

## Service

- **`beat81.promote_waitlist`** — same logic as the button (first configured Beat81 entry).

## Support

This integration is unofficial and uses the same public API endpoints as the Beat81 web app. It is not affiliated with Beat81.
