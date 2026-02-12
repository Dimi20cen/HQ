import subprocess
import platform
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def venv_python():
    if platform.system() == "Windows":
        return BASE_DIR / ".venv" / "Scripts" / "python.exe"
    return BASE_DIR / ".venv" / "bin" / "python"

def main():
    python = venv_python()
    host = os.getenv("CONTROLLER_HOST", "0.0.0.0")
    port = os.getenv("CONTROLLER_PORT", "8000")

    subprocess.call([
        str(python), "-m", "uvicorn",
        "controller.controller_main:app",
        "--host", str(host),
        "--port", str(port),
        "--reload"
    ])

if __name__ == "__main__":
    main()
