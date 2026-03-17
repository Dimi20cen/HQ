import json
import sqlite3
import os
import subprocess
import requests
import psutil
from pathlib import Path
from datetime import UTC, date, datetime, timedelta
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
from controller.portfolio_publish import publish_portfolio_catalog
from controller.projects_registry import (
    ProjectValidationError,
    create_project,
    delete_project,
    ensure_projects_store,
    export_projects,
    get_project,
    list_projects,
    update_project,
)

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# --- Path Setup ---
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
PROJECT_ACTION_COMMANDS = {
    "deploy": "deploy_command",
    "start": "start_command",
    "restart": "restart_command",
    "stop": "stop_command",
    "logs": "logs_command",
}
PROJECT_HEALTH_CACHE: dict[str, dict] = {}


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


def _normalize_tool_category(value: str | None) -> str:
    if not isinstance(value, str):
        return "display"
    category = value.strip().lower()
    if category in {"display", "background", "hybrid"}:
        return category
    return "display"


def _jobber_db_path() -> Path:
    configured = os.getenv("JOBBER_DB_PATH")
    if configured:
        return Path(configured)
    return BASE_DIR.parent / "tools" / "jobber" / "jobs.db"


def _job_application_counts(days: int) -> dict:
    safe_days = max(1, min(int(days), 730))
    end_day = date.today()
    start_day = end_day - timedelta(days=safe_days - 1)
    db_path = _jobber_db_path()

    if not db_path.exists():
        return {
            "days": [],
            "range_start": start_day.isoformat(),
            "range_end": end_day.isoformat(),
            "total_count": 0,
            "max_count": 0,
        }

    rows = []
    try:
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                """
                SELECT substr(date_scraped, 1, 10) AS day, COUNT(*) AS count
                FROM jobs
                WHERE date_scraped IS NOT NULL
                  AND date_scraped != ''
                  AND substr(date_scraped, 1, 10) BETWEEN ? AND ?
                GROUP BY day
                ORDER BY day ASC
                """,
                (start_day.isoformat(), end_day.isoformat()),
            ).fetchall()
    except Exception:
        rows = []

    day_counts = []
    max_count = 0
    total_count = 0
    for row in rows:
        day_value = str(row[0] or "")
        count_value = int(row[1] or 0)
        if not day_value:
            continue
        max_count = max(max_count, count_value)
        total_count += count_value
        day_counts.append({"date": day_value, "count": count_value})

    return {
        "days": day_counts,
        "range_start": start_day.isoformat(),
        "range_end": end_day.isoformat(),
        "total_count": total_count,
        "max_count": max_count,
    }


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _check_health_target(label: str, url: str) -> dict:
    if not url:
        return {
            "label": label,
            "url": "",
            "status": "unconfigured",
            "ok": False,
            "http_status": None,
            "checked_at": _now_iso(),
            "detail": "No health URL configured.",
        }

    try:
        response = requests.get(url, timeout=5)
        healthy = 200 <= response.status_code < 400
        return {
            "label": label,
            "url": url,
            "status": "healthy" if healthy else "down",
            "ok": healthy,
            "http_status": response.status_code,
            "checked_at": _now_iso(),
            "detail": f"HTTP {response.status_code}",
        }
    except requests.RequestException as exc:
        return {
            "label": label,
            "url": url,
            "status": "down",
            "ok": False,
            "http_status": None,
            "checked_at": _now_iso(),
            "detail": str(exc),
        }


def _default_health_check(label: str, url: str) -> dict:
    if not url:
        return {
            "label": label,
            "url": "",
            "status": "unconfigured",
            "ok": False,
            "http_status": None,
            "checked_at": _now_iso(),
            "detail": "No health URL configured.",
        }
    return {
        "label": label,
        "url": url,
        "status": "unknown",
        "ok": False,
        "http_status": None,
        "checked_at": "",
        "detail": "Not checked yet.",
    }


def _summarize_health(snapshot: dict) -> str:
    configured = [
        entry["status"]
        for entry in snapshot.values()
        if isinstance(entry, dict) and entry.get("status") != "unconfigured"
    ]
    if not configured:
        return "unconfigured"
    if all(status == "healthy" for status in configured):
        return "healthy"
    if all(status == "unknown" for status in configured):
        return "unknown"
    if any(status == "healthy" for status in configured):
        return "degraded"
    if any(status == "unknown" for status in configured):
        return "unknown"
    return "down"


def _project_health_snapshot(project: dict) -> dict:
    checks = {
        "public": _check_health_target("public", str(project.get("health_public_url") or "")),
        "private": _check_health_target("private", str(project.get("health_private_url") or "")),
    }
    return {
        "slug": project["slug"],
        "checked_at": _now_iso(),
        "summary": _summarize_health(checks),
        "checks": checks,
    }


def _project_health_snapshot_from_cache(project: dict) -> dict:
    cached = PROJECT_HEALTH_CACHE.get(project["slug"])
    if cached:
        return cached
    checks = {
        "public": _default_health_check("public", str(project.get("health_public_url") or "")),
        "private": _default_health_check("private", str(project.get("health_private_url") or "")),
    }
    return {
        "slug": project["slug"],
        "checked_at": "",
        "summary": _summarize_health(checks),
        "checks": checks,
    }


def _dependency_status(snapshot: dict | None) -> str:
    if not snapshot:
        return "unknown"
    return str(snapshot.get("summary") or "unknown")


def _summarize_dependencies(items: list[dict]) -> str:
    if not items:
        return "none"
    statuses = [item["status"] for item in items]
    if any(status == "down" for status in statuses):
        return "down"
    if any(status == "unknown" for status in statuses):
        return "unknown"
    if any(status in {"degraded", "unconfigured"} for status in statuses):
        return "degraded"
    if all(status == "healthy" for status in statuses):
        return "healthy"
    return "degraded"


def _project_dependency_snapshot(project: dict, project_map: dict[str, dict], snapshots: dict[str, dict]) -> dict:
    dependencies = []
    for dependency_slug in project.get("depends_on") or []:
        dependency = project_map.get(dependency_slug)
        snapshot = snapshots.get(dependency_slug)
        dependencies.append(
            {
                "slug": dependency_slug,
                "title": dependency.get("title") if dependency else dependency_slug,
                "status": _dependency_status(snapshot),
                "private_url": dependency.get("private_url") if dependency else "",
            }
        )
    return {
        "summary": _summarize_dependencies(dependencies),
        "items": dependencies,
    }


def _project_ops_summary(health_summary: str, dependency_summary: str) -> str:
    if health_summary == "unknown":
        if dependency_summary in {"down", "degraded"}:
            return "degraded"
        return "unknown"
    if health_summary == "down":
        return "down"
    if health_summary == "degraded":
        return "degraded"
    if health_summary == "unconfigured":
        if dependency_summary in {"healthy", "none"}:
            return "unconfigured"
        if dependency_summary == "unknown":
            return "unknown"
        return "degraded"
    if dependency_summary == "down":
        return "degraded"
    if dependency_summary == "unknown":
        return "unknown"
    if dependency_summary == "degraded":
        return "degraded"
    return health_summary


def _action_runner_url() -> str:
    return str(os.getenv("HQ_ACTION_RUNNER_URL") or "").strip()


def _action_runner_token() -> str:
    return str(os.getenv("HQ_ACTION_RUNNER_TOKEN") or "").strip()


def _projects_with_runtime_state(refresh_health: bool = False) -> list[dict]:
    projects = list_projects()
    project_map = {project["slug"]: project for project in projects}
    if refresh_health:
        snapshots = {}
        for project in projects:
            snapshot = _project_health_snapshot(project)
            PROJECT_HEALTH_CACHE[project["slug"]] = snapshot
            snapshots[project["slug"]] = snapshot
    else:
        snapshots = {project["slug"]: _project_health_snapshot_from_cache(project) for project in projects}
    decorated = []
    for project in projects:
        dependency_snapshot = _project_dependency_snapshot(project, project_map, snapshots)
        health_snapshot = snapshots[project["slug"]]
        decorated.append(
            {
                **project,
                "health_snapshot": health_snapshot,
                "dependency_snapshot": dependency_snapshot,
                "ops_summary": _project_ops_summary(
                    str(health_snapshot.get("summary") or "unconfigured"),
                    str(dependency_snapshot.get("summary") or "none"),
                ),
            }
        )
    return decorated


def _run_project_command_local(command: str, runtime_path: str | None, action: str) -> dict:
    started_at = _now_iso()
    try:
        completed = subprocess.run(
            command,
            cwd=runtime_path,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        return {
            "ok": False,
            "action": action,
            "command": command,
            "cwd": runtime_path or "",
            "exit_code": None,
            "stdout": stdout,
            "stderr": stderr,
            "detail": "Command timed out after 600 seconds.",
            "ran_at": started_at,
        }
    except OSError as exc:
        return {
            "ok": False,
            "action": action,
            "command": command,
            "cwd": runtime_path or "",
            "exit_code": None,
            "stdout": "",
            "stderr": str(exc),
            "detail": str(exc),
            "ran_at": started_at,
        }

    return {
        "ok": completed.returncode == 0,
        "action": action,
        "command": command,
        "cwd": runtime_path or "",
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "detail": "Command completed successfully." if completed.returncode == 0 else "Command failed.",
        "ran_at": started_at,
    }


def _run_project_command_via_runner(project: dict, command: str, runtime_path: str | None, action: str) -> dict:
    runner_url = _action_runner_url()
    if not runner_url:
        raise ProjectValidationError("Host action runner is not configured.")

    headers = {"Content-Type": "application/json"}
    token = _action_runner_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {
        "slug": project["slug"],
        "action": action,
        "command": command,
        "cwd": runtime_path or "",
        "timeout_seconds": 600,
    }

    try:
        response = requests.post(
            f"{runner_url.rstrip('/')}/run",
            headers=headers,
            json=payload,
            timeout=610,
        )
    except requests.RequestException as exc:
        return {
            "ok": False,
            "action": action,
            "command": command,
            "cwd": runtime_path or "",
            "exit_code": None,
            "stdout": "",
            "stderr": str(exc),
            "detail": f"Host action runner request failed: {exc}",
            "ran_at": _now_iso(),
        }

    try:
        data = response.json()
    except ValueError:
        raw = response.text.strip()
        data = {
            "ok": False,
            "action": action,
            "command": command,
            "cwd": runtime_path or "",
            "exit_code": None,
            "stdout": "",
            "stderr": raw,
            "detail": raw or "Host action runner returned a non-JSON response.",
            "ran_at": _now_iso(),
        }

    if "action" not in data:
        data["action"] = action
    if "command" not in data:
        data["command"] = command
    if "cwd" not in data:
        data["cwd"] = runtime_path or ""
    if "ran_at" not in data:
        data["ran_at"] = _now_iso()
    if response.status_code >= 400 and "ok" not in data:
        data["ok"] = False
    return data


def _run_project_command(project: dict, action: str) -> dict:
    command_field = PROJECT_ACTION_COMMANDS.get(action)
    if not command_field:
        raise ProjectValidationError("Unsupported project action.")

    command = str(project.get(command_field) or "").strip()
    if not command:
        raise ProjectValidationError(f"No {action} command configured for this project.")
    runtime_path = str(project.get("runtime_path") or "").strip() or None

    runner_url = _action_runner_url()
    if runner_url:
        return _run_project_command_via_runner(project, command, runtime_path, action)
    return _run_project_command_local(command, runtime_path, action)

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
    ensure_projects_store()
    print("--- Controller Startup ---")

    # 1. DYNAMIC DISCOVERY
    tools_config = scan_tools()

    # 2. Sync to Database
    for t in tools_config:
        name = t["name"]
        process_path = t["process_path"]
        port = t["port"]

        db_tool = get_tool_by_name(name)
        if not db_tool:
            add_tool(name, process_path, port)
        else:
            if (
                db_tool.process_path != process_path
                or db_tool.port != port
            ):
                update_tool_metadata(
                    name,
                    process_path=process_path,
                    port=port,
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
            alive_check = ProcessManager.is_alive(t["name"])
            if alive_check.get("alive"):
                continue  # Already running

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex="chrome-extension://.*",
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# -------------------------------------------------------------
# Core Controller Routes
# -------------------------------------------------------------
@app.get("/dashboard")
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/dashboard/job-applications")
def dashboard_job_applications(days: int = 365):
    return _job_application_counts(days)


@app.get("/projects")
def get_projects():
    return {"projects": _projects_with_runtime_state()}


@app.post("/projects/refresh-health")
def refresh_projects_health():
    return {"projects": _projects_with_runtime_state(refresh_health=True)}


@app.post("/projects")
def register_project(payload: dict):
    try:
        project = create_project(payload)
    except ProjectValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    return {"project": project}


@app.put("/projects/{slug}")
def save_project(slug: str, payload: dict):
    if not get_project(slug):
        return JSONResponse(status_code=404, content={"detail": "Project not found."})
    try:
        project = update_project(slug, payload)
    except ProjectValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    return {"project": project}


@app.delete("/projects/{slug}")
def remove_project(slug: str):
    if not get_project(slug):
        return JSONResponse(status_code=404, content={"detail": "Project not found."})
    try:
        project = delete_project(slug)
    except ProjectValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    return {"project": project}


@app.post("/projects/export")
def export_project_catalog():
    try:
        result = export_projects()
    except ProjectValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except OSError as exc:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    return result


@app.post("/projects/publish")
def publish_project_catalog():
    try:
        result = publish_portfolio_catalog()
    except ProjectValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except OSError as exc:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    return result


@app.post("/projects/{slug}/health-check")
def check_project_health(slug: str):
    project = get_project(slug)
    if not project:
        return JSONResponse(status_code=404, content={"detail": "Project not found."})
    snapshot = _project_health_snapshot(project)
    PROJECT_HEALTH_CACHE[project["slug"]] = snapshot
    return snapshot


@app.post("/projects/{slug}/action")
def run_project_action(slug: str, payload: dict):
    project = get_project(slug)
    if not project:
        return JSONResponse(status_code=404, content={"detail": "Project not found."})

    action = str(payload.get("action") or "").strip().lower()
    try:
        result = _run_project_command(project, action)
    except ProjectValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "action": action,
                "command": "",
                "cwd": str(project.get("runtime_path") or ""),
                "exit_code": None,
                "stdout": "",
                "stderr": str(exc),
                "detail": str(exc),
                "ran_at": _now_iso(),
            },
        )

    if result["ok"]:
        return result
    return JSONResponse(status_code=500, content=result)


@app.get("/tools")
def get_tools():
    tools = list_tools()
    for tool in tools:
        manifest = _read_tool_manifest(tool["name"]) or {}
        tool["auto_start"] = bool(manifest.get("auto_start", False))
        tool["category"] = _normalize_tool_category(manifest.get("category"))
        tool["title"] = str(manifest.get("title") or tool["name"])
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
