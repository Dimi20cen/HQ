# Covlet Overview

Purpose: Generate plain-text cover letters from job ads.

## Flow

- Chrome extension injects `content.js` into the active tab on click.
- Content script extracts job title, company, and description text.
- Popup posts data to the local server at `http://127.0.0.1:5055/generate`.
- Server reads `covlet.config.json` + the info markdown, builds a prompt, runs `codex exec`.
- Output saved to `<outputDir>/<slug>.txt` (default `tools/covlet/cover-letter`).

## Key Files

- `extension/manifest.json`: extension permissions and popup setup.
- `extension/content.js`: DOM extraction.
- `extension/popup.js`: inject + POST to server.
- `server/server.js`: prompt building + codex invocation.
- `covlet.config.json`: info file + output directory.
