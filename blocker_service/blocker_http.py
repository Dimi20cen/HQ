import sys
import json
import uvicorn
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

# Import your existing core service
from blocker_service import BlockerService

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
service = BlockerService(config_path=str(BASE_DIR / "config.json"))

# Start the background thread on launch
@app.on_event("startup")
def startup_event():
    service.start()

# --- API Routes ---

@app.get("/status")
def status():
    return service.get_status()

@app.post("/start")
def start():
    service.start()
    return {"started": True}

@app.post("/stop")
def stop():
    service.stop()
    return {"stopped": True}

@app.post("/reload")
def reload_config():
    service.reload_config()
    return {"reloaded": True}

@app.post("/update-config")
async def update_config(request: Request):
    try:
        data = await request.json()
        service.update_config(data)
        return {"updated": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

# --- Widget UI ---

@app.get("/widget", response_class=HTMLResponse)
def widget():
    # Load current config for the UI
    try:
        with open(service.core.config_path, "r") as f:
            config = json.load(f)
            first_window = config.get("blocked_windows", [{}])[0]
            current_start = first_window.get("start", "09:00")
            current_end = first_window.get("end", "17:00")
            current_procs = "\n".join(first_window.get("processes", []))
    except Exception:
        current_start, current_end, current_procs = "09:00", "17:00", ""

    # Note: Double curly braces {{ }} needed for CSS/JS to escape Python f-strings
    html = f"""
    <!DOCTYPE html>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: sans-serif; padding: 10px; margin: 0;
            font-size: 12px; background: #fff; color: #222;
            overflow-x: hidden;
        }}
        .row {{ display: flex; gap: 6px; margin-bottom: 6px; width: 100%; }}
        input, textarea, button {{
            font-size: 12px; border: 1px solid #ccc;
            border-radius: 2px; background: #fafafa; padding: 4px;
        }}
        .time-input {{ flex: 1; min-width: 0; }}
        button {{ padding: 4px 10px; cursor: pointer; background: #f2f2f2; }}
        button:hover {{ background: #e6e6e6; }}
        textarea {{ width: 100%; height: 70px; resize: vertical; font-family: monospace; }}
    </style>

    <div class="row">
        <input class="time-input" id="start" value="{current_start}" placeholder="Start">
        <input class="time-input" id="end" value="{current_end}" placeholder="End">
        <button onclick="saveConfig(event)">Save</button>
    </div>
    <textarea id="procs" placeholder="blocked.exe">{current_procs}</textarea>

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

if __name__ == "__main__":
    PORT = 9001
    print(f"Blocker service running on http://127.0.0.1:{PORT}")
    try:
        uvicorn.run(app, host="127.0.0.1", port=PORT)
    except OSError:
        print(f"CRITICAL: Port {PORT} is already in use!")
        sys.exit(1)
