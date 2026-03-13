# Meditator Tool Guide
read_when: using timer sessions, music, and local sound assets

Meditator provides a countdown timer widget with selectable duration, optional background music, and end-of-session sound controls.

## Runtime

- Tool path: `tools/meditator/main.py`
- Default port: `9030`
- Asset directory: `tools/meditator/assets/`

## Setup

1. Install deps:
   - `pip install -r tools/meditator/requirements.txt`
2. Run directly:
   - `.venv/bin/python tools/meditator/main.py`
   - or launch from HQ controller.

## API

- `GET /health` (from `BaseTool`)
- `GET /manifest` (from `BaseTool`)
- `GET /widget` (from `BaseTool`)
- `GET /`
  - simple hello payload
- `GET /assets/{filename}`
  - serves local media assets (path traversal blocked)

## Widget Notes

- Duration picker supports hours/minutes/seconds.
- Optional background-music playback uses local assets.
- Session end sound is configurable in-widget.

## Included Assets

- `tools/meditator/assets/ringtone.mp3`
- `tools/meditator/assets/yoga_30min.mp3`
