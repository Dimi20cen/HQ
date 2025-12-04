import subprocess
import platform
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def venv_python():
    if platform.system() == "Windows":
        return BASE_DIR / ".venv" / "Scripts" / "python.exe"
    return BASE_DIR / ".venv" / "bin" / "python"

def main():
    python = venv_python()

    subprocess.call([
        str(python), "-m", "uvicorn",
        "controller.controller_main:app",
        "--host", "127.0.0.1",
        "--port", "8000",
        "--reload"
    ])

if __name__ == "__main__":
    main()
