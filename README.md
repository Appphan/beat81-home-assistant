# Beat81 Home Assistant integration

Unofficial Home Assistant custom integration for Beat81 class bookings. This integration does **not** use a browser on your HA host: you supply a Beat81 **Bearer JWT** (for example from a desktop sign-in helper or by copying the token your browser uses for the Beat81 web app). When the token expires, obtain a new JWT and update your Home Assistant secret.

## Contents

| Path | Purpose |
|------|---------|
| `custom_components/beat81/` | Custom integration (copy into HA `/config/custom_components/`) |
| `configuration.example.yaml` | Ready-to-merge `beat81:` block and `secrets` example |
| `lovelace/beat81-dashboard.yaml` | Lovelace layout: calendar, waitlist, one-tap promote |

## Features

- **Upcoming classes** as a **calendar** (booked and waitlisted, non-cancelled), so the built-in Calendar card and agenda views work.
- **Status sensor** with counts and structured waitlist rows (spots open, same-day block, can promote).
- **Button** “Promote waitlist” plus service **`beat81.promote_waitlist`** — tries to promote the first eligible waitlisted class.

## Requirements

- Home Assistant **2024.1** or newer (calendar + button patterns as implemented).
- Network access from HA to `https://api.production.b81.io`.

## Installation

1. Copy the folder `custom_components/beat81` into your Home Assistant configuration directory:

   `/config/custom_components/beat81/`

2. Add your token to `secrets.yaml` (see `configuration.example.yaml`).

3. Merge the `beat81:` block from `configuration.example.yaml` into `configuration.yaml`.

4. Restart Home Assistant.

5. Optional: add the dashboard from `lovelace/beat81-dashboard.yaml` (raw YAML mode or as a manual dashboard).

Confirm entity ids under **Settings → Devices & services → Beat81** (or **Developer tools → States**). Defaults are usually `calendar.beat81_classes`, `sensor.beat81_status`, and `button.beat81_promote_waitlist`; adjust the Lovelace file if yours differ.

## Configuration

| Key | Required | Description |
|-----|----------|-------------|
| `token` | Yes | Bearer JWT from Beat81 (e.g. use `!secret beat81_token` in `configuration.yaml`). |
| `user_id` | No | Override if the JWT payload does not expose a usable user id (rare). |
| `scan_interval` | No | Polling interval for bookings (default 15 minutes). |

## Token lifecycle

Beat81 tokens are JWTs with an expiry. When API calls fail with **401** or the integration logs auth errors, obtain a fresh JWT, update `secrets.yaml`, and reload or restart Home Assistant.

## Service

- **`beat81.promote_waitlist`** — runs the same promotion logic as the button (useful in automations).

## Support

This integration is unofficial and uses the same public API endpoints as the Beat81 web app. It is not affiliated with Beat81.
