from datetime import datetime, timezone

from fastapi import HTTPException


def _event_payload(event: dict) -> dict:
    return {
        "summary": event.get("summary"),
        "description": event.get("description"),
        "location": event.get("location"),
        "start": event.get("start"),
        "end": event.get("end"),
        "attendees": event.get("attendees"),
        "reminders": event.get("reminders"),
        "transparency": event.get("transparency"),
    }


def list_events(api_service, calendar_id: str, max_results: int, time_min: str | None, time_max: str | None, q: str | None) -> dict:
    now_iso = datetime.now(timezone.utc).isoformat()
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
    items = response.get("items", [])
    return {"calendar_id": calendar_id, "count": len(items), "events": items}


def create_event(api_service, calendar_id: str, payload: dict) -> dict:
    if not payload.get("start") or not payload.get("end"):
        raise HTTPException(status_code=400, detail="Event requires start and end fields.")

    created = (
        api_service.events()
        .insert(calendarId=calendar_id, body=_event_payload(payload))
        .execute()
    )
    return {"calendar_id": calendar_id, "event": created}


def update_event(api_service, calendar_id: str, event_id: str, payload: dict) -> dict:
    updated = (
        api_service.events()
        .patch(calendarId=calendar_id, eventId=event_id, body=_event_payload(payload))
        .execute()
    )
    return {"calendar_id": calendar_id, "event": updated}


def delete_event(api_service, calendar_id: str, event_id: str) -> dict:
    api_service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
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
