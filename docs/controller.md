# Controller API
read_when: integrating UI or debugging tools

Endpoints
- `GET /dashboard` html dashboard
- `GET /dashboard/job-applications?days=365` grouped daily job-application counts (from Jobber DB)
- `GET /tools` list tools from DB + manifest UI fields (`auto_start`, `title`, `category`)
- `GET /tools/status-all` batch status check
- `POST /tools/{name}/launch` start tool
- `POST /tools/{name}/kill` stop tool
- `POST /tools/{name}/auto-start` persist auto-start in `tools/<name>/tool.json`
- `GET /tools/{name}/alive` process alive check
- `POST /tools/register` add tool to DB
- `GET|POST /api/tools/{name}/{action}` simple JSON proxy to a tool action (legacy helper)
- `GET|POST|PUT|PATCH|DELETE|OPTIONS /proxy/{name}/{path}` full HTTP proxy for tool routes/widgets

Proxy notes
- Dashboard/tool widgets should use `/proxy/{name}/...` for broad HTTP compatibility.
- `GET /api/tools/{name}/{action}` only forwards one action segment and supports `GET`/`POST`.
