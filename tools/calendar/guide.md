# Calendar Tool

This tool now supports Google Calendar OAuth and event CRUD APIs, plus a widget that can connect/disconnect and list upcoming events.

## Code Structure

- `tools/calendar/main.py`: thin route wiring + startup/shutdown hooks.
- `tools/calendar/config.py`: env/config constants (OAuth, sync interval, embed settings).
- `tools/calendar/google_api.py`: guarded Google client imports + dependency checks.
- `tools/calendar/store.py`: SQLite persistence for OAuth tokens and sync state.
- `tools/calendar/auth.py`: OAuth flow, credential refresh, authenticated service builder.
- `tools/calendar/service.py`: calendar/event CRUD logic.
- `tools/calendar/sync.py`: incremental sync token flow + background sync worker + health.
- `tools/calendar/widget.py`: widget HTML/CSS/JS.
- `tools/calendar/calendar.db`: runtime SQLite data store.

## Environment Variables

Set these in your project `.env`:

- `GOOGLE_CLIENT_ID` (required for API auth)
- `GOOGLE_CLIENT_SECRET` (required for API auth)
- `GOOGLE_REDIRECT_URI` (optional, default: `http://127.0.0.1:9010/auth/callback`)
- `GOOGLE_CALENDAR_ID` (optional, default: `primary`)
- `CALENDAR_ID` (optional, used for the iframe embed)
- `CALENDAR_TIMEZONE` (optional, used for the iframe embed)
- `CALENDAR_AUTO_SYNC_ENABLED` (optional, default: `true`)
- `CALENDAR_SYNC_INTERVAL_SECONDS` (optional, default: `300`, minimum `15`)
- `CALENDAR_SYNC_MAX_BACKOFF_SECONDS` (optional, default: `1800`)

## Google Cloud Setup

1. Create/select a Google Cloud project.
2. Enable **Google Calendar API**.
3. Configure OAuth consent screen.
4. Create OAuth Client ID (`Web application`).
5. Add redirect URI, e.g. `http://127.0.0.1:9010/auth/callback`.
6. Put client ID/secret in `.env`.

If your app is in Testing mode, add your Google account under OAuth test users.

## Local Dev Runbook

1. Install deps:
   - `pip install -r tools/calendar/requirements.txt`
2. Run with project venv:
   - `.venv/bin/python tools/calendar/main.py`
3. Basic endpoint checks:
   - `curl http://127.0.0.1:9010/health`
   - `curl http://127.0.0.1:9010/auth/status`
   - `curl http://127.0.0.1:9010/sync/health`
4. Open widget:
   - `http://127.0.0.1:9010/widget`
5. OAuth flow:
   - click `Connect Google`
   - approve
   - verify `connected: true` at `/auth/status`

## API Endpoints

- `GET /auth/status`
- `GET /auth/start`
- `GET /auth/callback`
- `POST /auth/disconnect`
- `GET /calendars`
- `GET /events`
- `POST /events`
- `PATCH /events/{event_id}`
- `DELETE /events/{event_id}`
- `GET /sync/state`
- `POST /sync/run`
- `GET /sync/health`

## Example Event Payload

```json
{
  "summary": "1:1 with Alex",
  "description": "Weekly sync",
  "start": { "dateTime": "2026-02-12T15:00:00-05:00" },
  "end": { "dateTime": "2026-02-12T15:30:00-05:00" }
}
```

## Troubleshooting

- `Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET in environment`
  - Confirm `.env` exists at repo root.
  - Ensure values are loaded by the running process.
  - Restart the calendar tool after editing `.env`.
- `Error 403 access_denied` during Google OAuth
  - Add your account as OAuth test user (Google Cloud -> Auth Platform -> Audience).
- `redirect_uri_mismatch`
  - Ensure OAuth client redirect URI is exactly `http://127.0.0.1:9010/auth/callback`.
- `could not bind ... 127.0.0.1:9010`
  - Another process already owns port `9010`; stop it or restart cleanly.
- Embedded calendar shows Google `403` page
  - `CALENDAR_ID` points to a non-public calendar embed.
  - API auth/CRUD can still work even if embed preview fails.

## Known Limits

- OAuth tokens are stored in `tools/calendar/calendar.db`.
- Sync state (incremental sync tokens) is also stored in `tools/calendar/calendar.db`.
- Auto-sync runs in a background worker with retry backoff.
- Single local token profile (`user_key = default`), not multi-user tenancy.
- Conflict resolution policy across external systems is not included yet.
