# Chore Wheel — MVP Project Plan

## 1. Overview
A single-device web app for managing shared household chores on a fixed weekly rotation.
Designed for one shared screen (kitchen tablet / family computer). No accounts, no sync,
no notifications.

## 2. Core Decisions

| Topic        | Choice                                                        |
|--------------|---------------------------------------------------------------|
| Access model | Single shared device, local state only                        |
| Assignment   | Fixed rotation (no claiming, no points)                       |
| Cadence      | Weekly reset                                                  |
| Completion   | Simple toggle + inline shared note per chore                  |
| Persistence  | `localStorage`                                                |
| Roadmap      | Later: monthly "meeting mode" to recalibrate chore split      |

## 3. Features

### 3.1 Setup screen (one-time config)
- Input household member names
- Input chore list
- Stored in `localStorage`

## 3.2 Rotation engine
- Anchor date + week counter determines the current week number
- Staggered per-chore rotation: each chore cycles through members independently,
  offset by its position in the chore list, so no one gets everything in a week
- Assignment formula: `member = members[(weekNumber + choreIndex) % members.length]`
- Visible indicator: "Week of Sep 1" (or equivalent)

### 3.3 Chore board
- One row per chore: chore name, assigned person, done toggle, inline note field
- Notes are visible to everyone (e.g. "dishwasher liquid finished")

### 3.4 Cover / swap
- Strike-through on the assigned person's name
- Add the name of the person who actually did it, right after

### 3.5 Weekly reset
- Automatic on week boundary, plus a manual reset button
- Manual reset requires explicit confirmation (hard to tap accidentally)

## 4. Data model (localStorage)

```json
{
  "anchorDate": "2026-09-01",
  "members": ["Alex", "Sam", "Jo"],
  "chores": [
    {
      "name": "Dishes",
      "done": false,
      "note": "dishwasher liquid finished",
      "coveredBy": null
    }
  ]
}
```

## 5. Out of scope (MVP)
- Multiple devices / sync / backend
- Authentication
- Monthly meeting mode
- Streaks, points, history/log

## 6. Open items
- Tech stack (vanilla JS vs. framework)