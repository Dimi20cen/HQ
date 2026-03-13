# Blocker Tool Guide
read_when: configuring process-block windows and service behavior

Focus Blocker watches running processes and terminates configured executables during configured time windows.

## Runtime

- Tool path: `tools/blocker/main.py`
- Default port: `9001`
- Config file: `tools/blocker/config.json`
- Kill log file: `tools/blocker/logs/kills.log`

## Setup

1. Edit `tools/blocker/config.json`.
2. Start via controller, or run directly:
   - `.venv/bin/python tools/blocker/main.py`
3. Use `/status` to verify worker state and loaded windows.

## Config Shape

```json
{
  "check_interval_seconds": 3,
  "blocked_windows": [
    {
      "start": "05:00",
      "end": "19:00",
      "processes": ["example.exe", "another.exe"]
    }
  ]
}
```

Notes:
- Time format is `HH:MM` (24-hour).
- Window logic supports ranges crossing midnight.
- Process-name matching is case-insensitive.

## API

- `GET /health` (from `BaseTool`)
- `GET /manifest` (from `BaseTool`)
- `GET /widget` (from `BaseTool`)
- `GET /status`
- `POST /start`
- `POST /stop`
- `POST /reload`
- `POST /update-config`

## Safety Notes

- This tool can terminate any matching process name, so keep process lists specific.
- Test with low-impact processes before adding critical apps.
