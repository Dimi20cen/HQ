# HQ Theme Guidelines
read_when: changing dashboard or tool widget UI colors

## Goal
Standardize HQ visuals around a cherry-blossom palette that stays readable and consistent across states.

## Canonical Palette
- `--bg`: `#e7e9ff` (sky base)
- `--bg-accent`: `#ead7f2` (soft blossom wash)
- `--card`: `#fff9fd` (cloud white panel)
- `--surface`: `#fdf5fb` (nested panel)
- `--text`: `#372f56` (primary ink)
- `--muted`: `#756d95` (secondary text)
- `--border`: `rgba(143, 119, 171, 0.28)` (stroke)
- `--card-edge`: `#f0bddb` (card top accent)
- `--control-icon`: `#755f98` (icon/action ink)
- `--chip`: `#f6daed` (neutral chip fill)
- `--job-heat-0`: `#f4e9f3` (no applications)
- `--job-heat-1`: `#d9f0e3` (low daily volume)
- `--job-heat-2`: `#a6debe` (medium daily volume)
- `--job-heat-3`: `#6ac391` (high daily volume)
- `--job-heat-4`: `#3b9d72` (max daily volume)

## Semantic Status Colors
- `--status-running`: `#3b9d72`
- `--status-stopped`: `#cf5e97`
- `--status-busy`: `#bc8f5a`
- `--status-info`: `#6b83d9`

Status chip variants:
- `--chip-running-hidden-bg` / `--chip-running-hidden-text`
- `--chip-running-visible-bg` / `--chip-running-visible-text`
- `--chip-stopped-bg` / `--chip-stopped-text`

## Rules
- Always use semantic tokens in CSS (`--status-*`, `--chip-*`, `--text`, `--border`) instead of hardcoded hex values.
- Keep status semantics stable:
  - Running/success: green family
  - Stopped/error: blossom pink family
  - Busy/loading: warm gold family
  - Info/links: sky blue family
- Tool widgets should prefer a muted, flat visual treatment:
  - minimal/no gradients
  - low-contrast borders
  - subtle or no drop shadows
- Contribution/heatmap visuals should use the `--job-heat-*` tokens for level scaling.
- Preserve contrast for text and controls; avoid light-on-light combinations for labels or icons.
- Add new tokens in `:root` before usage and document them in this file.

## Current Scope
- Dashboard theme lives in `controller/static/dashboard.css`.
- Tool widget implementations currently aligned in:
  - `tools/calendar/widget.py`
  - `tools/blocker/main.py`
  - `tools/downloader/main.py`
  - `tools/jobber/main.py`
  - `tools/meditator/main.py`
- For new tools or pages, reuse these tokens first; only extend when needed.
