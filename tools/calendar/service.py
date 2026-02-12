from datetime import datetime, timezone
import json

from fastapi import HTTPException

from tools.calendar import google_api


def _event_payload(event: dict) -> dict:
    payload = {
        "summary": event.get("summary"),
        "description": event.get("description"),
        "location": event.get("location"),
        "start": event.get("start"),
        "end": event.get("end"),
        "attendees": event.get("attendees"),
        "reminders": event.get("reminders"),
        "transparency": event.get("transparency"),
    }
    return {k: v for k, v in payload.items() if v is not None}


def _raise_google_http_error(err: Exception) -> None:
    status = int(getattr(err, "status_code", 500) or 500)
    reason = str(err)
    content = getattr(err, "content", None)
    if content:
        try:
            data = json.loads(content.decode("utf-8") if isinstance(content, (bytes, bytearray)) else str(content))
            reason = data.get("error", {}).get("message") or reason
        except Exception:
            pass
    raise HTTPException(status_code=status, detail=f"Google Calendar API error: {reason}")


def list_events(api_service, calendar_id: str, max_results: int, time_min: str | None, time_max: str | None, q: str | None) -> dict:
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        response = (
            api_service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min or now_iso,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
                q=q,
            )
            .execute()
        )
    except google_api.HttpError as err:
        _raise_google_http_error(err)
    items = response.get("items", [])
    return {"calendar_id": calendar_id, "count": len(items), "events": items}


def create_event(api_service, calendar_id: str, payload: dict) -> dict:
    if not payload.get("start") or not payload.get("end"):
        raise HTTPException(status_code=400, detail="Event requires start and end fields.")

    try:
        created = (
            api_service.events()
            .insert(calendarId=calendar_id, body=_event_payload(payload))
            .execute()
        )
    except google_api.HttpError as err:
        _raise_google_http_error(err)
    return {"calendar_id": calendar_id, "event": created}


def update_event(api_service, calendar_id: str, event_id: str, payload: dict) -> dict:
    try:
        updated = (
            api_service.events()
            .patch(calendarId=calendar_id, eventId=event_id, body=_event_payload(payload))
            .execute()
        )
    except google_api.HttpError as err:
        _raise_google_http_error(err)
    return {"calendar_id": calendar_id, "event": updated}


def delete_event(api_service, calendar_id: str, event_id: str) -> dict:
    try:
        api_service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    except google_api.HttpError as err:
        _raise_google_http_error(err)
    return {"calendar_id": calendar_id, "deleted": True, "event_id": event_id}


def list_calendars(api_service) -> dict:
    response = api_service.calendarList().list(maxResults=250).execute()
    items = response.get("items", [])
    slim = [
        {
            "id": item.get("id"),
            "summary": item.get("summary"),
            "primary": item.get("primary", False),
            "timeZone": item.get("timeZone"),
            "accessRole": item.get("accessRole"),
        }
        for item in items
    ]
    return {"count": len(slim), "calendars": slim}
