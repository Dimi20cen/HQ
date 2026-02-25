# AGENTS.MD

Read `~/Projects/meta/agent-scripts/AGENTS.md` first.

## Dashboard Theme Standard

- For any HQ dashboard/UI styling work, treat `docs/theme-guidelines.md` as the canonical color and token standard.
- Prefer semantic theme tokens (for example `--status-running`, `--status-stopped`, `--chip-*`) over hardcoded hex values.
- When adding new UI colors, update both `controller/static/dashboard.css` (`:root` tokens) and `docs/theme-guidelines.md`.
