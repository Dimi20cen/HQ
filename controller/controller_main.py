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
    update_tool_metadata,
)

from controller.process_manager import ProcessManager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# --- Path Setup ---
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _manifest_path_for_tool(name: str) -> Path:
    return BASE_DIR.parent / "tools" / name / "tool.json"


def _read_tool_manifest(name: str) -> dict | None:
    manifest_path = _manifest_path_for_tool(name)
    if not manifest_path.exists():
        return None
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _write_tool_manifest(name: str, manifest: dict) -> bool:
    manifest_path = _manifest_path_for_tool(name)
    if not manifest_path.exists():
        return False
    try:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
            f.write("\n")
        return True
    except Exception:
        return False


def _get_tool_auto_start(name: str) -> bool:
    manifest = _read_tool_manifest(name)
    if not manifest:
        return False
    return bool(manifest.get("auto_start", False))

def scan_tools():
    """
    Scans tools/ directory for folders with a valid tool.json.
    Returns a list of config dictionaries.
    """
    tools_path = BASE_DIR.parent / "tools"
    discovered = []

    if not tools_path.exists():
        print("Warning: 'tools' directory not found.")
        return []

    for folder in tools_path.iterdir():
        manifest = folder / "tool.json"

        if folder.is_dir() and manifest.exists():
            try:
                with open(manifest, "r") as f:
                    config = json.load(f)

                entry_point = config.get("entry_point") or "main.py"
                entry_path = folder / entry_point

                if not entry_path.exists():
                    print(f"[Discovery] Skipping {folder.name}: missing entry_point {entry_point}")
                    continue
                
                # Critical: Add the path for ProcessManager
                # ProcessManager runs from Root, so path is tools/name/<entry_point>
                config["process_path"] = f"tools/{folder.name}/{entry_point}"
                
                discovered.append(config)
                print(f"[Discovery] Found tool: {config.get('title')} ({config.get('port')})")
            except Exception as e:
                print(f"[Discovery] Error loading {folder.name}: {e}")
    
    return discovered


# -------------------------------------------------------------
# LIFESPAN
# -------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP LOGIC ---
    init_db()
    print("--- Controller Startup ---")

    # 1. DYNAMIC DISCOVERY
    tools_config = scan_tools()

    # 2. Sync to Database
    for t in tools_config:
        name = t["name"]
        process_path = t["process_path"]
        port = t["port"]
        has_widget = t.get("has_widget", False)

        db_tool = get_tool_by_name(name)
        if not db_tool:
            add_tool(name, process_path, port, has_widget)
        else:
            if (
                db_tool.process_path != process_path
                or db_tool.port != port
                or db_tool.has_widget != has_widget
            ):
                update_tool_metadata(
                    name,
                    process_path=process_path,
                    port=port,
                    has_widget=has_widget,
                )

    # --- 2.5 Reconcile DB with Reality (The Orphan Check) ---
    all_tools = list_tools()
    print(f"[Check] Verifying {len(all_tools)} tools in database...")

    for tool in all_tools:
        name = tool["name"]
        pid = tool["pid"]
        
        if pid:
            if psutil.pid_exists(pid):
                try:
                    proc = psutil.Process(pid)
                    # Optional: Check if the process name looks python-ish
                    if "python" in proc.name().lower() or "exe" in proc.name().lower():
                         print(f"[Alive] Re-adopted '{name}' on PID {pid}.")
                    else:
                        # PID exists but it's not our tool (PID reuse)
                        update_tool_pid(name, None)
                        update_tool_status(name, "stopped")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
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
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# -------------------------------------------------------------
# Core Controller Routes
# -------------------------------------------------------------
@app.get("/dashboard")
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/tools")
def get_tools():
    tools = list_tools()
    for tool in tools:
        tool["auto_start"] = _get_tool_auto_start(tool["name"])
    return {"tools": tools}

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

@app.get("/tools/status-all")
def get_all_tool_statuses():
    """Checks the status of all tools in one go."""
    all_tools = list_tools()
    results = []
    
    for tool in all_tools:
        # Re-use the logic from ProcessManager without the HTTP overhead
        alive_check = ProcessManager.is_alive(tool["name"])
        results.append({
            "name": tool["name"],
            "alive": alive_check["alive"],
            "pid": alive_check.get("pid"),
            "port": tool["port"] # Include port so UI doesn't need to look it up
        })
        
    return {"tools": results}

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


@app.post("/tools/{name}/auto-start")
def set_tool_auto_start(name: str, payload: dict):
    tool = get_tool_by_name(name)
    if not tool:
        return JSONResponse(status_code=404, content={"detail": "Tool not found."})

    enabled = payload.get("enabled")
    if not isinstance(enabled, bool):
        return JSONResponse(status_code=400, content={"detail": "Missing boolean 'enabled' field."})

    manifest = _read_tool_manifest(name)
    if manifest is None:
        return JSONResponse(status_code=404, content={"detail": "tool.json not found."})

    manifest["auto_start"] = enabled
    if not _write_tool_manifest(name, manifest):
        return JSONResponse(status_code=500, content={"detail": "Failed to update tool.json."})

    return {"name": name, "auto_start": enabled}


def _rewrite_widget_content(content: bytes, tool_name: str, content_type: str) -> bytes:
    """Rewrite absolute root paths in proxied widget HTML/JS to stay under controller proxy."""
    if "text/html" not in content_type and "javascript" not in content_type:
        return content

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return content

    prefix = f"/proxy/{tool_name}/"
    replacements = [
        ('src="/', f'src="{prefix}'),
        ("src='/", f"src='{prefix}"),
        ('href="/', f'href="{prefix}'),
        ("href='/", f"href='{prefix}"),
        ('action="/', f'action="{prefix}'),
        ("action='/", f"action='{prefix}"),
        ('fetch("/', f'fetch("{prefix}'),
        ("fetch('/", f"fetch('{prefix}"),
    ]

    for before, after in replacements:
        text = text.replace(before, after)

    return text.encode("utf-8")


@app.api_route("/proxy/{name}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_tool_http(name: str, path: str, request: Request):
    tool = get_tool_by_name(name)
    if not tool:
        return JSONResponse(status_code=404, content={"detail": "Tool not found."})

    if not tool.port:
        return JSONResponse(status_code=400, content={"detail": "No port assigned."})

    target_url = f"http://127.0.0.1:{tool.port}/{path}"
    body = await request.body()

    headers = {}
    content_type = request.headers.get("content-type")
    if content_type:
        headers["content-type"] = content_type

    try:
        resp = requests.request(
            method=request.method,
            url=target_url,
            params=request.query_params,
            data=body if body else None,
            headers=headers,
            timeout=30,
            allow_redirects=False,
        )
    except requests.exceptions.ConnectionError:
        return JSONResponse(
            status_code=502,
            content={"detail": f"Tool '{name}' unreachable on port {tool.port}."},
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

    response_content_type = resp.headers.get("content-type", "")
    payload = _rewrite_widget_content(resp.content, name, response_content_type)

    out_headers = {}
    for h in ("content-type", "cache-control", "location"):
        value = resp.headers.get(h)
        if value:
            out_headers[h] = value

    return Response(content=payload, status_code=resp.status_code, headers=out_headers)

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
