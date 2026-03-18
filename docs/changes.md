read_when: reviewing notable behavior/UI/documentation changes and validation status

## 2026-03-18
- Summary: Wired Rent Predictor project actions to the AWS runner by adding its runtime path plus deploy, start/restart, and logs commands so HQ can operate it from the dashboard, and corrected the AWS path/log command after live validation.
- Affected files: `runtime/projects/projects.json`
- Migration notes: Assumes the AWS runner host exposes the app repo at `/home/ubuntu/apps/rentpredictor` and the container name remains `rentpredictor`.
- Validation status: `python3 -m json.tool runtime/projects/projects.json` passed.

## 2026-03-18
- Summary: Kept expanded project rows open while running health checks or actions by updating row-open state immediately instead of waiting for a later DOM capture during rerenders.
- Affected files: `controller/static/dashboard.js`
- Migration notes: No API or data-shape changes.
- Validation status: `node --check controller/static/dashboard.js` passed.

## 2026-03-18
- Summary: Restored lightweight scanability to collapsed project rows by showing public mode, deployment host, and last-checked time beneath each project title while keeping the simpler sidebar structure.
- Affected files: `controller/static/dashboard.css`, `controller/static/dashboard.js`
- Migration notes: No API or data-shape changes.
- Validation status: `node --check controller/static/dashboard.js` and `python3 -m pytest tests/test_project_ops_api.py tests/test_projects_registry.py tests/test_hosts_registry.py tests/test_portfolio_publish.py` passed.

## 2026-03-18
- Summary: Simplified the Projects sidebar by removing the duplicate expanded-card header and repeated summary chips/links/health blocks, consolidating project status into one compact panel, and turning `Public`/`Runtime`/`Health`/`Actions` into individually collapsible sections.
- Affected files: `controller/static/dashboard.css`, `controller/static/dashboard.js`
- Migration notes: No API or data-shape changes. Project actions, inline action output, and in-place configuration editing still work from the same Projects panel.
- Validation status: `node --check controller/static/dashboard.js` passed. Manual dashboard verification is still recommended for project-row scanning, action feedback, and responsive layout.

## 2026-03-18
- Summary: Redesigned the dashboard into a tools-first command strip with status pills and slide-over Projects/Hosts panels, and fixed the panel accessibility model so closed drawers are `hidden`/`inert` instead of remaining tabbable off-canvas.
- Affected files: `controller/templates/dashboard.html`, `controller/static/dashboard.css`, `controller/static/dashboard.js`, `docs/theme-guidelines.md`, `docs/dashboard-mobile-web-checklist.md`
- Migration notes: The old top-panel job-application heatmap is no longer part of the dashboard UI. Projects and Hosts now open in modal side panels from the command strip.
- Validation status: `node --check controller/static/dashboard.js` passed. Manual browser validation is still recommended for panel focus trapping and responsive behavior.

## 2026-03-18
- Summary: Enabled the `aws` host as a real HTTP runner, configured RentPredictor in HQ with AWS deployment metadata/public health, and repaired live GitHub auth for `POST /projects/publish` on `srv`.
- Affected files: `runtime/hosts/hosts.json`, `runtime/projects/projects.json`, `runtime/projects/projects.generated.json`, `docs/overview.md`, `docs/runtime.md`
- Migration notes: `aws` now expects `HQ_ACTION_RUNNER_TOKEN_AWS` on the HQ server env and a running `hq-action-runner` service on the Lightsail host.
- Validation status: live `POST /hosts/refresh-health` reports `aws` healthy, live `POST /projects/publish` returns `200`, and RentPredictor now reports healthy in `POST /projects/refresh-health`.

## 2026-03-18
- Summary: Changed private project health checks to route through the project's host runner when available, so HQ no longer reports false negatives for host-local services that are unreachable directly from the HQ container.
- Affected files: `controller/controller_main.py`, `host_runner/server.py`, `tests/test_project_ops_api.py`
- Migration notes: host runners now serve `POST /check-url` in addition to `GET /health` and `POST /run`; restart runner services after deploying this change.
- Validation status: `python3 -m pytest tests/test_project_ops_api.py tests/test_projects_registry.py tests/test_hosts_registry.py tests/test_portfolio_publish.py`, `python3 -m py_compile controller/controller_main.py host_runner/server.py`, and live `POST /projects/refresh-health` showed `hermes` and `jobby` healthy after restarting the runners.

## 2026-03-17
- Summary: Added a real host registry and multi-host runner routing so HQ can target one runner per host, show runner health in the dashboard, and route project actions by `deployment_host` instead of a single global runner setting.
- Affected files: `controller/controller_main.py`, `controller/hosts_registry.py`, `controller/static/dashboard.css`, `controller/static/dashboard.js`, `controller/templates/dashboard.html`, `docs/controller.md`, `docs/projects.md`, `docs/runtime.md`, `runtime/hosts/hosts.json`, `tests/test_hosts_registry.py`, `tests/test_project_ops_api.py`
- Migration notes: Keep `srv` on the existing socket runner, then add remote host records like `desk` and `aws` with `transport: "http"`, `runner_url`, and a host-specific token env var such as `HQ_ACTION_RUNNER_TOKEN_DESK`. Projects should point `deployment_host` at one of those host slugs.
- Validation status: `python3 -m pytest tests/test_hosts_registry.py tests/test_project_ops_api.py tests/test_projects_registry.py tests/test_portfolio_publish.py`, `python3 -m py_compile controller/controller_main.py controller/projects_registry.py controller/hosts_registry.py controller/portfolio_publish.py host_runner/server.py`, and `node --check controller/static/dashboard.js` passed.

## 2026-03-17
- Summary: Added a host action runner pattern for Docker-deployed HQ so project actions can execute on `srv` instead of inside the HQ container, and wired the controller to forward actions to that runner when configured.
- Affected files: `controller/controller_main.py`, `docker-compose.yml`, `docs/controller.md`, `docs/projects.md`, `docs/runtime.md`, `ops/systemd/hq-action-runner.service`, `host_runner/server.py`, `runtime/projects/projects.json`, `tests/test_project_ops_api.py`
- Migration notes: Configure `HQ_ACTION_RUNNER_SOCKET_HOST_PATH`, `HQ_ACTION_RUNNER_SOCKET_PATH`, and `HQ_ACTION_RUNNER_TOKEN` in `/srv/stacks/hq/.env`, install the sample `hq-action-runner.service` user unit on `srv`, and let the HQ container talk to the runner through the shared `runtime` socket.
- Validation status: `python3 -m pytest tests/test_project_ops_api.py`, `python3 -m py_compile controller/controller_main.py host_runner/server.py`, and `node --check controller/static/dashboard.js` passed.

## 2026-03-17
- Summary: Made project ops cards load immediately by serving cached/unchecked project status from `GET /projects` and moving full health refresh to a separate background endpoint.
- Affected files: `controller/controller_main.py`, `controller/static/dashboard.css`, `controller/static/dashboard.js`, `docs/controller.md`, `docs/projects.md`, `tests/test_project_ops_api.py`
- Migration notes: Dashboard health now refreshes through `POST /projects/refresh-health`; initial project loads no longer block on live health checks.
- Validation status: `python3 -m pytest tests/test_project_ops_api.py`, `python3 -m py_compile controller/controller_main.py`, and `node --check controller/static/dashboard.js` passed.

## 2026-03-17
- Summary: Refactored project management into ops-first dashboard cards with live computed health/dependency state, inline logs/deploy/restart actions, expandable configuration, and seeded runtime metadata for `hq`, `jobby`, `janus`, and `hermes`.
- Affected files: `controller/controller_main.py`, `controller/projects_registry.py`, `controller/static/dashboard.css`, `controller/static/dashboard.js`, `runtime/projects/projects.json`, `docs/controller.md`, `docs/projects.md`, `tests/test_projects_registry.py`, `tests/test_project_ops_api.py`
- Migration notes: Project records now support `depends_on` and `logs_command`. `GET /projects` includes computed `health_snapshot`, `dependency_snapshot`, and `ops_summary`. The dashboard auto-refreshes project health/state unless there are unsaved project edits.
- Validation status: `node --check controller/static/dashboard.js`, `python3 -m py_compile controller/controller_main.py controller/projects_registry.py`, and `python3 -m pytest tests/test_projects_registry.py tests/test_project_ops_api.py` passed.

## 2026-03-17
- Summary: Added a dedicated portfolio publish flow so HQ can validate a `dimy.dev` repo clone, update `data/projects.generated.json`, commit only that generated file, and push to GitHub for Vercel-triggered deploys; also split dashboard actions into `Export Catalog` and `Publish Portfolio`.
- Affected files: `controller/portfolio_publish.py`, `controller/controller_main.py`, `controller/templates/dashboard.html`, `controller/static/dashboard.css`, `controller/static/dashboard.js`, `docker-compose.yml`, `docs/controller.md`, `docs/projects.md`, `docs/runtime.md`, `tests/test_projects_registry.py`, `tests/test_project_ops_api.py`, `tests/test_portfolio_publish.py`
- Migration notes: Configure `HQ_PORTFOLIO_REPO_HOST_DIR`, `HQ_PORTFOLIO_REPO_DIR`, `HQ_PORTFOLIO_EXPORT_PATH`, and `HQ_PORTFOLIO_BRANCH` on `srv`, and mount the dedicated `dimy.dev` repo clone into the HQ container.
- Validation status: `node --check controller/static/dashboard.js`, `python3 -m py_compile controller/controller_main.py controller/projects_registry.py controller/portfolio_publish.py`, and `python3 -m pytest tests/test_projects_registry.py tests/test_project_ops_api.py tests/test_portfolio_publish.py` passed. Follow-up runtime fixes: HQ Docker image now installs `git` for live publish actions and marks `/portfolio-repo` as a safe Git directory.

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
- Summary: Added a compact square dashboard top-panel GitHub-style job-application heatmap (last 14 days) with an icon header and no legend/summary text, powered by a controller endpoint that aggregates Jobber DB daily counts. This UI was later removed in the 2026-03-18 tools-first redesign.
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
