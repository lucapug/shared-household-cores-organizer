# Chore Wheel

A single-device web app for managing shared household chores on a fixed weekly
rotation. Designed for one shared screen (kitchen tablet / family computer):
no accounts, no sync, no notifications.

Built with Django + HTMX (vendored locally, no build step).

## Features

- **Setup screen** — one-time configuration: add, remove and reorder household
  members and chores. An anchor date (set automatically on first launch) starts
  the week counter.
- **Weekly rotation** — each chore cycles through members independently, offset
  by its position in the chore list, so nobody gets everything in the same week:
  `member = members[(weekNumber + choreIndex) % members.length]`
- **Chore board** — one row per chore with the assigned person for the current
  week, a big touch-friendly done toggle and an inline shared note per chore.
- **Cover / swap** — someone else did the chore? Pick their name from the
  *Cover* menu: the assigned person is struck through and the actual doer is
  shown next to them.
- **Weekly reset** — automatic on week boundaries (state is stored per week),
  plus a manual *Reset week* button that asks for explicit confirmation before
  clearing the current week's done-marks, notes and covers.

## Requirements

- [uv](https://docs.astral.sh/uv/) (Python 3.14)

## Getting started

```bash
# install dependencies
uv sync

# create/apply database migrations
uv run python manage.py migrate

# start the development server
uv run python manage.py runserver
```

Then open:

- **http://127.0.0.1:8000/** — the chore board (main dashboard)
- **http://127.0.0.1:8000/setup/** — the setup screen (members & chores)

First run: go to *Setup*, add your household members and chores, then head back
to the *Board*.

## Running the tests

```bash
uv run python manage.py test shared_household_cores_organizer
```

## Project layout

```
config/                            Django project (settings, urls, wsgi/asgi)
shared_household_cores_organizer/  the app
  models.py                        Member, Chore, ChoreWeekState, HouseholdConfig
  rotation.py                      pure rotation/week logic (no DB)
  views.py, urls.py                board, setup, toggle/note/cover, week reset
  templates/…/                     board, row partial, setup, reset partials
  static/                          htmx.min.js (vendored), app.css
_docs/                             plan.md and backlog.md
```

## Tech notes

- Persistence is SQLite via the Django ORM; weekly chore state is keyed by
  `(chore, week_start)`, so week boundaries are handled automatically and past
  weeks are preserved.
- HTMX is served from `static/` (no CDN) so the app works offline; interactions
  degrade gracefully to full page loads without JavaScript.
- See `_docs/plan.md` for the original MVP plan and `_docs/backlog.md` for the
  development backlog.
