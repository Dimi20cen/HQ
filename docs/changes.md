read_when: reviewing notable behavior/UI/documentation changes and validation status

## 2026-03-17
- Summary: Added a dedicated portfolio publish flow so HQ can validate a `dimy.dev` repo clone, update `data/projects.generated.json`, commit only that generated file, and push to GitHub for Vercel-triggered deploys; also split dashboard actions into `Export Catalog` and `Publish Portfolio`.
- Affected files: `controller/portfolio_publish.py`, `controller/controller_main.py`, `controller/templates/dashboard.html`, `controller/static/dashboard.css`, `controller/static/dashboard.js`, `docker-compose.yml`, `docs/controller.md`, `docs/projects.md`, `docs/runtime.md`, `tests/test_projects_registry.py`, `tests/test_project_ops_api.py`, `tests/test_portfolio_publish.py`
- Migration notes: Configure `HQ_PORTFOLIO_REPO_HOST_DIR`, `HQ_PORTFOLIO_REPO_DIR`, `HQ_PORTFOLIO_EXPORT_PATH`, and `HQ_PORTFOLIO_BRANCH` on `srv`, and mount the dedicated `dimy.dev` repo clone into the HQ container.
- Validation status: `node --check controller/static/dashboard.js`, `python3 -m py_compile controller/controller_main.py controller/projects_registry.py controller/portfolio_publish.py`, and `python3 -m pytest tests/test_projects_registry.py tests/test_project_ops_api.py tests/test_portfolio_publish.py` passed. Follow-up runtime fix: HQ Docker image now installs `git` for live publish actions.

## 2026-02-27
- Summary: Consolidated repo docs entrypoint to a single root `README.md`, renamed secondary README files to non-README docs, and standardized `read_when` hints on cross-cutting docs.
- Affected files: `README.md`, `docs/index.md`, `docs/changes.md`, `docs/dashboard-mobile-web-checklist.md`, `tools/calendar/guide.md` (renamed from `tools/calendar/README.md`), `tools/jobber/guide.md` (renamed from `tools/jobber/README.md`)
- Migration notes: Use root `README.md` as the canonical start page. Tool docs moved to `guide.md` filenames for calendar/jobber.
- Validation status: `rg --files -g 'README.md'` returns only root `README.md`.

## 2026-02-27
- Summary: Converted downloader documentation from an unstructured TODO note into a proper `guide.md` with setup, API, lifecycle statuses, and output-path conventions.
- Affected files: `tools/downloader/guide.md` (renamed from `tools/downloader/README`), `README.md`
- Migration notes: Refer to `tools/downloader/guide.md` for downloader usage and endpoints.
- Validation status: Documentation update only.

## 2026-02-27
- Summary: Completed docs audit follow-up by documenting controller proxy routes, clarifying local-vs-docker DB paths, adding blocker/meditator guides, and removing environment-specific Jobber host assumptions from docs.
- Affected files: `docs/controller.md`, `docs/runtime.md`, `tools/blocker/guide.md`, `tools/meditator/guide.md`, `tools/jobber/guide.md`, `README.md`
- Migration notes: Use `/proxy/{name}/{path}` for full tool HTTP proxying; set DB path env vars explicitly when deviating from defaults.
- Validation status: Documentation update only.

## 2026-02-25
- Summary: Added a compact square dashboard top-panel GitHub-style job-application heatmap (last 14 days) with an icon header and no legend/summary text, powered by a controller endpoint that aggregates Jobber DB daily counts.
- Affected files: `controller/controller_main.py`, `controller/templates/dashboard.html`, `controller/static/dashboard.css`, `controller/static/dashboard.js`, `docs/controller.md`, `docs/theme-guidelines.md`
- Migration notes: None. If using a non-default Jobber database path, set `JOBBER_DB_PATH` for the controller process.
- Validation status: `node --check controller/static/dashboard.js` and `python3 -m py_compile controller/controller_main.py` passed.

## 2026-02-25
- Summary: Tuned tool widget theming to be more muted and flat (reduced gradients/shadows and softened accents) while retaining the shared HQ blossom token family.
- Affected files: `tools/blocker/main.py`, `tools/downloader/main.py`, `tools/jobber/main.py`, `tools/calendar/widget.py`, `tools/meditator/main.py`, `docs/theme-guidelines.md`
- Migration notes: Tool widgets should default to muted/flat styling unless a tool explicitly needs stronger visual hierarchy.
- Validation status: `python3 -m py_compile tools/blocker/main.py tools/downloader/main.py tools/jobber/main.py tools/meditator/main.py tools/calendar/widget.py` passed.

## 2026-02-25
- Summary: Propagated the cherry-blossom HQ theme to built-in tool widgets (calendar, blocker, downloader, jobber, meditator) and expanded theme-guideline scope to include tool UIs.
- Affected files: `tools/calendar/widget.py`, `tools/blocker/main.py`, `tools/downloader/main.py`, `tools/jobber/main.py`, `tools/meditator/main.py`, `docs/theme-guidelines.md`
- Migration notes: New tool widgets should start from the shared HQ semantic tokens/colors.
- Validation status: `python3 -m py_compile tools/blocker/main.py tools/downloader/main.py tools/jobber/main.py tools/meditator/main.py tools/calendar/widget.py` passed.

## 2026-02-25
- Summary: Updated repo `AGENTS.md` so agents explicitly follow the canonical HQ theme guidelines and semantic color-token usage for dashboard/UI changes.
- Affected files: `AGENTS.md`
- Migration notes: None.
- Validation status: Documentation update only.

## 2026-02-25
- Summary: Standardized HQ dashboard color usage with semantic theme/status tokens and added a canonical theme guideline document for future UI work.
- Affected files: `controller/static/dashboard.css`, `docs/theme-guidelines.md`, `docs/README.md`
- Migration notes: Prefer semantic color tokens over hardcoded hex values for new UI styling.
- Validation status: `node --check controller/static/dashboard.js` passed (no JS behavior change).

## 2026-02-25
- Summary: Adjusted the cherry blossom dashboard theme to a more pink-dominant palette based on updated reference art, using stronger sakura pink accents with twilight blue sky tones.
- Affected files: `controller/static/dashboard.css`
- Migration notes: None.
- Validation status: Visual style update only.

## 2026-02-25
- Summary: Replaced Hanafuda tones with an image-matched cherry blossom palette for the dashboard (sky blue, sakura pink, and cloud white) across surfaces, controls, shadows, and status chips.
- Affected files: `controller/static/dashboard.css`
- Migration notes: None.
- Validation status: Visual style update only.

## 2026-02-25
- Summary: Rethemed dashboard visuals to a Hanafuda-inspired palette (parchment surfaces, lacquer red, pine green, muted gold, and ink neutrals) while preserving existing layout and interactions.
- Affected files: `controller/static/dashboard.css`
- Migration notes: None.
- Validation status: Visual style update only.

## 2026-02-25
- Summary: Rebalanced the blossom dashboard theme to a more neutral “sakura steel” look by reducing pink saturation, strengthening neutral surfaces/controls, and simplifying typography to a single sans-serif family.
- Affected files: `controller/static/dashboard.css`, `controller/templates/dashboard.html`
- Migration notes: None.
- Validation status: Visual style update only.

## 2026-02-25
- Summary: Introduced a blossom-cherry dashboard theme with new color tokens, elevated surface styling, expressive typography, and staggered card entrance animation while preserving current dashboard behavior.
- Affected files: `controller/static/dashboard.css`, `controller/templates/dashboard.html`, `controller/static/dashboard.js`
- Migration notes: None.
- Validation status: `node --check controller/static/dashboard.js` passed.

## 2026-02-25
- Summary: Improved dashboard mobile/web usability by adding viewport scaling, always-visible status text, larger touch targets, small-screen layout safeguards, coarse-pointer drag reorder fallback, and a dedicated reorder mode panel with explicit up/down controls; added tool `category` support and a dashboard view-model mapping layer for cleaner UI rendering.
- Affected files: `controller/templates/dashboard.html`, `controller/static/dashboard.css`, `controller/static/dashboard.js`, `controller/controller_main.py`, `create_tool.py`, `docs/tools.md`, `docs/controller.md`, `docs/dashboard-mobile-web-checklist.md`, `tools/*/tool.json`
- Migration notes: None.
- Validation status: `node --check controller/static/dashboard.js`, `python3 -m py_compile controller/controller_main.py controller/db.py controller/process_manager.py create_tool.py`, runtime `GET /dashboard`, `GET /tools`, `GET /tools/status-all`, downloader lifecycle smoke (`launch`, `auto-start on/off`, `kill`), and `/tools` category/title payload check passed.

## 2026-02-25
- Summary: Removed `has_widget` from tool manifests and controller/dashboard logic; widgets are now treated as always available.
- Affected files: `controller/controller_main.py`, `controller/db.py`, `controller/static/dashboard.js`, `create_tool.py`, `tools/*/tool.json`, `docs/tools.md`
- Migration notes: Existing tools should remove `has_widget` from `tool.json`; no behavior toggle remains.
- Validation status: `node --check controller/static/dashboard.js` and `python3 -m py_compile controller/controller_main.py controller/db.py` passed.

## 2026-02-25
- Summary: Added per-tool settings actions in dashboard menus (hide/unhide, auto-start toggle, start/stop toggle), and added a controller API to persist `auto_start` in each tool manifest.
- Affected files: `controller/controller_main.py`, `controller/static/dashboard.js`, `controller/static/dashboard.css`, `controller/templates/dashboard.html`, `docs/controller.md`
- Migration notes: None.
- Validation status: `node --check controller/static/dashboard.js` and `python3 -m py_compile controller/controller_main.py controller/db.py controller/process_manager.py` passed.

## 2026-02-18
- Summary: Added containerized LAN deployment for HQ using Docker Compose, and switched tool state to a single runtime root (`runtime/tools/<tool_name>`) with auto-created state directories.
- Affected files: `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `controller/db.py`, `controller/controller_main.py`, `controller/static/dashboard.js`, `tools/calendar/config.py`, `tools/calendar/store.py`, `tools/jobber/main.py`, `docs/runtime.md`
- Migration notes: Create/update `.env` with `LAN_BIND_IP` and `LAN_BIND_PORT`, then run `docker compose up -d --build`.
- Validation status: `python -m py_compile controller/controller_main.py controller/db.py tools/calendar/config.py tools/calendar/store.py tools/jobber/main.py` passed.

## 2026-02-15
- Summary: Implemented `Meditator` timer widget with selectable duration, optional background music, and configurable end-of-session sound behavior.
- Affected files: `tools/meditator/tool.json`, `tools/meditator/main.py`, `tools/meditator/requirements.txt`
- Migration notes: None.
- Validation status: `python -m py_compile tools/meditator/main.py` passed.
