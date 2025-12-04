import subprocess
import sys
from pathlib import Path
import os
import platform

BASE_DIR = Path(__file__).resolve().parent
VENV_DIR = BASE_DIR / ".venv"

def run(cmd):
    print("> " + " ".join(cmd))
    subprocess.check_call(cmd)

def venv_python():
    """Return path to the python executable inside venv."""
    if platform.system() == "Windows":
        return VENV_DIR / "Scripts" / "python.exe"
    else:
        return VENV_DIR / "bin" / "python"

def venv_pip():
    """Return path to pip inside venv."""
    if platform.system() == "Windows":
        return VENV_DIR / "Scripts" / "pip.exe"
    else:
        return VENV_DIR / "bin" / "pip"

def main():
    # 1. Create the virtual environment if it doesn't exist
    if not VENV_DIR.exists():
        print("Creating virtual environment...")
        run([sys.executable, "-m", "venv", str(VENV_DIR)])
    else:
        print("Virtual environment already exists.")

    # 2. Install dependencies
    print("Installing dependencies...")
    run([str(venv_pip()), "install", "-r", "requirements.txt"])

    print("Setup complete! You can now run the controller with: python run.py")

if __name__ == "__main__":
    main()
