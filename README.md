# HQ
read_when: start here

HQ is a local tool hub that discovers tools under `tools/`, runs them, and provides a dashboard plus controller API.
It also owns the private project catalog and can export a sanitized public project feed for portfolio publishing.

## Cross-Cutting Docs

- `docs/overview.md`
  - `read_when: need a mental model of HQ`
- `docs/runtime.md`
  - `read_when: running HQ locally or in Docker`
- `docs/tools.md`
  - `read_when: creating or editing tools`
- `docs/controller.md`
  - `read_when: integrating UI, API clients, or debugging controller routes`
- `docs/projects.md`
  - `read_when: managing the project publishing registry for portfolio`
- `docs/theme-guidelines.md`
  - `read_when: changing dashboard or tool widget UI colors`
- `docs/changes.md`
  - `read_when: reviewing notable repo changes and validation history`
- `docs/dashboard-mobile-web-checklist.md`
  - `read_when: validating responsive and accessibility dashboard quality`

## Tool-Specific Docs

- Calendar: `tools/calendar/guide.md`, `tools/calendar/docs/OVERVIEW.md`
- Jobber: `tools/jobber/guide.md`, `tools/jobber/docs/overview.md`
- Downloader: `tools/downloader/guide.md`
- Blocker: `tools/blocker/guide.md`
- Meditator: `tools/meditator/guide.md`

## Quick Start

1. `python setup.py`
2. `python run.py`
3. Open `http://127.0.0.1:8000/dashboard`
