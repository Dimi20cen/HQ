# Overview
read_when: need a mental model of HQ

HQ is your private control plane.

It still acts as a local tool hub for the built-in widgets under `tools/`, but it now also owns:
- a private project catalog
- host registry + runner routing
- project health/dependency monitoring
- deploy/restart/logs actions across multiple hosts
- portfolio catalog export/publish for `dimy.dev`

Core parts
- Controller: FastAPI app in `controller/` that scans tools, manages processes, exposes the dashboard, and serves the project/host APIs.
- Tools: one folder per tool under `tools/`, each with `tool.json` + `main.py`.
- Project registry: `runtime/projects/projects.json` stores the canonical project records HQ manages.
- Host registry: `runtime/hosts/hosts.json` stores actionable and metadata-only hosts like `srv`, `desk`, `aws`, and `vercel`.
- Host runners: one runner per actionable host; HQ routes project actions and private health checks through the runner for that host.
- Portfolio publish flow: HQ exports a sanitized project catalog and can publish it into the `dimy.dev` repo for GitHub/Vercel.

Current host model
- `srv`: socket-based runner host for HQ, Janus, Hermes, and Jobby
- `desk`: HTTP runner host over Tailscale for Sakura
- `aws`: HTTP runner host over Tailscale for RentPredictor and edge-local operations
- `vercel`: metadata-only host for portfolio deployment; no runner

Data flow
- Controller scans `tools/` on startup and registers tool metadata.
- Dashboard reads controller APIs for tools, hosts, and projects.
- Project actions resolve `deployment_host`, then run through that host's runner when available.
- Private health checks also use the host runner path when needed, so HQ does not depend on the container being able to reach every host-local service directly.
- Portfolio publishing writes the sanitized project catalog into the mounted `dimy.dev` repo and pushes it to GitHub.
