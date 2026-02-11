import threading
import time
from datetime import datetime, timezone

from tools.calendar import auth, config, google_api, store

_sync_thread: threading.Thread | None = None
_sync_stop_event = threading.Event()
_sync_lock = threading.Lock()
_sync_status: dict = {
    "enabled": True,
    "running": False,
    "started_at": None,
    "stopped_at": None,
    "last_started_at": None,
    "last_finished_at": None,
    "last_success_at": None,
    "last_error": None,
    "consecutive_failures": 0,
    "last_changes_count": None,
    "last_calendar_id": config.API_DEFAULT_CAL_ID,
    "next_run_at": None,
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _status_update(**updates) -> None:
    with _sync_lock:
        _sync_status.update(updates)


def health_snapshot() -> dict:
    with _sync_lock:
        return dict(_sync_status)


def _sync_key(calendar_id: str) -> str:
    return f"sync:{calendar_id}"


def _next_delay_seconds() -> int:
    status = health_snapshot()
    failures = int(status.get("consecutive_failures") or 0)
    if failures <= 0:
        return config.SYNC_INTERVAL_SECONDS
    delay = config.SYNC_INTERVAL_SECONDS * (2 ** min(failures, 6))
    return min(delay, config.SYNC_MAX_BACKOFF_SECONDS)


def run_incremental_sync(api_service, calendar_id: str) -> dict:
    key = _sync_key(calendar_id)
    prev_state = store.get_sync_state(key) or {}
    prev_token = prev_state.get("next_sync_token")

    items: list[dict] = []
    next_token = None
    page_token = None
    request_kwargs = {
        "calendarId": calendar_id,
        "singleEvents": True,
        "showDeleted": True,
        "maxResults": 250,
    }

    if prev_token:
        request_kwargs["syncToken"] = prev_token
    else:
        request_kwargs["timeMin"] = datetime.now(timezone.utc).isoformat()
        request_kwargs["orderBy"] = "startTime"

    try:
        while True:
            if page_token:
                request_kwargs["pageToken"] = page_token
            else:
                request_kwargs.pop("pageToken", None)

            response = api_service.events().list(**request_kwargs).execute()
            items.extend(response.get("items", []))
            page_token = response.get("nextPageToken")
            next_token = response.get("nextSyncToken") or next_token
            if not page_token:
                break
    except google_api.HttpError as exc:
        if getattr(exc, "resp", None) is not None and getattr(exc.resp, "status", None) == 410:
            prev_token = None
            items = []
            next_token = None
            page_token = None
            request_kwargs = {
                "calendarId": calendar_id,
                "singleEvents": True,
                "showDeleted": True,
                "maxResults": 250,
                "timeMin": datetime.now(timezone.utc).isoformat(),
                "orderBy": "startTime",
            }
            while True:
                if page_token:
                    request_kwargs["pageToken"] = page_token
                else:
                    request_kwargs.pop("pageToken", None)
                response = api_service.events().list(**request_kwargs).execute()
                items.extend(response.get("items", []))
                page_token = response.get("nextPageToken")
                next_token = response.get("nextSyncToken") or next_token
                if not page_token:
                    break
        else:
            raise

    result = {
        "calendar_id": calendar_id,
        "previous_sync_token_present": bool(prev_token),
        "next_sync_token": next_token,
        "changes_count": len(items),
        "changes": items,
        "ran_at": datetime.now(timezone.utc).isoformat(),
    }

    if next_token:
        store.set_sync_state(
            key,
            {
                "next_sync_token": next_token,
                "last_ran_at": result["ran_at"],
                "last_changes_count": result["changes_count"],
            },
        )
    return result


def get_state(calendar_id: str) -> dict:
    return {"calendar_id": calendar_id, "state": store.get_sync_state(_sync_key(calendar_id)) or {}}


def run_sync(calendar_id: str) -> dict:
    api_service = auth.build_service()
    return run_incremental_sync(api_service, calendar_id)


def _auto_sync_loop() -> None:
    _status_update(running=True, started_at=_iso_now(), stopped_at=None, last_error=None)

    while not _sync_stop_event.is_set():
        _status_update(last_started_at=_iso_now(), last_calendar_id=config.API_DEFAULT_CAL_ID)
        try:
            api_service = auth.build_service()
            result = run_incremental_sync(api_service, config.API_DEFAULT_CAL_ID)
            now = _iso_now()
            _status_update(
                last_finished_at=now,
                last_success_at=now,
                last_error=None,
                last_changes_count=result.get("changes_count"),
                consecutive_failures=0,
            )
        except Exception as exc:
            status = health_snapshot()
            failures = int(status.get("consecutive_failures") or 0) + 1
            _status_update(
                last_finished_at=_iso_now(),
                last_error=str(exc),
                consecutive_failures=failures,
            )

        delay = _next_delay_seconds()
        _status_update(next_run_at=datetime.fromtimestamp(time.time() + delay, timezone.utc).isoformat())
        if _sync_stop_event.wait(delay):
            break

    _status_update(running=False, stopped_at=_iso_now(), next_run_at=None)


def start_worker() -> None:
    global _sync_thread
    if not config.AUTO_SYNC_ENABLED:
        _status_update(
            enabled=False,
            running=False,
            last_error="Auto-sync disabled by CALENDAR_AUTO_SYNC_ENABLED",
        )
        return

    if _sync_thread and _sync_thread.is_alive():
        return

    _sync_stop_event.clear()
    _status_update(enabled=True, last_error=None)
    _sync_thread = threading.Thread(target=_auto_sync_loop, name="calendar-auto-sync", daemon=True)
    _sync_thread.start()


def stop_worker() -> None:
    if not _sync_thread:
        return
    _sync_stop_event.set()
    _sync_thread.join(timeout=5)
