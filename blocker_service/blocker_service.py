import threading
import time
from datetime import datetime
from pathlib import Path

from blocker_core import BlockerCore


class BlockerService:
    def __init__(self, config_path="config.json"):
        self.core = BlockerCore(config_path)

        self.running = False          # whether the worker loop is active
        self.thread = None            # worker thread handle
        self.lock = threading.Lock()  # protects self.running and other shared state

    # -------------------------------------------------------------
    # Worker loop management
    # -------------------------------------------------------------
    def start(self):
        """Starts the worker thread if not already running."""
        with self.lock:
            if self.running:
                return False  # already running
            self.running = True

        # Launch worker thread
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        """Stops the worker thread."""
        with self.lock:
            self.running = False
        return True

    def _worker_loop(self):
        """Main loop: runs until stopped."""
        while True:
            with self.lock:
                if not self.running:
                    break

            # Do one cycle of core logic
            self.core.run_once()

            # Sleep based on config interval
            time.sleep(self.core.check_interval)

    # -------------------------------------------------------------
    # Config operations
    # -------------------------------------------------------------
    def reload_config(self):
        """Reload config.json into memory."""
        self.core.load_config()
        return True

    def update_config(self, new_data: dict):
        """
        Update config.json with new data and reload into memory.
        This persists changes.
        """
        self.core.update_config(new_data)
        return True

    # -------------------------------------------------------------
    # Status reporting
    # -------------------------------------------------------------
    def get_status(self):
        """Return current status information as a dict."""
        with self.lock:
            running = self.running

        last_kill = (
            self.core.last_kill_time.strftime("%Y-%m-%d %H:%M:%S")
            if self.core.last_kill_time
            else None
        )

        return {
            "running": running,
            "current_time": datetime.now().strftime("%H:%M"),
            "check_interval_seconds": self.core.check_interval,
            "windows": self.core.windows,
            "last_kill": last_kill,
            "config_path": str(self.core.config_path),
        }
