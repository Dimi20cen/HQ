# Controller API
read_when: integrating UI or debugging tools

Endpoints
- `GET /dashboard` html dashboard
- `GET /tools` list tools from DB + manifest UI fields (`auto_start`, `title`, `category`)
- `GET /tools/status-all` batch status check
- `POST /tools/{name}/launch` start tool
- `POST /tools/{name}/kill` stop tool
- `POST /tools/{name}/auto-start` persist auto-start in `tools/<name>/tool.json`
- `GET /tools/{name}/alive` process alive check
- `POST /tools/register` add tool to DB
- `GET|POST /api/tools/{name}/{action}` proxy to tool endpoint
