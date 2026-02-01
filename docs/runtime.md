# Runtime
read_when: running HQ locally

Setup (first time)
- `python setup.py` (creates `.venv`, installs root + tool deps)
- `./start.sh` (creates `.venv`, installs root deps only)
- Windows: run `python setup.py`, then `start.bat`
- Manual: `python3 -m venv .venv` then `pip install -r requirements.txt` (+ tool deps as needed)

Start controller
- `python run.py` (uses `.venv` python; auto-reload)
- Serves on `http://127.0.0.1:8000`

Start a tool directly
- `python tools/<tool>/main.py`
- For node tools: `node tools/<tool>/<entry_point>`

Logs
- Tool stdout/stderr: `logs/<tool>.out.log` and `logs/<tool>.err.log`

Ports
- Controller default: 8000
- Tool ports: set per `tool.json`
