import json
import secrets
import time
from typing import Any

from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from tools.calendar import config, google_api, store

_oauth_states: dict[str, int] = {}


def _ensure_client_config() -> None:
    if not config.CLIENT_ID or not config.CLIENT_SECRET:
        raise HTTPException(
            status_code=400,
            detail="Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET in environment.",
        )


def _cleanup_states() -> None:
    cutoff = int(time.time()) - 900
    stale = [k for k, ts in _oauth_states.items() if ts < cutoff]
    for key in stale:
        _oauth_states.pop(key, None)


def auth_status(sync_health: dict) -> dict:
    token_data = store.load_token()
    if not token_data:
        return {
            "connected": False,
            "redirect_uri": config.REDIRECT_URI,
            "default_calendar_id": config.API_DEFAULT_CAL_ID,
            "sync": sync_health,
        }

    return {
        "connected": True,
        "has_refresh_token": bool(token_data.get("refresh_token")),
        "expiry": token_data.get("expiry"),
        "redirect_uri": config.REDIRECT_URI,
        "default_calendar_id": config.API_DEFAULT_CAL_ID,
        "sync": sync_health,
    }


def auth_start() -> dict:
    google_api.ensure_google_libs()
    _ensure_client_config()
    _cleanup_states()

    state = secrets.token_urlsafe(24)
    _oauth_states[state] = int(time.time())

    client_config = {
        "web": {
            "client_id": config.CLIENT_ID,
            "client_secret": config.CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [config.REDIRECT_URI],
        }
    }

    flow = google_api.Flow.from_client_config(client_config, scopes=config.SCOPES, state=state)
    flow.redirect_uri = config.REDIRECT_URI

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return {"auth_url": auth_url, "state": state}


def auth_callback(code: str, state: str) -> RedirectResponse:
    google_api.ensure_google_libs()
    _ensure_client_config()
    _cleanup_states()

    if state not in _oauth_states:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")
    _oauth_states.pop(state, None)

    client_config = {
        "web": {
            "client_id": config.CLIENT_ID,
            "client_secret": config.CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [config.REDIRECT_URI],
        }
    }

    flow = google_api.Flow.from_client_config(client_config, scopes=config.SCOPES, state=state)
    flow.redirect_uri = config.REDIRECT_URI
    flow.fetch_token(code=code)

    creds = flow.credentials
    store.save_token(json.loads(creds.to_json()))
    return RedirectResponse(url="/widget", status_code=302)


def auth_disconnect() -> dict:
    store.delete_token()
    return {"disconnected": True}


def credentials_from_db() -> Any:
    google_api.ensure_google_libs()
    token_data = store.load_token()
    if not token_data:
        return None

    creds = google_api.Credentials.from_authorized_user_info(token_data, config.SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(google_api.GoogleAuthRequest())
        store.save_token(json.loads(creds.to_json()))
    return creds


def build_service() -> Any:
    creds = credentials_from_db()
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated. Connect Google first.")
    return google_api.build("calendar", "v3", credentials=creds, cache_discovery=False)
