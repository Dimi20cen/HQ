## 2026-02-25
- Summary: Added per-tool settings actions in dashboard menus (hide/unhide, auto-start toggle, start/stop toggle), and added a controller API to persist `auto_start` in each tool manifest.
- Affected files: `controller/controller_main.py`, `controller/static/dashboard.js`, `controller/static/dashboard.css`, `controller/templates/dashboard.html`, `docs/controller.md`
- Migration notes: None.
- Validation status: `node --check controller/static/dashboard.js` and `python3 -m py_compile controller/controller_main.py controller/db.py controller/process_manager.py` passed.

## 2026-02-18
- Summary: Added containerized LAN deployment for HQ using Docker Compose, and switched tool state to a single runtime root (`runtime/tools/<tool_name>`) with auto-created state directories.
- Affected files: `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `controller/db.py`, `controller/controller_main.py`, `controller/static/dashboard.js`, `tools/calendar/config.py`, `tools/calendar/store.py`, `tools/jobber/main.py`, `docs/runtime.md`
- Migration notes: Create/update `.env` with `LAN_BIND_IP` and `LAN_BIND_PORT`, then run `docker compose up -d --build`.
- Validation status: `python -m py_compile controller/controller_main.py controller/db.py tools/calendar/config.py tools/calendar/store.py tools/jobber/main.py` passed.

## 2026-02-15
- Summary: Implemented `Meditator` timer widget with selectable duration, optional background music, and configurable end-of-session sound behavior.
- Affected files: `tools/meditator/tool.json`, `tools/meditator/main.py`, `tools/meditator/requirements.txt`
- Migration notes: None.
- Validation status: `python -m py_compile tools/meditator/main.py` passed.
