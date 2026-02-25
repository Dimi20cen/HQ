# Dashboard Mobile + Web Checklist

Goal: make HQ dashboard reliable and comfortable on both mobile and desktop, while reducing overwhelm.

## Phase 1: Critical UX and Responsive Fixes

- [x] Add viewport meta tag to dashboard template.
  - [x] Update `controller/templates/dashboard.html` with `<meta name="viewport" content="width=device-width, initial-scale=1">`.
- [x] Make tool status text visible in cards.
  - [x] Update `controller/static/dashboard.css` so `.status-line` is visible by default.
  - [x] Ensure status remains readable in collapsed/compact layouts.
- [x] Increase tap targets for mobile controls.
  - [x] Raise control sizes (`.btn-status`, `.tool-open-btn`, `.tool-settings-btn`, app menu row buttons) to mobile-safe sizes.
  - [ ] Verify spacing prevents accidental taps.
- [x] Prevent header crowding on narrow screens.
  - [x] Add truncation/wrapping rules for long tool names.
  - [x] Keep action buttons visible and aligned.

## Phase 2: Interaction Model Improvements

- [x] Remove mobile dependency on HTML drag-and-drop.
  - [x] Keep drag reorder for desktop pointer devices.
  - [x] Provide mobile-safe reorder fallback (move up/down actions, or disable reorder on touch with clear messaging).
- [x] Keep critical status visible even when tools are compact/collapsed.
  - [x] Surface running/stopped/error state at all times in the collapsed header.
  - [x] Ensure hidden tools menu also reflects health/state clearly.

## Phase 3: Dashboard Architecture Refinement

- [x] Introduce a small view model layer for tool cards.
  - [x] Normalize UI input fields (`id`, `name`, `type`, `status`, `autoStart`, `alive`, `actions`).
  - [x] Avoid direct ad hoc mapping in rendering code.
- [x] Add first-class tool categories.
  - [x] Support `display`, `background`, and optional `hybrid` tag.
  - [x] Add category filters/sections without duplicating tools across views.
- [ ] Implement collapsed/expanded card modes.
  - [ ] Collapsed: name, status, primary action, quick open.
  - [ ] Expanded: widget/content + advanced settings.
  - [ ] Persist expanded state per user session.

## Phase 4: Validation and Hardening

- [ ] Run responsive checks at common breakpoints (mobile, tablet, desktop).
  - [ ] Test at ~360px, ~768px, and >=1280px widths.
- [ ] Test on real mobile browsers (iOS Safari, Android Chrome if available).
  - [ ] Confirm taps, menus, resize controls, and scrolling behavior.
- [ ] Accessibility pass.
  - [ ] Verify keyboard escape/close behavior.
  - [ ] Verify focus visibility and label clarity for all icon buttons.
- [ ] Regression pass.
  - [x] Ensure launch/kill/auto-start/hide/show flows still work.
  - [ ] Ensure status refresh and widget loading remain stable.

## Validation Log

- 2026-02-25 (CLI smoke):
  - [x] `node --check controller/static/dashboard.js`
  - [x] `python3 -m py_compile controller/controller_main.py controller/db.py controller/process_manager.py`
  - [x] Runtime endpoint smoke: `GET /dashboard`, `GET /tools`, `GET /tools/status-all` returned `200`.
  - [x] Runtime lifecycle smoke (downloader): `launch -> alive true`, `auto-start true/false`, `kill -> alive false`.
  - [ ] Manual UI breakpoint/device validation (pending).

## Step Plan I Will Take

1. Apply Phase 1 fixes first (fastest value, lowest risk).
2. Implement Phase 2 interaction changes, prioritizing mobile-safe behavior.
3. Refactor toward Phase 3 incrementally (no big-bang rewrite).
4. Validate with Phase 4 tests before finalizing.
5. Ship in small PR-sized chunks to reduce risk and simplify review.

## Definition of Done

- [ ] Dashboard is usable on phone without zooming or precision tapping.
- [x] Core tool state is always visible in compact views.
- [x] Desktop keeps efficient controls, including reorder.
- [ ] Categories and compact/expanded behavior reduce visual overload.
- [ ] No regressions in tool lifecycle actions (start/stop/open/auto-start/hide).
