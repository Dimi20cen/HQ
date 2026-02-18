## 2026-02-18
- Summary: Added containerized LAN deployment for HQ using Docker Compose, with persistent runtime SQLite paths for controller/calendar/jobber.
- Affected files: `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `controller/db.py`, `tools/calendar/config.py`, `tools/jobber/main.py`, `docs/runtime.md`
- Migration notes: Create/update `.env` with `LAN_BIND_IP` and `LAN_BIND_PORT`, then run `docker compose up -d --build`.
- Validation status: Not run in this workspace (container build/runtime should be validated on target server).

## 2026-02-15
- Summary: Implemented `Meditator` timer widget with selectable duration, optional background music, and configurable end-of-session sound behavior.
- Affected files: `tools/meditator/tool.json`, `tools/meditator/main.py`, `tools/meditator/requirements.txt`
- Migration notes: None.
- Validation status: `python -m py_compile tools/meditator/main.py` passed.
