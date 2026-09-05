from datetime import date

from django.test import Client, SimpleTestCase, TestCase

from . import rotation
from .models import Chore, ChoreWeekState, Member


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
