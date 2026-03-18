from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from controller.projects_registry import ProjectValidationError, export_projects


DEFAULT_PORTFOLIO_REPO_DIR = Path(__file__).resolve().parents[2] / "dimy.dev"
DEFAULT_PORTFOLIO_BRANCH = "main"
DEFAULT_EXPORT_RELATIVE_PATH = Path("data") / "projects.generated.json"
PUBLISH_COMMIT_MESSAGE = "Update portfolio project catalog"


def _portfolio_repo_dir() -> Path:
    configured = str(os.getenv("HQ_PORTFOLIO_REPO_DIR") or "").strip()
    if configured:
        return Path(configured)
    if (DEFAULT_PORTFOLIO_REPO_DIR / ".git").exists():
        return DEFAULT_PORTFOLIO_REPO_DIR
    raise ProjectValidationError(
        "HQ_PORTFOLIO_REPO_DIR is not configured and no sibling dimy.dev repo was found."
    )


def _portfolio_branch() -> str:
    return str(os.getenv("HQ_PORTFOLIO_BRANCH") or DEFAULT_PORTFOLIO_BRANCH).strip() or DEFAULT_PORTFOLIO_BRANCH


def _portfolio_export_path(repo_dir: Path) -> Path:
    configured = str(os.getenv("HQ_PORTFOLIO_EXPORT_PATH") or "").strip()
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else repo_dir / path
    return repo_dir / DEFAULT_EXPORT_RELATIVE_PATH


def _run_git(repo_dir: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and completed.returncode != 0:
        command = "git " + " ".join(args)
        detail = completed.stderr.strip() or completed.stdout.strip() or "git command failed."
        raise ProjectValidationError(f"{command} failed: {detail}")
    return completed


def _parse_status_paths(raw: str) -> list[str]:
    paths: list[str] = []
    for line in raw.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
        paths.append(path)
    return paths


def _relative_repo_path(path: Path, repo_dir: Path) -> str:
    return path.resolve().relative_to(repo_dir.resolve()).as_posix()


def _status_path_matches_export(path: str, export_relpath: str) -> bool:
    normalized = path.rstrip("/")
    if normalized == export_relpath:
        return True
    return bool(normalized) and export_relpath.startswith(f"{normalized}/")


def _branch_ahead_behind(repo_dir: Path, branch: str) -> tuple[int, int]:
    tracking_ref = f"origin/{branch}"
    completed = _run_git(repo_dir, "rev-list", "--left-right", "--count", f"{tracking_ref}...HEAD")
    raw = completed.stdout.strip()
    parts = raw.split()
    if len(parts) != 2:
        raise ProjectValidationError(
            f"Unable to determine branch sync status for {tracking_ref}: {raw or 'no output'}"
        )
    behind, ahead = (int(part) for part in parts)
    return ahead, behind


def _validate_repo(repo_dir: Path, export_path: Path, branch: str) -> dict:
    if not repo_dir.exists():
        raise ProjectValidationError(f"Portfolio repo path does not exist: {repo_dir}")
    if not repo_dir.is_dir():
        raise ProjectValidationError(f"Portfolio repo path is not a directory: {repo_dir}")

    top_level = _run_git(repo_dir, "rev-parse", "--show-toplevel").stdout.strip()
    top_level_path = Path(top_level).resolve()
    if top_level_path != repo_dir.resolve():
        raise ProjectValidationError(
            f"Portfolio repo path {repo_dir} is not the git toplevel ({top_level_path})."
        )

    try:
        export_rel = _relative_repo_path(export_path, repo_dir)
    except ValueError as exc:
        raise ProjectValidationError(
            f"Portfolio export path must live inside the repo: {export_path}"
        ) from exc

    current_branch = _run_git(repo_dir, "branch", "--show-current").stdout.strip()
    if current_branch != branch:
        raise ProjectValidationError(
            f"Portfolio repo must be on branch {branch}, found {current_branch or '(detached)'}."
        )

    origin_url = _run_git(repo_dir, "remote", "get-url", "origin").stdout.strip()
    if not origin_url:
        raise ProjectValidationError("Portfolio repo is missing remote 'origin'.")

    status_raw = _run_git(repo_dir, "status", "--porcelain", "--untracked-files=all").stdout
    dirty_paths = _parse_status_paths(status_raw)
    unrelated_paths = sorted(
        path for path in dirty_paths if not _status_path_matches_export(path, export_rel)
    )
    if unrelated_paths:
        preview = ", ".join(unrelated_paths[:5])
        extra = "" if len(unrelated_paths) <= 5 else f" (+{len(unrelated_paths) - 5} more)"
        raise ProjectValidationError(
            f"Portfolio repo has unrelated changes outside {export_rel}: {preview}{extra}"
        )

    return {
        "repo_path": str(repo_dir),
        "repo_top_level": str(top_level_path),
        "export_path": str(export_path),
        "export_relpath": export_rel,
        "branch": current_branch,
        "origin_url": origin_url,
        "dirty_paths": dirty_paths,
    }


def publish_portfolio_catalog() -> dict:
    repo_dir = _portfolio_repo_dir().resolve()
    branch = _portfolio_branch()
    export_path = _portfolio_export_path(repo_dir).resolve()
    repo_info = _validate_repo(repo_dir, export_path, branch)

    export_result = export_projects()
    payload = f"{json.dumps(export_result['projects'], indent=2)}\n"
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(payload, encoding="utf-8")

    status_after_write = _run_git(
        repo_dir, "status", "--porcelain", "--untracked-files=all"
    ).stdout
    dirty_paths = _parse_status_paths(status_after_write)
    unrelated_paths = sorted(
        path
        for path in dirty_paths
        if not _status_path_matches_export(path, repo_info["export_relpath"])
    )
    if unrelated_paths:
        preview = ", ".join(unrelated_paths[:5])
        extra = "" if len(unrelated_paths) <= 5 else f" (+{len(unrelated_paths) - 5} more)"
        raise ProjectValidationError(
            f"Portfolio repo changed outside {repo_info['export_relpath']}: {preview}{extra}"
        )

    if not any(_status_path_matches_export(path, repo_info["export_relpath"]) for path in dirty_paths):
        ahead, behind = _branch_ahead_behind(repo_dir, branch)
        if ahead > 0:
            push_result = _run_git(repo_dir, "push", "origin", branch)
            commit_sha = _run_git(repo_dir, "rev-parse", "HEAD").stdout.strip()
            detail = "Pushed previously committed portfolio catalog to origin."
            if behind > 0:
                detail = (
                    "Pushed local portfolio commits to origin, but the branch also differs from "
                    f"origin/{branch}."
                )
            return {
                "ok": True,
                "detail": detail,
                "repo_path": repo_info["repo_path"],
                "branch": branch,
                "origin_url": repo_info["origin_url"],
                "export_path": repo_info["export_path"],
                "export_relpath": repo_info["export_relpath"],
                "hq_export_path": export_result["export_path"],
                "count": export_result["count"],
                "no_changes": False,
                "commit_sha": commit_sha,
                "commit_message": "",
                "stdout": push_result.stdout.strip(),
                "stderr": push_result.stderr.strip(),
            }
        return {
            "ok": True,
            "detail": "Portfolio catalog already up to date.",
            "repo_path": repo_info["repo_path"],
            "branch": branch,
            "origin_url": repo_info["origin_url"],
            "export_path": repo_info["export_path"],
            "export_relpath": repo_info["export_relpath"],
            "hq_export_path": export_result["export_path"],
            "count": export_result["count"],
            "no_changes": True,
            "commit_sha": "",
            "stdout": "",
            "stderr": "",
        }

    add_result = _run_git(repo_dir, "add", "--", repo_info["export_relpath"])
    commit_result = _run_git(repo_dir, "commit", "-m", PUBLISH_COMMIT_MESSAGE)
    push_result = _run_git(repo_dir, "push", "origin", branch)
    commit_sha = _run_git(repo_dir, "rev-parse", "HEAD").stdout.strip()

    stdout_parts = [
        part
        for part in (
            add_result.stdout.strip(),
            commit_result.stdout.strip(),
            push_result.stdout.strip(),
        )
        if part
    ]
    stderr_parts = [
        part
        for part in (
            add_result.stderr.strip(),
            commit_result.stderr.strip(),
            push_result.stderr.strip(),
        )
        if part
    ]

    return {
        "ok": True,
        "detail": "Published portfolio catalog to origin.",
        "repo_path": repo_info["repo_path"],
        "branch": branch,
        "origin_url": repo_info["origin_url"],
        "export_path": repo_info["export_path"],
        "export_relpath": repo_info["export_relpath"],
        "hq_export_path": export_result["export_path"],
        "count": export_result["count"],
        "no_changes": False,
        "commit_sha": commit_sha,
        "commit_message": PUBLISH_COMMIT_MESSAGE,
        "stdout": "\n".join(stdout_parts),
        "stderr": "\n".join(stderr_parts),
    }
