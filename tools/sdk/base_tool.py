import json
import uvicorn
import sys
from pathlib import Path
from typing import Callable, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

class BaseTool:
    def __init__(self, file_path: str):
        """
        :param file_path: Pass __file__ from your main.py so we can find tool.json
        """
        self.root_dir = Path(file_path).parent.resolve()
        self.config_path = self.root_dir / "tool.json"

        if not self.config_path.exists():
            raise FileNotFoundError(f"Missing tool.json in {self.root_dir}")

        # 1. Load Config (Single Source of Truth)
        with open(self.config_path, "r") as f:
            self.config = json.load(f)

        self.name = self.config["name"]
        self.port = self.config["port"]
        self.title = self.config.get("title", self.name.replace("_", " ").title())
        self.version = self.config.get("version", "0.1.0")

        # 2. Lifecycle Hooks Storage
        self._on_startup: Optional[Callable] = None
        self._on_shutdown: Optional[Callable] = None

        # 3. Initialize FastAPI with Lifespan
        self.app = FastAPI(
            title=self.title, 
            version=self.version, 
            lifespan=self._lifespan
        )

        # 4. Standard CORS (Crucial for Dashboard/Extension)
        self.app.add_middleware(
            CORSMiddleware,
            # 1. ALLOW DASHBOARD (Exact Match)
            allow_origins=[
                "http://localhost:8000",
                "http://127.0.0.1:8000"
            ],
            # 2. ALLOW EXTENSIONS (Pattern Match)
            allow_origin_regex="chrome-extension://.*",
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # 5. Register Core Routes
        self._register_core_routes()

    # --- Lifecycle Management ---
    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        # Startup
        if self._on_startup:
            # Handle both async and sync hooks
            if is_async(self._on_startup):
                await self._on_startup()
            else:
                self._on_startup()
        
        yield
        
        # Shutdown
        if self._on_shutdown:
            if is_async(self._on_shutdown):
                await self._on_shutdown()
            else:
                self._on_shutdown()

    def set_startup_hook(self, func: Callable):
        """Set a function to run when the tool starts."""
        self._on_startup = func

    def set_shutdown_hook(self, func: Callable):
        """Set a function to run when the tool stops."""
        self._on_shutdown = func

    # --- Routing Helpers ---
    def _register_core_routes(self):
        @self.app.get("/manifest")
        def manifest():
            return self.config

        @self.app.get("/health")
        def health():
            return {"status": "ok", "tool": self.name}

    def add_widget_route(self, html_generator_func):
        """Helper to register the widget UI."""
        self.app.get("/widget", response_class=HTMLResponse)(html_generator_func)

    def run(self):
        """Standard launcher."""
        # CHANGED: Removed rocket emoji to prevent Windows UnicodeEncodeError
        print(f"[*] [{self.title}] Starting on http://127.0.0.1:{self.port}")
        uvicorn.run(self.app, host="127.0.0.1", port=self.port)

# Helper to check if a function is async
import inspect
def is_async(func):
    return inspect.iscoroutinefunction(func)