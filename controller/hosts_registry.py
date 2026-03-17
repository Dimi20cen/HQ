from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse

from controller.projects_registry import ProjectValidationError


HOST_TRANSPORTS = {"none", "socket", "http"}
HOST_REQUIRED_FIELDS = {
    "slug",
    "title",
    "transport",
    "runner_url",
    "runner_socket_path",
    "token_env_var",
    "location",
    "notes",
    "updated_at",
}


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_HOSTS_PATH = BASE_DIR.parent / "runtime" / "hosts" / "hosts.json"


def _hosts_path() -> Path:
    configured = os.getenv("HQ_HOSTS_PATH")
    if configured:
        return Path(configured)
    return DEFAULT_HOSTS_PATH


def ensure_hosts_store() -> Path:
    path = _hosts_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("[]\n", encoding="utf-8")
    return path


def _load_hosts_raw() -> list[dict]:
    path = ensure_hosts_store()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectValidationError(f"Invalid host registry JSON: {exc}") from exc
    if not isinstance(data, list):
        raise ProjectValidationError("Host registry must be a JSON array.")
    return [normalize_host(item) for item in data]


def _write_hosts(hosts: list[dict]) -> None:
    path = ensure_hosts_store()
    payload = [normalize_host(host) for host in hosts]
    path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")


def _slugify(value: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    parts = [part for part in safe.split("-") if part]
    return "-".join(parts)


def _validate_optional_url(field_name: str, value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return ""
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ProjectValidationError(f"{field_name} must be a full http/https URL.")
    return cleaned


def normalize_host(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ProjectValidationError("Host payload must be an object.")

    slug = _slugify(str(payload.get("slug") or ""))
    title = str(payload.get("title") or "").strip()
    transport = str(payload.get("transport") or "none").strip().lower()
    runner_url = _validate_optional_url("runner_url", str(payload.get("runner_url") or ""))
    runner_socket_path = str(payload.get("runner_socket_path") or "").strip()
    token_env_var = str(payload.get("token_env_var") or "").strip()
    location = str(payload.get("location") or "").strip()
    notes = str(payload.get("notes") or "").strip()
    updated_at = str(payload.get("updated_at") or "").strip()

    if not slug:
        raise ProjectValidationError("Host slug is required.")
    if not title:
        raise ProjectValidationError("Host title is required.")
    if transport not in HOST_TRANSPORTS:
        raise ProjectValidationError(
            f"Host transport must be one of: {', '.join(sorted(HOST_TRANSPORTS))}."
        )
    if transport == "http" and not runner_url:
        raise ProjectValidationError("HTTP runner hosts require a runner_url.")
    if transport == "socket" and not runner_socket_path:
        raise ProjectValidationError("Socket runner hosts require a runner_socket_path.")
    if transport != "http":
        runner_url = ""
    if transport != "socket":
        runner_socket_path = ""

    host = {
        "slug": slug,
        "title": title,
        "transport": transport,
        "runner_url": runner_url,
        "runner_socket_path": runner_socket_path,
        "token_env_var": token_env_var,
        "location": location,
        "notes": notes,
        "updated_at": updated_at,
    }

    for field in HOST_REQUIRED_FIELDS:
        host.setdefault(field, "")

    return host


def list_hosts() -> list[dict]:
    hosts = _load_hosts_raw()
    return sorted(hosts, key=lambda item: (item["title"].lower(), item["slug"]))


def get_host(slug: str) -> dict | None:
    target = _slugify(slug)
    for host in _load_hosts_raw():
        if host["slug"] == target:
            return host
    return None


def create_host(payload: dict) -> dict:
    hosts = _load_hosts_raw()
    host = normalize_host(payload)
    if any(existing["slug"] == host["slug"] for existing in hosts):
        raise ProjectValidationError("Host slug already exists.")
    hosts.append(host)
    _write_hosts(hosts)
    return host


def update_host(slug: str, payload: dict) -> dict:
    target = _slugify(slug)
    hosts = _load_hosts_raw()
    for index, existing in enumerate(hosts):
        if existing["slug"] != target:
            continue
        merged = deepcopy(existing)
        merged.update(payload or {})
        merged["slug"] = target
        hosts[index] = normalize_host(merged)
        _write_hosts(hosts)
        return hosts[index]
    raise ProjectValidationError("Host not found.")


def delete_host(slug: str) -> dict:
    target = _slugify(slug)
    hosts = _load_hosts_raw()
    for index, existing in enumerate(hosts):
        if existing["slug"] != target:
            continue
        removed = hosts.pop(index)
        _write_hosts(hosts)
        return removed
    raise ProjectValidationError("Host not found.")
