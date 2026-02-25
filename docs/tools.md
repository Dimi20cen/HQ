# Tools
read_when: creating or editing tools

Structure
- `tools/<name>/tool.json` tool manifest
- `tools/<name>/<entry>` entry point (file in tool.json)
- `tools/sdk/base_tool.py` shared FastAPI wrapper

Required `tool.json` fields
- `name`: tool id (used for DB + API routes; keep URL-safe)
- `port`: tool HTTP port

Common fields (defaults)
- `entry_point`: entry script (default `main.py`)
- `runtime`: command used to launch (default `python`; uses controller's interpreter)
- `title`: dashboard label (default from `name`)
- `version`: default `0.1.0`
- `auto_start`: controller auto-launch (default `false`)

Optional `tool.json` fields
- `key`: legacy/folder id (not used by controller)
- `description`: freeform
- `runtime_args`: list of args before entry point (ex: `["--loader","tsx"]`)
- `args`: list of args after entry point

Tool API conventions (when using `BaseTool`)
- `/manifest` returns tool.json
- `/health` returns `{status, tool}`
- `/widget` for small UI (register via `add_widget_route`)

Create a tool
- `python create_tool.py "My Tool" --port 30001`
- Edit `tools/<name>/main.py`
- Restart controller to re-scan

Notes
- `create_tool.py` defaults `auto_start=true`; edit `tool.json` if needed.
- `BaseTool` loads `.env` from the repo root via python-dotenv.
