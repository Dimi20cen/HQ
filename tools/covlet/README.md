# covlet

Generate cover letters from job pages using your local Codex CLI.

## Setup

1. Load the extension:
   - Chrome → `chrome://extensions`
   - Enable Developer Mode
   - “Load unpacked” → select `~/Projects/HQ/tools/covlet/extension`

2. Start the local server:
   ```bash
   node /home/dim/Projects/HQ/tools/covlet/server/server.js
   ```

3. Open a job page, click the Covlet extension, then **Generate**.

## Config

Edit `covlet.config.json` (paths relative to `tools/covlet` unless absolute):
- `infoFile`: your resume/summary markdown
- `outputDir`: where to write letters (default `cover-letter`)
- `model`: optional codex model override (empty = CLI default)
- `reasoningEffort`: optional override (`low|medium|high|xhigh`)

Env overrides (optional):
- `COVLET_INFO_FILE`
- `COVLET_OUTPUT_DIR`
- `COVLET_MODEL`
- `COVLET_REASONING_EFFORT`
- `COVLET_PORT` / `COVLET_HOST`
- `COVLET_PROMPT_LOG` (path for last prompt dump)

## Output

Letters are written to:
- `<outputDir>/<slug>.txt` (default `tools/covlet/cover-letter`)

## Notes

- Server uses `codex exec` under the hood.
- If a company name is missing, it falls back to role/title (else `unknown-company`).
