#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import socketserver
from pathlib import Path
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _runner_token() -> str:
    return str(os.getenv("HQ_ACTION_RUNNER_TOKEN") or "").strip()


def _timeout_seconds() -> int:
    raw = str(os.getenv("HQ_ACTION_RUNNER_TIMEOUT_SECONDS") or "600").strip()
    try:
        return max(1, min(int(raw), 3600))
    except ValueError:
        return 600


def _host() -> str:
    return str(os.getenv("HQ_ACTION_RUNNER_HOST") or "0.0.0.0").strip() or "0.0.0.0"


def _port() -> int:
    raw = str(os.getenv("HQ_ACTION_RUNNER_PORT") or "8051").strip()
    try:
        return int(raw)
    except ValueError:
        return 8051


def _socket_path() -> str:
    return str(
        os.getenv("HQ_ACTION_RUNNER_SOCKET_HOST_PATH")
        or os.getenv("HQ_ACTION_RUNNER_SOCKET_PATH")
        or ""
    ).strip()


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _unauthorized(handler: BaseHTTPRequestHandler) -> None:
    _json_response(handler, HTTPStatus.UNAUTHORIZED, {"detail": "Unauthorized."})


def _forbidden(handler: BaseHTTPRequestHandler) -> None:
    _json_response(handler, HTTPStatus.FORBIDDEN, {"detail": "Forbidden."})


def _bad_request(handler: BaseHTTPRequestHandler, detail: str) -> None:
    _json_response(handler, HTTPStatus.BAD_REQUEST, {"detail": detail})


def _not_found(handler: BaseHTTPRequestHandler) -> None:
    _json_response(handler, HTTPStatus.NOT_FOUND, {"detail": "Not found."})


def _check_auth(handler: BaseHTTPRequestHandler) -> bool:
    expected = _runner_token()
    if not expected:
        return True
    header = str(handler.headers.get("Authorization") or "")
    if not header.startswith("Bearer "):
        _unauthorized(handler)
        return False
    token = header.removeprefix("Bearer ").strip()
    if token != expected:
        _forbidden(handler)
        return False
    return True


def _run_command(payload: dict) -> tuple[int, dict]:
    action = str(payload.get("action") or "").strip().lower()
    command = str(payload.get("command") or "").strip()
    cwd = str(payload.get("cwd") or "").strip() or None
    timeout_seconds = payload.get("timeout_seconds")
    try:
        timeout = max(1, min(int(timeout_seconds), 3600)) if timeout_seconds is not None else _timeout_seconds()
    except (TypeError, ValueError):
        timeout = _timeout_seconds()

    if not action:
        return HTTPStatus.BAD_REQUEST, {"detail": "action is required."}
    if not command:
        return HTTPStatus.BAD_REQUEST, {"detail": "command is required."}

    started_at = _now_iso()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return HTTPStatus.INTERNAL_SERVER_ERROR, {
            "ok": False,
            "action": action,
            "command": command,
            "cwd": cwd or "",
            "exit_code": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "detail": f"Command timed out after {timeout} seconds.",
            "ran_at": started_at,
        }
    except OSError as exc:
        return HTTPStatus.INTERNAL_SERVER_ERROR, {
            "ok": False,
            "action": action,
            "command": command,
            "cwd": cwd or "",
            "exit_code": None,
            "stdout": "",
            "stderr": str(exc),
            "detail": str(exc),
            "ran_at": started_at,
        }

    payload = {
        "ok": completed.returncode == 0,
        "action": action,
        "command": command,
        "cwd": cwd or "",
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "detail": "Command completed successfully." if completed.returncode == 0 else "Command failed.",
        "ran_at": started_at,
    }
    return HTTPStatus.OK if completed.returncode == 0 else HTTPStatus.INTERNAL_SERVER_ERROR, payload


class Handler(BaseHTTPRequestHandler):
    server_version = "HQActionRunner/0.1"

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            _not_found(self)
            return
        _json_response(
            self,
            HTTPStatus.OK,
            {
                "ok": True,
                "service": "hq-action-runner",
                "checked_at": _now_iso(),
            },
        )

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/run":
            _not_found(self)
            return
        if not _check_auth(self):
            return

        length = int(self.headers.get("Content-Length") or "0")
        raw_body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            _bad_request(self, "Body must be valid JSON.")
            return
        if not isinstance(payload, dict):
            _bad_request(self, "Body must be a JSON object.")
            return

        status, response = _run_command(payload)
        _json_response(self, status, response)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


class ThreadingUnixHTTPServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


def main() -> None:
    socket_path = _socket_path()
    if not socket_path and not _runner_token():
        raise SystemExit("HQ_ACTION_RUNNER_TOKEN is required when the runner is exposed over HTTP.")
    if socket_path:
        path = Path(socket_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        server = ThreadingUnixHTTPServer(str(path), Handler)
    else:
        server = ThreadingHTTPServer((_host(), _port()), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
