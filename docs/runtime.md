# Runtime
read_when: running HQ locally

Setup (first time)
- `python setup.py` (creates `.venv`, installs root + tool deps)
- `./start.sh` (creates `.venv`, installs root deps only)
- Windows: run `python setup.py`, then `start.bat`
- Manual: `python3 -m venv .venv` then `pip install -r requirements.txt` (+ tool deps as needed)

Start controller
- `python run.py` (uses `.venv` python; auto-reload)
- Serves on `http://127.0.0.1:8000`

Start a tool directly
- `python tools/<tool>/main.py`
- For node tools: `node tools/<tool>/<entry_point>`

Logs
- Tool stdout/stderr: `logs/<tool>.out.log` and `logs/<tool>.err.log`

Ports
- Controller default: 8000
- Tool ports: set per `tool.json`

Gate
- `./bin/gate` (compileall; pytest only if tests exist + installed)

Docker (LAN deploy)
- Requires Docker Engine + Compose v2.
- Uses `docker-compose.yml` in repo root.
- Set bind values in `.env`:
  - `LAN_BIND_IP=192.168.1.119`
  - `LAN_BIND_PORT=8000`
- Start:
  - `docker compose up -d --build`
- Verify:
  - `curl http://127.0.0.1:8000/tools`
  - `curl http://192.168.1.119:8000/tools`
- Persistent runtime data:
  - `runtime/controller/tools.db`
  - `runtime/tools/calendar/calendar.db`
  - `runtime/tools/jobber/jobs.db`
  - Future tools: `runtime/tools/<tool_name>/...` (auto-created by tool code)
