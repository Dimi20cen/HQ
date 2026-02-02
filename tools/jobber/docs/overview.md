# Jobber Overview

Purpose: collect job postings and generate plain-text cover letters.

## Flow

- Jobber Chrome extension scrapes the active tab into the popup form.
- Popup can save jobs to the local DB and call `/generate`.
- Server builds a prompt from `jobber.config.json` + info markdown, then runs the Gemini CLI (or Codex if configured).
- Output saved to `<outputDir>/<slug>.txt` (default `tools/jobber/cover-letter`).

## Key Files

- `job-jsonifier/manifest.json`: extension permissions and popup setup.
- `job-jsonifier/popup.js`: scrape + POST to server.
- `main.py`: FastAPI server, DB, and cover letter generation.
- `jobber.config.json`: info file + output directory.
