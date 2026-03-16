from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime, UTC
from pathlib import Path


PUBLIC_MODES = {"none", "docs", "demo", "full"}
REQUIRED_FIELDS = {
    "slug",
    "title",
    "public_summary",
    "public_mode",
    "primary_url",
    "repo_url",
    "sort_order",
    "linked_tools",
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


def normalize_project(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ProjectValidationError("Project payload must be an object.")

    slug = _slugify(str(payload.get("slug") or ""))
    title = str(payload.get("title") or "").strip()
    public_summary = str(payload.get("public_summary") or "").strip()
    public_mode = str(payload.get("public_mode") or "none").strip().lower()
    primary_url = str(payload.get("primary_url") or "").strip()
    repo_url = str(payload.get("repo_url") or "").strip()

    try:
        sort_order = int(payload.get("sort_order", 0))
    except (TypeError, ValueError) as exc:
        raise ProjectValidationError("sort_order must be an integer.") from exc

    linked_tools_raw = payload.get("linked_tools") or []
    if not isinstance(linked_tools_raw, list):
        raise ProjectValidationError("linked_tools must be an array.")
    linked_tools = [str(item).strip() for item in linked_tools_raw if str(item).strip()]

    if not slug:
        raise ProjectValidationError("slug is required.")
    if not title:
        raise ProjectValidationError("title is required.")
    if not public_summary:
        raise ProjectValidationError("public_summary is required.")
    if public_mode not in PUBLIC_MODES:
        raise ProjectValidationError(f"public_mode must be one of: {', '.join(sorted(PUBLIC_MODES))}.")

    if public_mode in {"demo", "full"} and not primary_url and not repo_url:
        raise ProjectValidationError(
            "public projects need at least one public destination: primary_url or repo_url."
        )

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


def export_projects(destination: Path | None = None) -> dict:
    export_path = destination or _export_path()
    export_path.parent.mkdir(parents=True, exist_ok=True)
    exported = [
        {field: project.get(field) for field in PUBLIC_EXPORT_FIELDS}
        for project in list_projects()
        if project["public_mode"] != "none"
    ]
    export_path.write_text(f"{json.dumps(exported, indent=2)}\n", encoding="utf-8")
    return {
        "count": len(exported),
        "path": str(export_path),
        "projects": exported,
    }
