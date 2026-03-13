# Downloader Tool Guide
read_when: using or debugging HQ downloader behavior

Downloader queues media downloads and saves files to a shared folder for easy access from the widget or filesystem.

## Runtime

- Tool path: `tools/downloader/main.py`
- Default port: `9020`
- Output directory: `shared/downloads/`
- Manifest: `tools/downloader/tool.json`

## Setup

1. Install deps:
   - `pip install -r tools/downloader/requirements.txt`
2. Optional but recommended for site scanning/login flows:
   - `playwright install chromium`
3. Run tool directly:
   - `.venv/bin/python tools/downloader/main.py`
   - or start from HQ controller dashboard.

## API

- `GET /health` (from `BaseTool`)
- `GET /manifest` (from `BaseTool`)
- `GET /widget` (from `BaseTool`)
- `GET /list`
  - returns downloaded files in `shared/downloads`
- `POST /start`
  - body: `{ "url": "https://...", "mode": "video|audio", "use_login": false }`
  - returns: `{ "job_id": "...", "status": "started" }`
- `POST /cancel/{job_id}`
- `GET /status/{job_id}`
- `POST /open_folder`
  - asks OS to open `shared/downloads`
- `GET /files/<name>`
  - static file serving from download directory

## Job Lifecycle

Common status values from `/status/{job_id}`:
- `pending`
- `downloading`
- `cancelling`
- `cancelled`
- `done`
- `error`

## Notes

- `use_login` currently attempts browser-cookie bridging for restricted pages.
- Downloads are processed via a background queue with worker threads.
- Tool keeps lightweight history in `shared/downloads/history.json`.
