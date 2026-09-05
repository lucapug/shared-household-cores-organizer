from __future__ import annotations

from datetime import date, timedelta
from typing import Sequence, TypeVar

T = TypeVar("T")


def week_start_for(day: date) -> date:
    """Return the Monday of the week containing ``day``."""
    return day - timedelta(days=day.weekday())


def week_number(day: date, anchor: date) -> int:
    """Zero-based count of weeks between the week of ``anchor`` and the week of ``day``."""
    delta = week_start_for(day) - week_start_for(anchor)
    return delta.days // 7


def current_week_start(anchor: date, today: date | None = None) -> date:
    """Week start (Monday) of the current week. ``today`` is injectable for tests."""
    return week_start_for(today if today is not None else date.today())


def assign_member(
    members: Sequence[T], week_number: int, chore_index: int
) -> T | None:
    """Member assigned to the chore at ``chore_index`` in week ``week_number``.

    Formula from the plan: ``members[(week_number + chore_index) % len(members)]``.
    Staggering by chore index spreads chores across members within a week.
    """
    count = len(members)
    if count == 0:
        return None
    return members[(week_number + chore_index) % count]


def assign_all(members: Sequence[T], chore_count: int, week_number: int) -> list[T | None]:
    """Assignment for every chore index (0..chore_count-1) in the given week."""
    return [assign_member(members, week_number, index) for index in range(chore_count)]


def week_label(week_start: date, today: date | None = None) -> str:
    """Human label like ``Week of Sep 1`` (year appended when it differs from today's)."""
    today = today if today is not None else date.today()
    label = f"{week_start.strftime('%b')} {week_start.day}"
    if week_start.year != today.year:
        label += f", {week_start.year}"
    return f"Week of {label}"
