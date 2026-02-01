# Overview
read_when: need a mental model of HQ

HQ is a local tool hub. It discovers tools under `tools/`, launches them, and provides a dashboard + proxy API.

Core parts
- Controller: FastAPI app in `controller/` that scans tools, manages processes, and proxies requests.
- Tools: one folder per tool under `tools/`, each with `tool.json` + `main.py`.
- BaseTool: shared FastAPI wrapper in `tools/sdk/base_tool.py` for manifest, CORS, and widget.
- Storage: controller uses SQLite at `controller/tools.db`.

Data flow
- Controller scans `tools/` on startup, registers tool metadata.
- ProcessManager starts/stops tool processes, tracks PID/status.
- Dashboard reads controller API and links to tool widgets.
