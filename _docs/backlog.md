# Chore Wheel — Django Backlog

Adapted from `_docs/plan.md`. The only real deviation: persistence moves from
`localStorage` to Django ORM (SQLite). No auth, no sync — out of scope as planned.

## Decisions

| Topic            | Choice                                                              |
|------------------|---------------------------------------------------------------------|
| Stack            | Django (project layout: `manage.py` + `config/`), app: `shared_household_cores_organizer` |
| Persistence      | SQLite via Django ORM (replaces `localStorage`)                      |
| Interactivity    | HTMX, vendored locally in `static/` (no CDN, no build step)          |
| Fallback         | Views return full page for normal requests, row fragment for HTMX    |
| Setup screen     | Plain form POSTs (rare interaction, full reload acceptable)          |

## Phase 1 — Foundations

- [x] **1. Data models + migrations**
  `Member`, `Chore`, `ChoreWeekState` (FK chore, week start date, `done`, `note`,
  `covered_by` nullable FK to Member). State keyed by week start makes weekly
  reset nearly free and preserves future history.
- [x] **2. Rotation engine (pure service module + unit tests)**
  Week number from anchor date; assignment formula
  `member = members[(week_number + chore_index) % len(members)]`;
  current-week resolution. Pure logic, no DB.

## Phase 2 — Screens

- [x] **3. Setup screen**
  Add/remove/reorder members and chores (forms + views; one-time config).
- [x] **4. Chore board (main screen)**
  One row per chore: name, assigned person for the current week, done toggle,
  inline note field. Big touch targets for a kitchen tablet.
- [x] **5. Base template + minimal styling**
  Single-page feel, tablet-friendly CSS; includes `htmx.min.js` vendored in `static/`.
- [x] **6. Row partials**
  `_chore_row.html` partial template. Toggle/note/cover views return the row
  fragment for HTMX requests, full page otherwise.

## Phase 3 — Interactions

- [x] **7. Cover/swap**
  Strike-through on assigned person's name, record who actually did it (HTMX row update).
- [x] **8. Weekly reset**
  Automatic on week boundary (week-keyed state) + manual reset button with
  explicit confirmation step.

## Phase 4 — Hardening

- [ ] **9. End-to-end tests**
  Board rendering across week boundaries, rotation stagger correctness, reset behavior.
