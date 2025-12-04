import json
import psutil
from datetime import datetime
from pathlib import Path

class BlockerCore:
    def __init__(self, config_path="config.json", log_dir="logs"):
        self.config_path = Path(config_path)
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        self.kill_log_path = self.log_dir / "kills.log"
        self.kill_log_path.touch(exist_ok=True)

        # State loaded from config
        self.check_interval = 5
        self.windows = []

        # Runtime state
        self.last_kill_time = None

        self.load_config()

    # -------------------------------------------------------------
    # Config handling
    # -------------------------------------------------------------
    def load_config(self):
        """Loads config.json and pre-parses time windows."""
        with open(self.config_path, "r") as f:
            raw = json.load(f)

        self.check_interval = raw.get("check_interval_seconds", 5)

        windows = []
        for w in raw.get("blocked_windows", []):
            windows.append({
                "start": self._parse_time(w["start"]),
                "end": self._parse_time(w["end"]),
                "processes": [name.lower() for name in w["processes"]],
            })
        self.windows = windows

    def update_config(self, new_data: dict):
        """Writes new config to disk and reloads it into memory."""
        with open(self.config_path, "w") as f:
            json.dump(new_data, f, indent=4)
        self.load_config()

    # -------------------------------------------------------------
    # Time helpers
    # -------------------------------------------------------------
    def _parse_time(self, tstr):
        """Convert HH:MM to minutes since midnight."""
        h, m = map(int, tstr.split(":"))
        return h * 60 + m

    def _now_minutes(self):
        now = datetime.now()
        return now.hour * 60 + now.minute

    def _in_window(self, start, end, current):
        """Handles normal and midnight-crossing windows."""
        if start <= end:
            return start <= current < end
        else:
            return current >= start or current < end

    # -------------------------------------------------------------
    # Core logic
    # -------------------------------------------------------------
    def run_once(self):
        """
        Called by the worker thread once per loop.
        Checks windows and kills processes when needed.
        Returns: True if any process was killed.
        """
        current = self._now_minutes()
        killed_any = False

        for w in self.windows:
            if self._in_window(w["start"], w["end"], current):
                result = self._kill_matching(w["processes"])
                if result:
                    killed_any = True

        return killed_any

    def _kill_matching(self, target_names):
        """Kill running processes whose names match target_names (case-insensitive)."""
        target_set = set(target_names)
        killed_any = False

        for proc in psutil.process_iter(["name", "pid"]):
            name = proc.info.get("name")
            if not name:
                continue

            if name.lower() in target_set:
                try:
                    pid = proc.info["pid"]
                    proc.terminate()
                    killed_any = True
                    self.last_kill_time = datetime.now()
                    self._log_kill(name, pid)
                except Exception:
                    pass  # MVP: ignore

        return killed_any

    # -------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------
    def _log_kill(self, name, pid):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] Killed: {name} (PID {pid})\n"
        with open(self.kill_log_path, "a", encoding="utf-8") as f:
            f.write(line)
