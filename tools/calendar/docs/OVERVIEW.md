# Calendar Tool Overview

## Purpose
Calendar tool provides Google Calendar OAuth and event CRUD through API endpoints and a dashboard widget.

## Current Structure
- `tools/calendar/main.py`: FastAPI app wiring and route registration.
- `tools/calendar/config.py`: environment/config constants.
- `tools/calendar/google_api.py`: Google API client bootstrap.
- `tools/calendar/store.py`: local persistence.
- `tools/calendar/auth.py`: OAuth connect/callback/disconnect/status.
- `tools/calendar/service.py`: event CRUD API handlers and Google error normalization.
- `tools/calendar/sync.py`: sync/health endpoints.
- `tools/calendar/widget.py`: widget HTML/CSS/JS UI.

## Runtime
- Default port: `9010`
- Required env:
  - `GOOGLE_CLIENT_ID`
  - `GOOGLE_CLIENT_SECRET`
- Google OAuth redirect URI:
  - `http://127.0.0.1:9010/auth/callback`

## Widget UI (Current)
- Connected-state controls:
  - `+ Create` toggle button
  - refresh icon button with feedback (`Refreshing...`, success, error)
  - `Disconnect`
- Timezone display in format:
  - `Region/City (GMT±offset)`
- Month-first calendar view:
  - current month title + previous/next month navigation
  - day selection
  - up to 3 event dots per day
  - compact dynamic month grid (no forced 6-week rows)
- Entries panel:
  - filtered to selected day
  - edit/delete actions
- Create/Edit form (toggle above calendar):
  - `Title`
  - `Start Date` and `End Date` in `YYYY-MM-DD HH:MM` (24h)
  - optional `Description`

## Key Behavioral Notes
- Form validates date-time format and enforces `end > start`.
- Event day matching supports timed and all-day events.
- Month loading uses bounded query window (`month start` to `next month start`).
- Google API failures are surfaced as normalized HTTP errors.

## Verification
- Compile check:
  - `python -m py_compile tools/calendar/widget.py`

## Notes
- This document supersedes the previous `tools/calendar/HANDOFF.md`.
