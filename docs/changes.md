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
