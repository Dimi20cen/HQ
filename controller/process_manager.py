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

        try:
            proc = subprocess.Popen(
                [sys.executable, str(path)],   # always launch using venv python
                cwd=str(path.parent),          # so tool finds config.json, logs, etc.
                stdout=None,
                stderr=None
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
