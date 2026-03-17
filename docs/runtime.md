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
- Project registry: `runtime/projects/projects.json`
- Project export: `runtime/projects/projects.generated.json`

Ports
- Controller default: 8000
- Tool ports: set per `tool.json`

Gate
- `./bin/gate` (compileall; pytest only if tests exist + installed)

Docker (LAN deploy)
- Requires Docker Engine + Compose v2.
- Uses `docker-compose.yml` in repo root.
- Expose only controller port `8000`; widget traffic is proxied through controller.
- Keep a separate local `.env` on each machine (do not sync `.env` in git).
- Server `.env` notes:
  - Keep `LAN_BIND_IP=0.0.0.0`
  - Set Google OAuth values in server `.env`
  - Use a server-reachable redirect URI (not `127.0.0.1`), e.g. `http://<server-host>:9010/auth/callback`
  - To let `Export Catalog` sync portfolio data from the container, set:
    - `HQ_PORTFOLIO_REPO_DIR=/srv/stacks/dimy.dev`
    - `HQ_PORTFOLIO_EXPORT_PATH=/portfolio-repo/data/projects.generated.json`
    - `HQ_PORTFOLIO_BRANCH=main`
- Start:
  - `docker compose up -d --build`
- Verify:
  - `curl http://127.0.0.1:8000/tools`
  - `curl http://192.168.1.119:8000/tools`

Database/storage paths
- Local defaults (without env overrides):
  - Controller DB: `controller/tools.db`
  - Calendar DB: `tools/calendar/calendar.db`
  - Jobber DB: `tools/jobber/jobs.db`
- Docker Compose runtime paths (configured by env):
  - `runtime/controller/tools.db`
  - `runtime/tools/calendar/calendar.db`
  - `runtime/tools/jobber/jobs.db`
- Key env overrides:
  - `CONTROLLER_DB_PATH`
  - `CALENDAR_DB_PATH`
  - `JOBBER_DB_PATH`
  - `HQ_PROJECTS_PATH`
  - `HQ_PROJECTS_EXPORT_PATH`
  - `HQ_PORTFOLIO_EXPORT_PATH`
  - `HQ_PORTFOLIO_REPO_DIR`
  - `HQ_PORTFOLIO_BRANCH`

Project catalog export sync
- `POST /projects/export` always writes the sanitized HQ export JSON.
- If `HQ_PORTFOLIO_EXPORT_PATH` is set, the same export is also copied into the portfolio repo.
- Without that env var, HQ auto-detects a sibling local repo at `../dimy.dev/data/projects.generated.json` when present.
- In Docker, `HQ_PORTFOLIO_REPO_DIR` should mount the host portfolio repo into `/portfolio-repo`.
- `POST /projects/publish` assumes that mounted repo is a dedicated publish clone with working GitHub push auth.
