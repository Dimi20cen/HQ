import json
import requests
from pathlib import Path

from controller.db import (
    init_db,
    list_tools,
    add_tool,
    get_tool_by_name,
    update_tool_pid,
)

from controller.process_manager import ProcessManager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

# --- 1. Path Fix for Templates ---
# This ensures the app finds "dashboard.html" regardless of where you run it from.
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(
    title="Utility Controller",
    description="Controller API for managing local utility services.",
    version="0.2.0",
)

# -------------------------------------------------------------
# Startup & Registration
# -------------------------------------------------------------
@app.on_event("startup")
def startup_event():
    init_db()
    print("Database initialized.")

    # Locate tools.json relative to the project root
    # controller_main.py is in /controller, so we go up one level
    tools_file = BASE_DIR.parent / "tools.json"
    
    if tools_file.exists():
        with open(tools_file, "r") as f:
            tools = json.load(f)

        for t in tools:
            name = t["name"]
            process_path = t["process_path"]
            port = t["port"]

            db_tool = get_tool_by_name(name)
            if not db_tool:
                add_tool(name, process_path, port)
                print(f"Registered tool from JSON: {name}")

# -------------------------------------------------------------
# Core Controller Routes
# -------------------------------------------------------------
@app.get("/dashboard")
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/tools")
def get_tools():
    return {"tools": list_tools()}

@app.post("/tools/register")
def register_tool(payload: dict):
    """
    Manually register a tool via API.
    """
    name = payload.get("name")
    process_path = payload.get("process_path")
    port = payload.get("port")

    if not name or not process_path or not port:
        return JSONResponse(
            status_code=400,
            content={"detail": "Missing name, process_path, or port."}
        )

    existing = get_tool_by_name(name)
    if existing:
        return JSONResponse(
            status_code=400,
            content={"detail": f"Tool '{name}' already registered."}
        )

    tool = add_tool(name, process_path, port)
    return {"registered": tool.as_dict()}

# -------------------------------------------------------------
# Process Management Routes (Launch/Kill)
# -------------------------------------------------------------
@app.post("/tools/{name}/launch")
def launch_tool(name: str):
    result = ProcessManager.launch_tool(name)
    if "error" in result:
        return JSONResponse(status_code=400, content=result)
    return result

@app.post("/tools/{name}/kill")
def kill_tool(name: str):
    result = ProcessManager.kill_tool(name)
    if "error" in result:
        return JSONResponse(status_code=400, content=result)
    return result

@app.get("/tools/{name}/alive")
def tool_alive(name: str):
    return ProcessManager.is_alive(name)

# -------------------------------------------------------------
# NEW: Generic Tool Proxy
# -------------------------------------------------------------
# This replaces the hardcoded "BlockerClient".
# It blindly forwards commands to whichever tool you specify in the URL.
# Example: POST /api/tools/blocker/start  -> http://127.0.0.1:9001/start
# Example: POST /api/tools/logger/status -> http://127.0.0.1:9002/status

@app.api_route("/api/tools/{name}/{action}", methods=["GET", "POST"])
async def proxy_tool_command(name: str, action: str, request: Request):
    """
    Generic proxy that forwards requests to the tool's internal port.
    """
    # 1. Look up the tool in the DB to find its port
    tool = get_tool_by_name(name)
    if not tool:
        return JSONResponse(status_code=404, content={"detail": f"Tool '{name}' not found."})
    
    if not tool.port:
        return JSONResponse(status_code=400, content={"detail": f"Tool '{name}' has no port assigned."})

    # 2. Build the destination URL
    target_url = f"http://127.0.0.1:{tool.port}/{action}"

    # 3. Capture the JSON body if this is a POST request (e.g. for config updates)
    json_body = None
    if request.method == "POST":
        try:
            json_body = await request.json()
        except Exception:
            json_body = None

    # 4. Forward the request
    try:
        if request.method == "GET":
            # Forward GET
            resp = requests.get(target_url, timeout=5)
        else:
            # Forward POST
            resp = requests.post(target_url, json=json_body, timeout=5)
        
        # Return the tool's response exactly as is
        return resp.json()

    except requests.exceptions.ConnectionError:
        return JSONResponse(
            status_code=502, 
            content={"detail": f"Tool '{name}' is unreachable on port {tool.port}. Is it running?"}
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Proxy error: {str(e)}"})
