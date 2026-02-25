import sys
import json
from pathlib import Path
from fastapi import Request
from fastapi.responses import JSONResponse

# 1. SETUP PATHS
# We need to add the project root to sys.path so we can import 'tools.sdk'
# Current file: tools/blocker/main.py -> Root is 3 levels up
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# We also ensure the current folder is in path so we can import sibling files
sys.path.append(str(Path(__file__).parent))

# 2. IMPORTS
from tools.sdk.base_tool import BaseTool
from blocker_service import BlockerService

# 3. INITIALIZE TOOL
# This loads tool.json automatically to get name, port, etc.
tool = BaseTool(__file__)

# 4. INITIALIZE SERVICE
# We use tool.root_dir to guarantee we find config.json inside tools/blocker/
service = BlockerService(config_path=str(tool.root_dir / "config.json"))

# 5. LIFECYCLE HOOKS
tool.set_startup_hook(service.start)
tool.set_shutdown_hook(service.stop)

# --- API Routes ---

@tool.app.get("/status")
def status():
    return service.get_status()

@tool.app.post("/start")
def start():
    service.start()
    return {"started": True}

@tool.app.post("/stop")
def stop():
    service.stop()
    return {"stopped": True}

@tool.app.post("/reload")
def reload_config():
    service.reload_config()
    return {"reloaded": True}

@tool.app.post("/update-config")
async def update_config(request: Request):
    try:
        data = await request.json()
        service.update_config(data)
        return {"updated": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

# --- Widget UI ---

def widget_generator():
    """Generates the HTML for the dashboard widget."""
    # Load current config for the UI state
    try:
        with open(service.core.config_path, "r") as f:
            config = json.load(f)
            first_window = config.get("blocked_windows", [{}])[0]
            current_start = first_window.get("start", "09:00")
            current_end = first_window.get("end", "17:00")
            current_procs = "\n".join(first_window.get("processes", []))
    except Exception:
        current_start, current_end, current_procs = "09:00", "17:00", ""

    html = f"""
    <!DOCTYPE html>
    <style>
        :root {{
            --bg: #fdf5fb;
            --surface: #fff9fd;
            --text: #372f56;
            --muted: #756d95;
            --border: rgba(143, 119, 171, 0.28);
            --control-bg: #ffffff;
            --control-bg-hover: #f2edf7;
            --status-info: #7d8cc3;
        }}
        * {{ box-sizing: border-box; }}
        html, body {{ height: 100%; }}
        body {{
            font-family: "Manrope", "Space Grotesk", "Segoe UI", sans-serif; padding: 0; margin: 0;
            font-size: 12px; background: var(--bg); color: var(--text);
            overflow-x: hidden;
        }}
        .widget-root {{
            width: 100%;
            height: 100%;
            padding: 8px 8px 10px 8px;
            background: var(--surface);
        }}
        .row {{ display: flex; gap: 6px; margin-bottom: 6px; width: 100%; }}
        input, textarea, button {{
            font-size: 12px; border: 1px solid var(--border);
            border-radius: 6px; background: var(--control-bg); padding: 4px;
            color: var(--text);
        }}
        .time-input {{ flex: 1; min-width: 0; }}
        button {{
            padding: 4px 10px;
            cursor: pointer;
            background: var(--control-bg);
            border-color: var(--border);
            font-weight: 600;
        }}
        button:hover {{ background: var(--control-bg-hover); }}
        textarea {{ width: 100%; height: 70px; resize: vertical; font-family: monospace; }}
    </style>

    <div class="widget-root">
        <div class="row">
            <input class="time-input" id="start" value="{current_start}" placeholder="Start">
            <input class="time-input" id="end" value="{current_end}" placeholder="End">
            <button onclick="saveConfig(event)">Save</button>
        </div>
        <textarea id="procs" placeholder="blocked.exe">{current_procs}</textarea>
    </div>

    <script>
        async function saveConfig(event) {{
            const start = document.getElementById('start').value.trim();
            const end = document.getElementById('end').value.trim();
            const rawProcs = document.getElementById('procs').value;

            const processes = rawProcs.split('\\n')
                .map(p => p.trim())
                .filter(Boolean);

            const newConfig = {{
                "check_interval_seconds": 3,
                "blocked_windows": [{{
                    "start": start,
                    "end": end,
                    "processes": processes
                }}]
            }};

            const btn = event.target;
            const original = btn.innerText;
            btn.innerText = "Saving...";

            try {{
                const res = await fetch('/update-config', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(newConfig)
                }});
                btn.innerText = res.ok ? "Saved" : "Error";
            }} catch {{
                btn.innerText = "Error";
            }}
            setTimeout(() => btn.innerText = original, 1000);
        }}
    </script>
    """
    return html

# Register the widget using the SDK helper
tool.add_widget_route(widget_generator)

# 6. RUN
if __name__ == "__main__":
    tool.run()
