from datetime import date, timedelta
from unittest import mock

from django.test import Client, SimpleTestCase, TestCase

from . import rotation
from .models import Chore, ChoreWeekState, HouseholdConfig, Member


class WeekStartTests(SimpleTestCase):
    def test_monday_is_its_own_week_start(self):
        self.assertEqual(date(2026, 8, 31), rotation.week_start_for(date(2026, 8, 31)))

    def test_mid_week_maps_to_monday(self):
        self.assertEqual(date(2026, 8, 31), rotation.week_start_for(date(2026, 9, 5)))

    def test_sunday_belongs_to_previous_week(self):
        self.assertEqual(date(2026, 8, 31), rotation.week_start_for(date(2026, 9, 6)))


class WeekNumberTests(SimpleTestCase):
    ANCHOR = date(2026, 9, 1)

    def test_same_week_is_zero(self):
        self.assertEqual(0, rotation.week_number(date(2026, 9, 6), self.ANCHOR))

    def test_one_week_later(self):
        self.assertEqual(1, rotation.week_number(date(2026, 9, 7), self.ANCHOR))

    def test_one_week_earlier_is_negative(self):
        self.assertEqual(-1, rotation.week_number(date(2026, 8, 30), self.ANCHOR))

    def test_partial_week_counts_as_one(self):
        self.assertEqual(1, rotation.week_number(date(2026, 9, 13), self.ANCHOR))


class CurrentWeekStartTests(SimpleTestCase):
    def test_injectable_today(self):
        self.assertEqual(
            date(2026, 8, 31),
            rotation.current_week_start(date(2026, 1, 1), today=date(2026, 9, 5)),
        )


class AssignmentTests(SimpleTestCase):
    MEMBERS = ["Alex", "Sam", "Jo"]

    def test_week_zero_follows_chore_order(self):
        self.assertEqual(
            ["Alex", "Sam", "Jo"], rotation.assign_all(self.MEMBERS, 3, week_number=0)
        )

    def test_week_one_shifts_every_chore(self):
        self.assertEqual(
            ["Sam", "Jo", "Alex"], rotation.assign_all(self.MEMBERS, 3, week_number=1)
        )

    def test_more_chores_than_members_wrap(self):
        self.assertEqual(
            ["Alex", "Sam", "Jo", "Alex", "Sam"],
            rotation.assign_all(self.MEMBERS, 5, week_number=0),
        )

    def test_no_members_assigns_nothing(self):
        self.assertIsNone(rotation.assign_member([], week_number=0, chore_index=0))
        self.assertEqual([None, None, None], rotation.assign_all([], 3, week_number=0))

    def test_negative_weeks_still_assign(self):
        self.assertEqual("Jo", rotation.assign_member(self.MEMBERS, -1, chore_index=0))


class WeekLabelTests(SimpleTestCase):
    def test_label_within_current_year(self):
        self.assertEqual(
            "Week of Sep 1",
            rotation.week_label(date(2026, 9, 1), today=date(2026, 9, 5)),
        )

    def test_label_across_years_includes_year(self):
        self.assertEqual(
            "Week of Dec 29, 2025",
            rotation.week_label(date(2025, 12, 29), today=date(2026, 9, 5)),
        )


class ChoreWeekStateModelTests(TestCase):
    def test_unique_chore_per_week(self):
        chore = Chore.objects.create(name="Dishes")
        ChoreWeekState.objects.create(chore=chore, week_start=date(2026, 8, 31))
        with self.assertRaises(Exception):
            ChoreWeekState.objects.create(chore=chore, week_start=date(2026, 8, 31))

    def test_covered_by_optional(self):
        chore = Chore.objects.create(name="Dishes")
        state = ChoreWeekState.objects.create(chore=chore, week_start=date(2026, 8, 31))
        self.assertIsNone(state.covered_by)
        member = Member.objects.create(name="Alex")
        state.covered_by = member
        state.save()
        self.assertEqual("Alex", state.covered_by.name)


class CoverViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.member = Member.objects.create(name="Alex")
        self.other = Member.objects.create(name="Sam")
        self.chore = Chore.objects.create(name="Dishes")
        self.state = ChoreWeekState.objects.create(
            chore=self.chore, week_start=date(2026, 8, 31)
        )

    def test_set_cover_via_htmx_returns_row_with_strike_through(self):
        response = self.client.post(
            f"/states/{self.state.pk}/cover/",
            {"covered_by": self.other.pk},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(200, response.status_code)
        self.assertIn(b"covered-original", response.content)
        self.assertIn(b"covered-by", response.content)
        self.assertIn(b"Sam", response.content)
        self.assertEqual(self.other, ChoreWeekState.objects.get(pk=self.state.pk).covered_by)

    def test_clear_cover(self):
        self.state.covered_by = self.other
        self.state.save()
        response = self.client.post(
            f"/states/{self.state.pk}/cover/",
            {"covered_by": ""},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(200, response.status_code)
        self.assertIsNone(ChoreWeekState.objects.get(pk=self.state.pk).covered_by)

    def test_non_htmx_redirects(self):
        response = self.client.post(f"/states/{self.state.pk}/cover/", {"covered_by": self.other.pk})
        self.assertEqual(302, response.status_code)


class WeekResetTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.chore = Chore.objects.create(name="Dishes")
        self.week_start = rotation.week_start_for(date.today())
        self.state = ChoreWeekState.objects.create(
            chore=self.chore,
            week_start=self.week_start,
            done=True,
            note="milk",
        )
        self.other_week = ChoreWeekState.objects.create(
            chore=self.chore, week_start=date(2020, 1, 6), done=True
        )

    def test_get_returns_button_partial_without_resetting(self):
        response = self.client.get("/week/reset/", HTTP_HX_REQUEST="true")
        self.assertEqual(200, response.status_code)
        self.assertIn(b"Reset week", response.content)
        self.assertTrue(ChoreWeekState.objects.filter(pk=self.state.pk).exists())

    def test_post_without_confirm_returns_armed_partial_and_keeps_state(self):
        response = self.client.post("/week/reset/", HTTP_HX_REQUEST="true")
        self.assertEqual(200, response.status_code)
        self.assertIn(b"Yes, reset", response.content)
        self.assertTrue(ChoreWeekState.objects.filter(pk=self.state.pk).exists())

    def test_confirmed_post_resets_current_week_only(self):
        response = self.client.post(
            "/week/reset/", {"confirm": "1"}, HTTP_HX_REQUEST="true"
        )
        self.assertEqual(200, response.status_code)
        self.assertIn(b"Reset week", response.content)
        self.assertFalse(ChoreWeekState.objects.filter(pk=self.state.pk).exists())
        self.assertTrue(ChoreWeekState.objects.filter(pk=self.other_week.pk).exists())

    def test_non_htmx_post_resets_and_redirects(self):
        response = self.client.post("/week/reset/")
        self.assertEqual(302, response.status_code)
        self.assertFalse(ChoreWeekState.objects.filter(pk=self.state.pk).exists())


class EndToEndTests(TestCase):
    def _add_member(self, name):
        self.client.post("/members/add/", {"name": name})

    def _add_chore(self, name):
        self.client.post("/chores/add/", {"name": name})

    def _board_rows(self):
        response = self.client.get("/")
        return [
            (row["chore"].name, row["member"].name if row["member"] else None, row["state"])
            for row in response.context["rows"]
        ]

    def _toggle(self, state):
        response = self.client.post(
            f"/states/{state.pk}/toggle/", HTTP_HX_REQUEST="true"
        )
        self.assertEqual(200, response.status_code)

    def test_full_journey_setup_board_toggle_cover_note_reset(self):
        for name in ["Alex", "Sam", "Jo"]:
            self._add_member(name)
        for name in ["Dishes", "Trash", "Floor"]:
            self._add_chore(name)

        setup = self.client.get("/setup/")
        self.assertContains(setup, "Alex")
        self.assertContains(setup, "Dishes")

        rows = self._board_rows()
        self.assertEqual(
            [("Dishes", "Alex"), ("Trash", "Sam"), ("Floor", "Jo")],
            [(chore, member, None)[:2] for chore, member, _ in rows],
        )

        first, second, third = [state for _, _, state in rows]
        self._toggle(first)
        self._toggle(second)

        response = self.client.post(
            f"/states/{third.pk}/cover/",
            {"covered_by": Member.objects.get(name="Alex").pk},
            HTTP_HX_REQUEST="true",
        )
        self.assertContains(response, "covered-original")

        response = self.client.post(
            f"/states/{first.pk}/note/",
            {"note": "dishwasher liquid finished"},
            HTTP_HX_REQUEST="true",
        )
        self.assertContains(response, "dishwasher liquid finished")

        response = self.client.post("/week/reset/", HTTP_HX_REQUEST="true")
        self.assertContains(response, "Yes, reset")
        self.assertTrue(ChoreWeekState.objects.get(pk=first.pk).done)

        response = self.client.post(
            "/week/reset/", {"confirm": "1"}, HTTP_HX_REQUEST="true"
        )
        self.assertEqual("true", response.headers.get("HX-Refresh"))

        rows_after = self._board_rows()
        self.assertEqual([False, False, False], [s.done for _, _, s in rows_after])
        self.assertEqual(["", "", ""], [s.note for _, _, s in rows_after])
        self.assertEqual([None, None, None], [s.covered_by for _, _, s in rows_after])

    def test_rotation_stagger_on_board(self):
        for name in ["Alex", "Sam", "Jo"]:
            self._add_member(name)
        for name in ["C1", "C2", "C3", "C4", "C5"]:
            self._add_chore(name)

        rows = self._board_rows()
        self.assertEqual(
            [("C1", "Alex"), ("C2", "Sam"), ("C3", "Jo"), ("C4", "Alex"), ("C5", "Sam")],
            [(chore, member) for chore, member, _ in rows],
        )

    def test_week_boundary_creates_fresh_week_and_keeps_history(self):
        for name in ["Alex", "Sam"]:
            self._add_member(name)
        self._add_chore("Dishes")

        rows = self._board_rows()
        state = rows[0][2]
        self._toggle(state)

        self.assertEqual(1, HouseholdConfig.objects.count())
        anchor = HouseholdConfig.objects.first().anchor_date

        fake_today = rotation.week_start_for(anchor) + timedelta(days=9)

        class FakeDate(date):
            @classmethod
            def today(cls):
                return fake_today

        with mock.patch("shared_household_cores_organizer.rotation.date", FakeDate):
            rows_next_week = self._board_rows()
            new_state = rows_next_week[0][2]

            self.assertNotEqual(state.pk, new_state.pk)
            self.assertFalse(new_state.done)
            self.assertEqual(
                state.week_start + timedelta(days=7), new_state.week_start
            )
            old = ChoreWeekState.objects.get(pk=state.pk)
            self.assertTrue(old.done)
