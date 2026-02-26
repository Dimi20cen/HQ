import sys
from pathlib import Path

from fastapi import Query
from fastapi.responses import RedirectResponse

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from tools.sdk.base_tool import BaseTool

tool = BaseTool(__file__)

from tools.calendar import auth, config, service, store, sync, widget
from tools.calendar.schemas import EventCreateRequest, EventUpdateRequest


@tool.app.get("/auth/status")
def auth_status():
    return auth.auth_status(sync.health_snapshot())


@tool.app.get("/auth/start")
def auth_start(format: str | None = Query(default=None)):
    result = auth.auth_start()
    if (format or "").strip().lower() == "json":
        return result
    return RedirectResponse(url=result["auth_url"], status_code=302)


@tool.app.get("/auth/callback")
def auth_callback(code: str = Query(...), state: str = Query(...)):
    return auth.auth_callback(code=code, state=state)


@tool.app.post("/auth/disconnect")
def auth_disconnect():
    return auth.auth_disconnect()


@tool.app.get("/events")
def list_events(
    calendar_id: str = Query(config.API_DEFAULT_CAL_ID),
    max_results: int = Query(20, ge=1, le=250),
    time_min: str | None = None,
    time_max: str | None = None,
    q: str | None = None,
):
    api_service = auth.build_service()
    return service.list_events(
        api_service=api_service,
        calendar_id=calendar_id,
        max_results=max_results,
        time_min=time_min,
        time_max=time_max,
        q=q,
    )


@tool.app.post("/events")
async def create_event(request: EventCreateRequest, calendar_id: str = Query(config.API_DEFAULT_CAL_ID)):
    api_service = auth.build_service()
    payload = request.model_dump(exclude_none=True)
    return service.create_event(api_service=api_service, calendar_id=calendar_id, payload=payload)


@tool.app.patch("/events/{event_id}")
async def update_event(event_id: str, request: EventUpdateRequest, calendar_id: str = Query(config.API_DEFAULT_CAL_ID)):
    api_service = auth.build_service()
    payload = request.model_dump(exclude_none=True)
    return service.update_event(api_service=api_service, calendar_id=calendar_id, event_id=event_id, payload=payload)


@tool.app.delete("/events/{event_id}")
def delete_event(event_id: str, calendar_id: str = Query(config.API_DEFAULT_CAL_ID)):
    api_service = auth.build_service()
    return service.delete_event(api_service=api_service, calendar_id=calendar_id, event_id=event_id)


@tool.app.get("/calendars")
def list_calendars():
    api_service = auth.build_service()
    return service.list_calendars(api_service=api_service)


@tool.app.get("/sync/state")
def get_sync_state(calendar_id: str = Query(config.API_DEFAULT_CAL_ID)):
    return sync.get_state(calendar_id=calendar_id)


@tool.app.post("/sync/run")
def run_sync(calendar_id: str = Query(config.API_DEFAULT_CAL_ID)):
    return sync.run_sync(calendar_id=calendar_id)


@tool.app.get("/sync/health")
def sync_health():
    return sync.health_snapshot()


def widget_html():
    return widget.widget_html(config.CAL_URL)


tool.add_widget_route(widget_html)


def _startup():
    store.init_db()
    sync.start_worker()


def _shutdown():
    sync.stop_worker()


tool.set_startup_hook(_startup)
tool.set_shutdown_hook(_shutdown)


if __name__ == "__main__":
    tool.run()
