import sys
import json
import os
import re
import sqlite3
import subprocess
import tempfile
import threading
import time
import uuid
import shlex
from pathlib import Path
from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse

# 1. SETUP PATHS
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from tools.sdk.base_tool import BaseTool

# 2. INITIALIZE TOOL
tool = BaseTool(__file__)

# 3. DATABASE SETUP
DB_FILE = tool.root_dir / "jobs.db"
CONFIG_PATH = tool.root_dir / "jobber.config.json"

DEFAULT_OUTPUT_DIR = "cover-letter"
DEFAULT_PROMPT_LOG = Path(tempfile.gettempdir()) / "covlet-last-prompt.txt"
DEFAULT_PROVIDER = "gemini"
DEFAULT_GEMINI_CLI = "gemini"
DEFAULT_GEMINI_MODEL_FLAG = "--model"

def load_config():
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def expand_home(value: str | None) -> str | None:
    if not value:
        return value
    if value == "~":
        return str(Path.home())
    if value.startswith("~/"):
        return str(Path.home() / value[2:])
    return value

def resolve_info_file(value: str | None) -> Path:
    if not value:
        return tool.root_dir / "info.md"
    expanded = expand_home(value)
    if not expanded:
        return tool.root_dir / "info.md"
    path = Path(expanded)
    if path.is_absolute():
        return path
    return (tool.root_dir / path).resolve()

def slugify(input_text: str) -> str:
    base = (input_text or "").strip().lower()
    base = base.replace("&", "and")
    base = re.sub(r"[^a-z0-9]+", "-", base)
    base = base.strip("-")
    return (base[:80] or "unknown-company")

def safe_read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return None

def build_prompt(company: str, job_title: str, job_description: str, job_url: str, info_text: str) -> str:
    parts = [
        "Write a tailored cover letter in plain text.",
        "Constraints:",
        "- Use only the provided info and job ad; do not invent details.",
        "- Keep it concise (120-170 words).",
        "- No placeholders.",
        "- Professional, warm tone.",
        "- No typical AI language; should feel human",
        "- Stick to facts; no over exaggeration",
        "- Output plain text only.",
        "",
        "Candidate info:",
        info_text.strip(),
        "",
        "Job context:"
    ]

    if company:
        parts.append(f"Company: {company}")
    if job_title:
        parts.append(f"Role: {job_title}")
    if job_url:
        parts.append(f"Job URL: {job_url}")
    if job_description:
        parts.extend(["", "Job ad text:", job_description.strip()])

    return "\n".join(parts)

def validate_model_name(name: str | None) -> str | None:
    if not name:
        return None
    trimmed = str(name).strip()
    if re.search(r"(^|[\s-])((x)?high|medium|low)\b", trimmed, re.IGNORECASE):
        return (
            f'Model "{trimmed}" looks like it includes a reasoning-effort suffix. '
            'Use "gpt-5.2-codex" and set reasoningEffort separately.'
        )
    return None

def normalize_args(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        return shlex.split(value)
    return []

def run_codex(prompt: str, model: str, reasoning_effort: str) -> tuple[str, list[str]]:
    with tempfile.NamedTemporaryFile(prefix="covlet-", suffix=".txt", delete=False) as tmp:
        output_path = tmp.name

    args = ["codex", "exec", "--skip-git-repo-check", "--output-last-message", output_path]
    if model:
        args.extend(["-m", model])
    if reasoning_effort:
        args.extend(["-c", f'model_reasoning_effort="{reasoning_effort}"'])
    args.append("-")

    result = subprocess.run(
        args,
        input=prompt,
        text=True,
        capture_output=True,
        cwd=tool.root_dir,
        check=False
    )

    if result.returncode != 0:
        raise RuntimeError(f"codex exited with code {result.returncode}: {result.stderr.strip()}")

    output_text = safe_read(Path(output_path))
    if not output_text:
        raise RuntimeError("codex output file missing")

    return output_text.strip(), args

def run_gemini(prompt: str, model: str, cli: str, extra_args: list[str], model_flag: str | None) -> tuple[str, list[str]]:
    args = [cli] + extra_args
    if model and model_flag:
        args.extend([model_flag, model])

    result = subprocess.run(
        args,
        input=prompt,
        text=True,
        capture_output=True,
        cwd=tool.root_dir,
        check=False
    )

    if result.returncode != 0:
        raise RuntimeError(f"gemini exited with code {result.returncode}: {result.stderr.strip()}")

    output_text = (result.stdout or "").strip()
    if not output_text:
        raise RuntimeError("gemini output empty")

    return output_text, args

def reveal_in_file_manager(path: Path) -> None:
    if sys.platform.startswith("win"):
        subprocess.Popen(["explorer", "/select,", str(path)])
        return
    if sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(path)])
        return
    subprocess.Popen(["xdg-open", str(path.parent)])

_jobs_lock = threading.Lock()
_jobs: dict[str, dict] = {}
_inflight_by_output: dict[str, str] = {}

def _set_job(job_id: str, updates: dict) -> None:
    with _jobs_lock:
        job = _jobs.get(job_id, {})
        job.update(updates)
        _jobs[job_id] = job

def _get_job(job_id: str) -> dict | None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None

def _get_inflight_job_id(output_path: Path) -> str | None:
    with _jobs_lock:
        job_id = _inflight_by_output.get(str(output_path))
        if not job_id:
            return None
        if job_id not in _jobs:
            # Stale mapping; drop it.
            _inflight_by_output.pop(str(output_path), None)
            return None
        return job_id

def _set_inflight(output_path: Path, job_id: str) -> None:
    with _jobs_lock:
        _inflight_by_output[str(output_path)] = job_id

def _clear_inflight(output_path: Path, job_id: str) -> None:
    with _jobs_lock:
        existing = _inflight_by_output.get(str(output_path))
        if existing == job_id:
            _inflight_by_output.pop(str(output_path), None)

config = load_config()
INFO_FILE = resolve_info_file(os.environ.get("COVLET_INFO_FILE") or config.get("infoFile"))
OUTPUT_DIR = os.environ.get("COVLET_OUTPUT_DIR") or config.get("outputDir") or DEFAULT_OUTPUT_DIR
MODEL = os.environ.get("COVLET_MODEL") or config.get("model") or ""
REASONING_EFFORT = os.environ.get("COVLET_REASONING_EFFORT") or config.get("reasoningEffort") or ""

def parse_bool(value) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
    return None

provider_raw = os.environ.get("COVLET_PROVIDER")
if provider_raw is None:
    codex_enabled = parse_bool(config.get("codex"))
    gemini_enabled = parse_bool(config.get("gemini"))
    if codex_enabled is True and gemini_enabled is True:
        provider_raw = "gemini"
    elif codex_enabled is True:
        provider_raw = "codex"
    elif gemini_enabled is True:
        provider_raw = "gemini"
    else:
        provider_raw = config.get("provider") or DEFAULT_PROVIDER
PROVIDER = str(provider_raw).strip().lower() if provider_raw else DEFAULT_PROVIDER

gemini_cli_raw = os.environ.get("COVLET_GEMINI_CLI")
if gemini_cli_raw is None:
    gemini_cli_raw = config.get("geminiCli") or DEFAULT_GEMINI_CLI
GEMINI_CLI = str(gemini_cli_raw).strip() if gemini_cli_raw else DEFAULT_GEMINI_CLI

gemini_args_raw = os.environ.get("COVLET_GEMINI_ARGS")
if gemini_args_raw is None:
    gemini_args_raw = config.get("geminiArgs")
GEMINI_ARGS = normalize_args(gemini_args_raw)

gemini_model_flag_raw = os.environ.get("COVLET_GEMINI_MODEL_FLAG")
if gemini_model_flag_raw is None:
    gemini_model_flag_raw = config.get("geminiModelFlag", DEFAULT_GEMINI_MODEL_FLAG)
GEMINI_MODEL_FLAG = str(gemini_model_flag_raw) if gemini_model_flag_raw is not None else DEFAULT_GEMINI_MODEL_FLAG
GEMINI_MODEL_FLAG = GEMINI_MODEL_FLAG.strip() if isinstance(GEMINI_MODEL_FLAG, str) else DEFAULT_GEMINI_MODEL_FLAG
GEMINI_MODEL_FLAG = GEMINI_MODEL_FLAG or None

codex_reasoning_raw = config.get("codex_reasoningEffort")
if REASONING_EFFORT == "" and codex_reasoning_raw:
    REASONING_EFFORT = str(codex_reasoning_raw).strip()

PROMPT_LOG = Path(os.environ.get("COVLET_PROMPT_LOG") or DEFAULT_PROMPT_LOG)

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                company TEXT,
                location TEXT,
                url TEXT UNIQUE,
                date_scraped TEXT,
                description TEXT
            )
        """)

# Initialize DB immediately on startup
init_db()

# --- Routes ---

@tool.app.post("/check")
async def check_job(request: Request):
    """Checks if a URL exists in the DB and returns the data."""
    data = await request.json()
    url_to_check = data.get("url")

    if not url_to_check:
        return JSONResponse({"found": False})

    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE url = ?", (url_to_check,))
            row = cursor.fetchone()

            if row:
                return {
                    "found": True,
                    "data": {
                        "title": row["title"],
                        "company": row["company"],
                        "location": row["location"],
                        "url": row["url"],
                        "date_scraped": row["date_scraped"],
                        "description": row["description"]
                    }
                }
            else:
                return {"found": False}
    except Exception as e:
        print(f"Error checking job: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@tool.app.post("/save")
async def save_job(request: Request):
    data = await request.json()
    
    if not data:
        return JSONResponse({"error": "No data"}, status_code=400)

    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("""
                INSERT INTO jobs (title, company, location, url, date_scraped, description)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    title=excluded.title,
                    company=excluded.company,
                    location=excluded.location,
                    date_scraped=excluded.date_scraped,
                    description=excluded.description
            """, (
                data.get('title', 'Unknown'),
                data.get('company', 'Unknown'),
                data.get('location', 'Unknown'),
                data.get('url', ''),
                data.get('date_scraped', ''),
                data.get('description', '')
            ))
            
            count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            
        print(f"Saved/Updated job: {data.get('title')}")
        return {"status": "saved", "total_count": count}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@tool.app.post("/generate")
async def generate_letter(request: Request):
    data = await request.json()

    info_text = safe_read(INFO_FILE)
    if not info_text:
        return JSONResponse({"ok": False, "error": f"Missing info file: {INFO_FILE}"}, status_code=500)

    company = (data.get("company") or "").strip()
    job_title = (data.get("jobTitle") or data.get("title") or "").strip()
    job_description = (data.get("jobDescription") or data.get("description") or "").strip()
    job_url = (data.get("jobUrl") or data.get("url") or "").strip()

    if not job_description:
        return JSONResponse({"ok": False, "error": "Missing job description"}, status_code=400)

    prompt = build_prompt(company, job_title, job_description, job_url, info_text)
    warnings = []
    if PROVIDER == "codex":
        model_warning = validate_model_name(MODEL)
        if model_warning:
            warnings.append(model_warning)
            print(f"jobber: warnings: {' | '.join(warnings)}")
    elif PROVIDER != "gemini":
        warnings.append(f'Unknown provider "{PROVIDER}". Expected "gemini" or "codex".')
        print(f"jobber: warnings: {' | '.join(warnings)}")

    try:
        PROMPT_LOG.write_text(prompt + "\n", encoding="utf-8")
    except Exception:
        pass

    output_name = f"{slugify(company or job_title or 'job')}.txt"
    output_dir = (tool.root_dir / OUTPUT_DIR).resolve()
    output_path = output_dir / output_name

    if output_path.exists():
        return {
            "ok": True,
            "outputPath": str(output_path),
            "skipped": True,
            "reason": "Letter already exists for this job/company."
        }

    inflight_job_id = _get_inflight_job_id(output_path)
    if inflight_job_id:
        job = _get_job(inflight_job_id) or {}
        return {
            "ok": True,
            "jobId": inflight_job_id,
            "status": job.get("status", "running"),
            "outputPath": str(output_path),
            "inFlight": True,
            "reason": "Generation already in progress."
        }

    job_id = uuid.uuid4().hex
    _set_job(job_id, {
        "ok": True,
        "jobId": job_id,
        "status": "queued",
        "outputPath": str(output_path),
        "createdAtMs": int(time.time() * 1000),
        "warnings": warnings,
        "promptLogPath": str(PROMPT_LOG),
        "engine": PROVIDER,
        "modelRequested": MODEL or ""
    })
    _set_inflight(output_path, job_id)

    def worker():
        _set_job(job_id, {"status": "running", "startedAtMs": int(time.time() * 1000)})
        request_start = time.time()
        try:
            llm_start = time.time()
            if PROVIDER == "codex":
                letter, command_args = run_codex(prompt, MODEL, REASONING_EFFORT)
                model_used = MODEL or ""
            elif PROVIDER == "gemini":
                letter, command_args = run_gemini(prompt, MODEL, GEMINI_CLI, GEMINI_ARGS, GEMINI_MODEL_FLAG)
                model_used = MODEL or ""
            else:
                raise RuntimeError(f'Unknown provider "{PROVIDER}"')
            llm_ms = int((time.time() - llm_start) * 1000)
            command_str = " ".join(command_args)

            output_dir.mkdir(parents=True, exist_ok=True)
            output_path.write_text(letter + "\n", encoding="utf-8")

            total_ms = int((time.time() - request_start) * 1000)
            if model_used:
                print(f"jobber: model: {model_used}")
            print(f"jobber: cmd: {command_str}")
            print(f"jobber: generated {output_name} in {total_ms}ms ({PROVIDER} {llm_ms}ms)")

            _set_job(job_id, {
                "status": "done",
                "preview": letter[:500],
                "timingsMs": {"total": total_ms, "llm": llm_ms},
                "engine": PROVIDER,
                "modelUsed": model_used,
                "command": command_str,
                "commandArgs": command_args,
                "finishedAtMs": int(time.time() * 1000)
            })
        except Exception as e:
            _set_job(job_id, {
                "status": "error",
                "error": str(e),
                "modelUsed": model_used if "model_used" in locals() else "",
                "command": " ".join(command_args) if "command_args" in locals() else "",
                "commandArgs": command_args if "command_args" in locals() else [],
                "finishedAtMs": int(time.time() * 1000)
            })
        finally:
            _clear_inflight(output_path, job_id)

    threading.Thread(target=worker, daemon=True).start()

    # Return immediately; popup can poll /generate-status/<jobId>.
    return {"ok": True, "jobId": job_id, "status": "queued", "outputPath": str(output_path)}

@tool.app.get("/generate-status/{job_id}")
async def generate_status(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return JSONResponse({"ok": False, "error": "Unknown job id"}, status_code=404)
    return job

@tool.app.post("/open-output")
async def open_output(request: Request):
    data = await request.json()
    path_raw = data.get("path")
    if not path_raw:
        return JSONResponse({"ok": False, "error": "Missing path"}, status_code=400)

    try:
        path = Path(path_raw).expanduser().resolve()
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid path"}, status_code=400)

    output_dir = (tool.root_dir / OUTPUT_DIR).resolve()
    if output_dir not in path.parents:
        return JSONResponse({"ok": False, "error": "Path not allowed"}, status_code=400)

    if not path.exists():
        return JSONResponse({"ok": False, "error": "File not found"}, status_code=404)

    try:
        reveal_in_file_manager(path)
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@tool.app.post("/delete")
async def delete_job(request: Request):
    data = await request.json()
    url_to_delete = data.get("url")

    if not url_to_delete:
        return JSONResponse({"error": "No URL provided"}, status_code=400)

    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("DELETE FROM jobs WHERE url = ?", (url_to_delete,))
            
        print(f"Deleted job: {url_to_delete}")
        return {"status": "deleted"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# --- Widget UI ---

def widget_generator():
    """Displays jobs in a clean, truncated list with hover-reveal"""
    jobs = []
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            jobs = conn.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT 50").fetchall()
    except Exception:
        pass # Handle DB errors gracefully in UI

    list_html = ""
    
    if not jobs:
        list_html = """<div class="empty-state">No jobs saved yet.</div>"""
    
    for job in jobs:
        date_str = job['date_scraped'][:10] if job['date_scraped'] else "-"
        
        list_html += f"""
        <a class="row" href="{job['url']}" target="_blank">
            <div class="col-title" title="{job['title']}">{job['title']}</div>
            <div class="col-company" title="{job['company']}">{job['company']}</div>
            <div class="col-loc" title="{job['location']}">{job['location']}</div>
            <div class="col-date">{date_str}</div>
        </a>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            :root {{
                --bg: #ffffff; --text-main: #222; --text-sub: #666;
                --border: #f0f0f0; --hover-bg: #f8f9fa;
            }}
            * {{ box-sizing: border-box; }}
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background-color: var(--bg); padding: 10px 30px; margin: 0 auto;
                max-width: 1200px; color: var(--text-main);
            }}
            .row {{
                display: flex; align-items: center; padding: 12px 0;
                text-decoration: none; border-bottom: 1px solid var(--border);
                color: inherit; gap: 20px; transition: background 0.15s;
            }}
            .row:hover {{ background-color: var(--hover-bg); }}
            .col-title {{ flex: 1; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }}
            .col-company {{ width: 180px; font-size: 13px; color: var(--text-sub); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-shrink: 0; }}
            .col-loc {{ width: 140px; font-size: 12px; color: #999; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-shrink: 0; }}
            .col-date {{ width: 85px; font-size: 11px; color: #bbb; font-family: monospace; text-align: right; flex-shrink: 0; }}
            @media (max-width: 700px) {{ .col-loc {{ display: none; }} .col-company {{ width: 120px; }} }}
            .empty-state {{ padding: 40px; text-align: center; color: #ccc; }}
        </style>
    </head>
    <body>
        <div>{list_html}</div>
    </body>
    </html>
    """
    return html

# Register Widget
tool.add_widget_route(widget_generator)

if __name__ == "__main__":
    tool.run()
