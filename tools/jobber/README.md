# jobber

Collect job postings and generate cover letters from job pages using the local Gemini CLI.

## Setup

1. Load the extension:
   - Chrome → `chrome://extensions`
   - Enable Developer Mode
   - “Load unpacked” → select `~/Projects/HQ/tools/jobber/job-jsonifier`

2. Start the local tool:
   - Via controller, or run directly:
     ```bash
     python /home/dim/Projects/HQ/tools/jobber/main.py
     ```

3. Open a job page, click the Jobber extension, then **Refill** and **Generate Letter**.

## Config

Edit `jobber.config.json` (paths relative to `tools/jobber` unless absolute):
- `infoFile`: your resume/summary markdown
- `outputDir`: where to write letters (default `cover-letter`)
- `codex`: true/false (default false)
- `codex_reasoningEffort`: codex-only override (`low|medium|high|xhigh`)
- `gemini`: true/false (default true)
- `geminiCli`: gemini executable name/path (default `gemini`)
- `geminiArgs`: extra args list (optional)
- `geminiModelFlag`: model flag (default `--model`, set empty to disable)
- `model`: optional model override (empty = CLI default)

Env overrides (optional):
- `COVLET_INFO_FILE`
- `COVLET_OUTPUT_DIR`
- `COVLET_MODEL`
- `COVLET_PROVIDER`
- `COVLET_GEMINI_CLI`
- `COVLET_GEMINI_ARGS`
- `COVLET_GEMINI_MODEL_FLAG`
- `COVLET_REASONING_EFFORT`
- `COVLET_PROMPT_LOG` (path for last prompt dump)

## Output

Letters are written to:
- `<outputDir>/<slug>.txt` (default `tools/jobber/cover-letter`)

## Endpoints

- `POST /check` → check if a job URL exists
- `POST /save` → upsert job data
- `POST /delete` → delete by URL
- `POST /generate` → generate cover letter
- `GET /generate-status/{jobId}` → poll generation status
- `POST /open-output` → reveal output file in file explorer
