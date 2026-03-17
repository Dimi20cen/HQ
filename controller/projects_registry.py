from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime, UTC
from pathlib import Path
from urllib.parse import urlparse


PUBLIC_MODES = {"hidden", "demo", "full", "source"}
URL_FIELDS = {
    "primary_url",
    "repo_url",
    "private_url",
    "health_public_url",
    "health_private_url",
}
REQUIRED_FIELDS = {
    "slug",
    "title",
    "public_summary",
    "public_mode",
    "primary_url",
    "repo_url",
    "sort_order",
    "linked_tools",
    "depends_on",
    "private_url",
    "deployment_host",
    "deployment_location",
    "runtime_path",
    "health_public_url",
    "health_private_url",
    "deploy_command",
    "start_command",
    "restart_command",
    "stop_command",
    "logs_command",
    "updated_at",
}
PUBLIC_EXPORT_FIELDS = (
    "slug",
    "title",
    "public_summary",
    "public_mode",
    "primary_url",
    "repo_url",
    "sort_order",
)


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_PROJECTS_PATH = BASE_DIR.parent / "runtime" / "projects" / "projects.json"
DEFAULT_EXPORT_PATH = BASE_DIR.parent / "runtime" / "projects" / "projects.generated.json"
DEFAULT_PORTFOLIO_EXPORT_PATH = BASE_DIR.parent.parent / "dimy.dev" / "data" / "projects.generated.json"


class ProjectValidationError(ValueError):
    pass


def _projects_path() -> Path:
    configured = os.getenv("HQ_PROJECTS_PATH")
    if configured:
        return Path(configured)
    return DEFAULT_PROJECTS_PATH


def _export_path() -> Path:
    configured = os.getenv("HQ_PROJECTS_EXPORT_PATH")
    if configured:
        return Path(configured)
    return DEFAULT_EXPORT_PATH


def _portfolio_export_path() -> Path | None:
    configured = os.getenv("HQ_PORTFOLIO_EXPORT_PATH")
    if configured:
        return Path(configured)
    if DEFAULT_PORTFOLIO_EXPORT_PATH.exists():
        return DEFAULT_PORTFOLIO_EXPORT_PATH
    return None


def ensure_projects_store() -> Path:
    path = _projects_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("[]\n", encoding="utf-8")
    return path


def _load_projects_raw() -> list[dict]:
    path = ensure_projects_store()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectValidationError(f"Invalid project registry JSON: {exc}") from exc
    if not isinstance(data, list):
        raise ProjectValidationError("Project registry must be a JSON array.")
    return [normalize_project(item) for item in data]


def _write_projects(projects: list[dict]) -> None:
    path = ensure_projects_store()
    payload = [normalize_project(project) for project in projects]
    path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")


def _slugify(value: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    parts = [part for part in safe.split("-") if part]
    return "-".join(parts)


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validate_optional_url(field_name: str, value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return ""
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ProjectValidationError(f"{field_name} must be a full http/https URL.")
    return cleaned


def normalize_project(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ProjectValidationError("Project payload must be an object.")

    slug = _slugify(str(payload.get("slug") or ""))
    title = str(payload.get("title") or "").strip()
    public_summary = str(payload.get("public_summary") or "").strip()
    public_mode = str(payload.get("public_mode") or "hidden").strip().lower()
    primary_url = _validate_optional_url("primary_url", str(payload.get("primary_url") or ""))
    repo_url = _validate_optional_url("repo_url", str(payload.get("repo_url") or ""))
    private_url = _validate_optional_url("private_url", str(payload.get("private_url") or ""))
    health_public_url = _validate_optional_url(
        "health_public_url", str(payload.get("health_public_url") or "")
    )
    health_private_url = _validate_optional_url(
        "health_private_url", str(payload.get("health_private_url") or "")
    )
    deployment_host = str(payload.get("deployment_host") or "").strip()
    deployment_location = str(payload.get("deployment_location") or "").strip()
    runtime_path = str(payload.get("runtime_path") or "").strip()
    deploy_command = str(payload.get("deploy_command") or "").strip()
    start_command = str(payload.get("start_command") or "").strip()
    restart_command = str(payload.get("restart_command") or "").strip()
    stop_command = str(payload.get("stop_command") or "").strip()
    logs_command = str(payload.get("logs_command") or "").strip()

    try:
        sort_order = int(payload.get("sort_order", 0))
    except (TypeError, ValueError) as exc:
        raise ProjectValidationError("sort_order must be an integer.") from exc

    linked_tools_raw = payload.get("linked_tools") or []
    if not isinstance(linked_tools_raw, list):
        raise ProjectValidationError("linked_tools must be an array.")
    linked_tools = [str(item).strip() for item in linked_tools_raw if str(item).strip()]
    depends_on_raw = payload.get("depends_on") or []
    if isinstance(depends_on_raw, str):
        depends_on_raw = [part.strip() for part in depends_on_raw.split(",")]
    if not isinstance(depends_on_raw, list):
        raise ProjectValidationError("depends_on must be an array.")
    depends_on: list[str] = []
    for item in depends_on_raw:
        dependency = _slugify(str(item).strip())
        if dependency and dependency not in depends_on:
            depends_on.append(dependency)

    if not slug:
        raise ProjectValidationError("slug is required.")
    if not title:
        raise ProjectValidationError("title is required.")
    if not public_summary:
        raise ProjectValidationError("public_summary is required.")
    if public_mode not in PUBLIC_MODES:
        raise ProjectValidationError(f"public_mode must be one of: {', '.join(sorted(PUBLIC_MODES))}.")
    if public_mode in {"demo", "full"} and not primary_url:
        raise ProjectValidationError("demo/full projects require a public primary_url.")
    if public_mode == "source" and not repo_url:
        raise ProjectValidationError("source projects require a public repo_url.")
    if deployment_host:
        from controller.hosts_registry import get_host

        if not get_host(deployment_host):
            raise ProjectValidationError(f"Unknown deployment_host '{deployment_host}'.")

    updated_at = str(payload.get("updated_at") or "").strip() or _now_iso()

    project = {
        "slug": slug,
        "title": title,
        "public_summary": public_summary,
        "public_mode": public_mode,
        "primary_url": primary_url,
        "repo_url": repo_url,
        "sort_order": sort_order,
        "linked_tools": linked_tools,
        "depends_on": depends_on,
        "private_url": private_url,
        "deployment_host": deployment_host,
        "deployment_location": deployment_location,
        "runtime_path": runtime_path,
        "health_public_url": health_public_url,
        "health_private_url": health_private_url,
        "deploy_command": deploy_command,
        "start_command": start_command,
        "restart_command": restart_command,
        "stop_command": stop_command,
        "logs_command": logs_command,
        "updated_at": updated_at,
    }

    for field in REQUIRED_FIELDS:
        project.setdefault(field, None)

    return project


def list_projects() -> list[dict]:
    projects = _load_projects_raw()
    return sorted(projects, key=lambda item: (item["sort_order"], item["title"].lower(), item["slug"]))


def get_project(slug: str) -> dict | None:
    target = _slugify(slug)
    for project in _load_projects_raw():
        if project["slug"] == target:
            return project
    return None


def create_project(payload: dict) -> dict:
    projects = _load_projects_raw()
    project = normalize_project(payload)
    if any(existing["slug"] == project["slug"] for existing in projects):
        raise ProjectValidationError("Project slug already exists.")
    project["updated_at"] = _now_iso()
    projects.append(project)
    _write_projects(projects)
    return project


def update_project(slug: str, payload: dict) -> dict:
    target = _slugify(slug)
    projects = _load_projects_raw()
    for index, existing in enumerate(projects):
        if existing["slug"] != target:
            continue
        merged = deepcopy(existing)
        merged.update(payload or {})
        merged["slug"] = target
        merged["updated_at"] = _now_iso()
        projects[index] = normalize_project(merged)
        _write_projects(projects)
        return projects[index]
    raise ProjectValidationError("Project not found.")


def delete_project(slug: str) -> dict:
    target = _slugify(slug)
    projects = _load_projects_raw()
    for index, existing in enumerate(projects):
        if existing["slug"] != target:
            continue
        removed = projects.pop(index)
        _write_projects(projects)
        return removed
    raise ProjectValidationError("Project not found.")


def export_projects(destination: Path | None = None) -> dict:
    export_path = destination or _export_path()
    export_path.parent.mkdir(parents=True, exist_ok=True)
    exported = [
        {field: project.get(field) for field in PUBLIC_EXPORT_FIELDS}
        for project in list_projects()
        if project["public_mode"] != "hidden"
    ]
    payload = f"{json.dumps(exported, indent=2)}\n"
    export_path.write_text(payload, encoding="utf-8")

    synced_paths: list[str] = []
    portfolio_export_path = _portfolio_export_path()
    if portfolio_export_path:
        portfolio_export_path.parent.mkdir(parents=True, exist_ok=True)
        portfolio_export_path.write_text(payload, encoding="utf-8")
        synced_paths.append(str(portfolio_export_path))

    return {
        "count": len(exported),
        "path": str(export_path),
        "export_path": str(export_path),
        "synced_paths": synced_paths,
        "projects": exported,
    }
