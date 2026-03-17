# Projects
read_when: managing the private project catalog that feeds portfolio and tracks deployment/runtime details

HQ keeps a separate project registry for both public publishing decisions and private operations details.

Core ideas
- A project is not the same thing as a runnable HQ tool.
- HQ owns the canonical project records.
- HQ also owns a separate host registry for runner routing.
- Portfolio consumes only a sanitized export JSON file.
- Portfolio publish happens through a dedicated `dimy.dev` git clone on the same host as HQ.
- Public ordering is controlled only by `sort_order`.
- Health state is observed on demand and not stored as long-term uptime history.
- `GET /projects` is intentionally fast and returns cached or unchecked health state; the dashboard refreshes health separately in the background.
- Project actions are routed through the host named by `deployment_host`, ideally through that host's runner when HQ itself is containerized.

Stored fields
- `slug`
- `title`
- `public_summary`
- `public_mode`: `hidden | demo | full | source`
- `primary_url`
- `repo_url`
- `sort_order`
- `linked_tools`
- `depends_on`
- `private_url`
- `deployment_host`
- `deployment_location`
- `runtime_path`
- `health_public_url`
- `health_private_url`
- `deploy_command`
- `start_command`
- `restart_command`
- `stop_command`
- `logs_command`

Validation rules
- Any non-empty URL field must be a full `http` or `https` URL.
- `demo` and `full` projects must include a valid `primary_url`.
- `source` projects must include a valid `repo_url`.
- `source` projects may also keep a `primary_url`, but portfolio will not show it while in `source` mode.
- Action commands are optional plain shell-command strings.
- `depends_on` stores explicit project slugs for dependency-aware status in HQ.
- In Docker deployments, project actions should execute through the host action runner so commands can access host paths, Docker Compose, and systemd/journalctl.

Runtime storage
- Registry file: `runtime/projects/projects.json`
- Host registry file: `runtime/hosts/hosts.json`
- Default export target: `runtime/projects/projects.generated.json`
- Optional portfolio sync target:
  - `HQ_PORTFOLIO_EXPORT_PATH`
  - if unset, HQ auto-detects a sibling repo at `../dimy.dev/data/projects.generated.json` when present
- Override with env:
  - `HQ_PROJECTS_PATH`
  - `HQ_PROJECTS_EXPORT_PATH`
  - `HQ_PORTFOLIO_REPO_DIR`
  - `HQ_PORTFOLIO_EXPORT_PATH`
  - `HQ_PORTFOLIO_BRANCH`

Controller routes
- `GET /hosts`
  - returns each host plus cached or unchecked `runner_snapshot`
- `POST /hosts/refresh-health`
  - computes fresh runner reachability for all configured hosts
- `POST /hosts`
- `PUT /hosts/{slug}`
- `DELETE /hosts/{slug}`
- `GET /projects`
  - returns each project plus cached or unchecked `host`, `host_snapshot`, `health_snapshot`, `dependency_snapshot`, and `ops_summary`
- `POST /projects/refresh-health`
  - computes fresh health for all configured projects and returns the updated project list
- `POST /projects`
- `PUT /projects/{slug}`
- `DELETE /projects/{slug}`
- `POST /projects/{slug}/health-check`
- `POST /projects/{slug}/action`
- `POST /projects/export`
  - writes the sanitized export JSON
  - also syncs the same public JSON into the portfolio repo when `HQ_PORTFOLIO_EXPORT_PATH` is configured or the local sibling `dimy.dev` repo is present
- `POST /projects/publish`
  - validates the configured `dimy.dev` repo state
  - writes `data/projects.generated.json`
  - commits only that file with a fixed message
  - pushes to the configured branch so GitHub/Vercel can pick up the change

Action request body
```json
{ "action": "deploy" }
```

Supported actions:
- `deploy`
- `start`
- `restart`
- `stop`
- `logs`

Health response shape
- `summary`: `healthy | degraded | down | unconfigured`
- `checks.public`
- `checks.private`

Dependency/runtime response additions on `GET /projects`
- `host`
- `host_snapshot`
- `health_snapshot`
- `dependency_snapshot.summary`: `healthy | degraded | down | none`
- `dependency_snapshot.items`
- `ops_summary`: combined project/dependency status for the dashboard card

Host registry fields
- `slug`
- `title`
- `transport`: `none | socket | http`
- `runner_url`
- `runner_socket_path`
- `token_env_var`
- `location`
- `notes`

Host routing rules
- `deployment_host` should match a host slug in the host registry.
- `socket` hosts are intended for same-machine Docker-to-host communication, like HQ on `srv`.
- `http` hosts are intended for remote runners over Tailscale, like `desk` or `aws`.
- `http` hosts must define `token_env_var`, and HQ must be able to resolve a non-empty token from that env var before actions will route to the runner.
- `none` means HQ can still track deployment metadata for that host, but it cannot run actions there.
- If `deployment_host` is blank, HQ does not use a host runner. Actions run locally inside the controller environment instead.
- If `deployment_host` is set but does not match a host record, HQ rejects the action instead of falling back.
- Hosts cannot be deleted while any project still references them via `deployment_host`.

Export script
```bash
python bin/export-portfolio-projects.py
```

This writes to the HQ runtime export path by default, which is safe for the
deployed container. It also syncs the portfolio copy when a portfolio export
path is configured or auto-detected.

Optional explicit export path:
```bash
python bin/export-portfolio-projects.py /path/to/projects.generated.json
```

For local portfolio updates, pass the portfolio repo path explicitly:
```bash
python bin/export-portfolio-projects.py /home/dim/Projects/dimy.dev/data/projects.generated.json
```

Recommended env for a stable local/dev sync target:
```bash
HQ_PORTFOLIO_EXPORT_PATH=/home/dim/Projects/dimy.dev/data/projects.generated.json
```

Recommended env for the Docker deployment on `srv`:
```bash
HQ_PORTFOLIO_REPO_HOST_DIR=/srv/stacks/dimy.dev
HQ_PORTFOLIO_REPO_DIR=/portfolio-repo
HQ_PORTFOLIO_EXPORT_PATH=/portfolio-repo/data/projects.generated.json
HQ_PORTFOLIO_BRANCH=main
```

Publish safety rules
- The portfolio repo must be on the configured branch before publish runs.
- The repo must be clean except for `data/projects.generated.json`.
- HQ only commits the generated catalog file; portfolio code/layout stays managed in the portfolio repo itself.
