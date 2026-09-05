from django.db.models import Max
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import rotation
from .forms import ChoreForm, MemberForm
from .models import Chore, ChoreWeekState, HouseholdConfig, Member

APP = "shared_household_cores_organizer"


def _row(chore, index, members, week_num, week_start):
    state = ChoreWeekState.objects.get_or_create(chore=chore, week_start=week_start)[0]
    return {
        "chore": chore,
        "state": state,
        "member": rotation.assign_member(members, week_num, index),
    }


def board(request):
    anchor = HouseholdConfig.load().anchor_date
    week_start = rotation.current_week_start(anchor)
    week_num = rotation.week_number(week_start, anchor)
    members = list(Member.objects.all())
    rows = [
        _row(chore, index, members, week_num, week_start)
        for index, chore in enumerate(Chore.objects.all())
    ]
    return render(
        request,
        f"{APP}/board.html",
        {
            "rows": rows,
            "members": members,
            "week_label": rotation.week_label(week_start),
        },
    )


def _row_context(state):
    anchor = HouseholdConfig.load().anchor_date
    week_number = rotation.week_number(state.week_start, anchor)
    members = list(Member.objects.all())
    chores = list(Chore.objects.all())
    index = next((i for i, chore in enumerate(chores) if chore.id == state.chore_id), 0)
    return {
        "members": members,
        "row": {
            "chore": state.chore,
            "state": state,
            "member": rotation.assign_member(members, week_number, index),
        },
    }


def _respond_with_row(request, state):
    if request.headers.get("HX-Request") == "true":
        return render(request, f"{APP}/_chore_row.html", _row_context(state))
    return redirect("chore_wheel:board")


@require_POST
def toggle_done(request, pk):
    state = get_object_or_404(ChoreWeekState, pk=pk)
    state.done = not state.done
    state.save()
    return _respond_with_row(request, state)


@require_POST
def set_note(request, pk):
    state = get_object_or_404(ChoreWeekState, pk=pk)
    state.note = request.POST.get("note", "")
    state.save()
    return _respond_with_row(request, state)


@require_POST
def set_cover(request, pk):
    state = get_object_or_404(ChoreWeekState, pk=pk)
    member_id = request.POST.get("covered_by", "")
    state.covered_by = Member.objects.filter(pk=member_id).first() if member_id else None
    state.save()
    return _respond_with_row(request, state)


def week_reset(request):
    anchor = HouseholdConfig.load().anchor_date
    week_start = rotation.current_week_start(anchor)
    is_htmx = request.headers.get("HX-Request") == "true"
    if request.method == "POST":
        if is_htmx and not request.POST.get("confirm"):
            return render(request, f"{APP}/_reset_confirm.html")
        ChoreWeekState.objects.filter(week_start=week_start).delete()
        if is_htmx:
            response = render(request, f"{APP}/_reset_button.html")
            response["HX-Refresh"] = "true"
            return response
        return redirect("chore_wheel:board")
    return render(request, f"{APP}/_reset_button.html")


def setup(request):
    return render(
        request,
        f"{APP}/setup.html",
        {
            "members": Member.objects.all(),
            "chores": Chore.objects.all(),
            "anchor": HouseholdConfig.load().anchor_date,
        },
    )


def _next_position(model):
    return (model.objects.aggregate(max_pos=Max("position"))["max_pos"] or 0) + 1


def _move(request, model, pk, direction):
    obj = get_object_or_404(model, pk=pk)
    siblings = list(model.objects.all())
    index = siblings.index(obj)
    target = index - 1 if direction == "up" else index + 1
    if 0 <= target < len(siblings):
        other = siblings[target]
        obj.position, other.position = other.position, obj.position
        other.save()
        obj.save()
    return redirect("chore_wheel:setup")


@require_POST
def add_member(request):
    form = MemberForm(request.POST)
    if form.is_valid():
        Member.objects.create(
            name=form.cleaned_data["name"], position=_next_position(Member)
        )
    return redirect("chore_wheel:setup")


@require_POST
def delete_member(request, pk):
    get_object_or_404(Member, pk=pk).delete()
    return redirect("chore_wheel:setup")


@require_POST
def move_member(request, pk, direction):
    return _move(request, Member, pk, direction)


@require_POST
def add_chore(request):
    form = ChoreForm(request.POST)
    if form.is_valid():
        Chore.objects.create(
            name=form.cleaned_data["name"], position=_next_position(Chore)
        )
    return redirect("chore_wheel:setup")


@require_POST
def delete_chore(request, pk):
    get_object_or_404(Chore, pk=pk).delete()
    return redirect("chore_wheel:setup")


@require_POST
def move_chore(request, pk, direction):
    return _move(request, Chore, pk, direction)
