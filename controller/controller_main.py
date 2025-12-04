import json
import requests
import psutil
from pathlib import Path
from contextlib import asynccontextmanager

from controller.db import (
    init_db,
    list_tools,
    add_tool,
    get_tool_by_name,
    update_tool_pid,
    update_tool_status,
)

from controller.process_manager import ProcessManager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

# --- Path Setup ---
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# -------------------------------------------------------------
# LIFESPAN
# -------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP LOGIC ---
    init_db()
    print("--- Controller Startup ---")

    # 1. Sync tools.json to Database
    tools_file = BASE_DIR.parent / "tools.json"
    tools_config = []
    
    if tools_file.exists():
        with open(tools_file, "r") as f:
            tools_config = json.load(f)

        for t in tools_config:
            name = t["name"]
            process_path = t["process_path"]
            port = t["port"]
            has_widget = t.get("has_widget", False)

            db_tool = get_tool_by_name(name)
            if not db_tool:
                # New tool found in JSON
                add_tool(name, process_path, port, has_widget)
                print(f"[Sync] Registered new tool: {name}")
            else:
                # OPTIONAL: You can update existing tools here if JSON changed
                pass

    # 2. Reconcile DB with Reality (The Orphan Check)
    all_tools = list_tools()
    print(f"[Check] Verifying {len(all_tools)} tools in database...")

    for tool in all_tools:
        name = tool["name"]
        pid = tool["pid"]
        
        if pid:
            if psutil.pid_exists(pid):
                try:
                    proc = psutil.Process(pid)
                    proc_name = proc.name().lower()
                    
                    if "python" in proc_name or "exe" in proc_name:
                        print(f"[Alive] Re-adopted '{name}' on PID {pid}.")
                    else:
                        print(f"[Warn] PID {pid} exists but mismatches. Marking stopped.")
                        update_tool_pid(name, None)
                        update_tool_status(name, "stopped")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    print(f"[Dead] '{name}' PID {pid} is gone. Marking stopped.")
                    update_tool_pid(name, None)
                    update_tool_status(name, "stopped")
            else:
                print(f"[Dead] '{name}' PID {pid} not found. Marking stopped.")
                update_tool_pid(name, None)
                update_tool_status(name, "stopped")

    # 3. Auto-Start Logic
    print("[Auto-Start] Checking for tools to launch...")
    for t in tools_config:
        if t.get("auto_start", False):
            db_tool = get_tool_by_name(t["name"])
            if db_tool and db_tool.pid:
                continue # Already running
            
            print(f"[Auto-Start] Launching {t['name']}...")
            ProcessManager.launch_tool(t["name"])

    print("--- Startup Complete ---\n")

    # --- YIELD CONTROL TO APP ---
    yield

    # --- SHUTDOWN LOGIC ---
    print("--- Controller Shutdown ---")


# -------------------------------------------------------------
# APP DEFINITION
# -------------------------------------------------------------
app = FastAPI(
    title="Utility Controller",
    description="Controller API for managing local utility services.",
    version="0.2.0",
    lifespan=lifespan
)

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
    name = payload.get("name")
    process_path = payload.get("process_path")
    port = payload.get("port")

    if not name or not process_path or not port:
        return JSONResponse(status_code=400, content={"detail": "Missing fields."})

    existing = get_tool_by_name(name)
    if existing:
        return JSONResponse(status_code=400, content={"detail": "Tool exists."})

    tool = add_tool(name, process_path, port)
    return {"registered": tool.as_dict()}

# -------------------------------------------------------------
# Process Management Routes
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
# Generic Tool Proxy
# -------------------------------------------------------------
@app.api_route("/api/tools/{name}/{action}", methods=["GET", "POST"])
async def proxy_tool_command(name: str, action: str, request: Request):
    tool = get_tool_by_name(name)
    if not tool:
        return JSONResponse(status_code=404, content={"detail": "Tool not found."})
    
    if not tool.port:
        return JSONResponse(status_code=400, content={"detail": "No port assigned."})

    target_url = f"http://127.0.0.1:{tool.port}/{action}"

    json_body = None
    if request.method == "POST":
        try:
            json_body = await request.json()
        except Exception:
            json_body = None

    try:
        if request.method == "GET":
            resp = requests.get(target_url, timeout=5)
        else:
            resp = requests.post(target_url, json=json_body, timeout=5)
        return resp.json()

    except requests.exceptions.ConnectionError:
        return JSONResponse(
            status_code=502, 
            content={"detail": f"Tool '{name}' unreachable on port {tool.port}."}
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})
