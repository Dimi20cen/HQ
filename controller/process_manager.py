import json
import os
import subprocess
import psutil
import sys
from pathlib import Path

from controller.db import (
    get_tool_by_name,
    update_tool_pid,
    update_tool_status
)

# Base directory of the whole project (hq/)
BASE_DIR = Path(__file__).resolve().parent.parent


class ProcessManager:
    @staticmethod
    def _load_manifest(process_path: Path):
        for parent in [process_path.parent, *process_path.parents]:
            manifest_path = parent / "tool.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, "r") as f:
                        return json.load(f)
                except Exception:
                    return {}
            if parent == BASE_DIR:
                break
        return {}

    @staticmethod
    def _normalize_args(value):
        if not value:
            return []
        if isinstance(value, list):
            return [str(v) for v in value]
        return [str(value)]

    @staticmethod
    def launch_tool(name: str):
        """Launch tool based on DB entry."""
        tool = get_tool_by_name(name)
        if not tool:
            return {"error": f"Tool '{name}' not registered."}

        # Already running?
        if tool.pid and ProcessManager._pid_alive(tool.pid):
            return {"error": f"Tool '{name}' already running (pid={tool.pid})."}

        # Resolve full path from the PROJECT ROOT
        path = (BASE_DIR / tool.process_path).resolve()

        if not path.exists():
            return {"error": f"Process path does not exist: {path}"}

        manifest = ProcessManager._load_manifest(path)
        runtime = str(manifest.get("runtime") or "python").lower()
        runtime_args = ProcessManager._normalize_args(manifest.get("runtime_args"))
        entry_args = ProcessManager._normalize_args(manifest.get("args"))

        if runtime in ("python", "py"):
            cmd = [sys.executable]
        else:
            cmd = [runtime]

        cmd += runtime_args
        cmd.append(str(path))
        cmd += entry_args

        # 1. Create a logs directory in the project root
        log_dir = BASE_DIR / "logs"
        log_dir.mkdir(exist_ok=True)

        # 2. Open log files for this specific tool
        stdout_f = open(log_dir / f"{name}.out.log", "a") 
        stderr_f = open(log_dir / f"{name}.err.log", "a")

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(path.parent),          # so tool finds config.json, logs, etc.
                stdout=stdout_f,
                stderr=stderr_f
            )
        except Exception as e:
            return {"error": f"Failed to launch: {str(e)}"}

        update_tool_pid(name, proc.pid)
        update_tool_status(name, "running")

        return {"started": True, "pid": proc.pid}

    @staticmethod
    def kill_tool(name: str):
        tool = get_tool_by_name(name)
        if not tool:
            return {"error": f"Tool '{name}' not registered."}

        pid = tool.pid
        if not pid:
            update_tool_status(name, "stopped")
            return {"stopped": True, "note": "No PID recorded."}

        if not ProcessManager._pid_alive(pid):
            update_tool_pid(name, None)
            update_tool_status(name, "stopped")
            return {"stopped": True, "note": "Process already dead."}

        try:
            p = psutil.Process(pid)
            p.terminate()
        except Exception as e:
            return {"error": f"Failed to terminate pid={pid}: {str(e)}"}

        update_tool_pid(name, None)
        update_tool_status(name, "stopped")

        return {"stopped": True}

    @staticmethod
    def is_alive(name: str):
        tool = get_tool_by_name(name)
        if not tool:
            return {"error": f"Tool '{name}' not registered."}

        if not tool.pid:
            update_tool_status(name, "stopped")
            return {"alive": False}

        alive = ProcessManager._pid_alive(tool.pid)
        if not alive:
            update_tool_pid(name, None)
            update_tool_status(name, "stopped")

        return {"alive": alive, "pid": tool.pid}

    @staticmethod
    def _pid_alive(pid: int):
        return psutil.pid_exists(pid)
