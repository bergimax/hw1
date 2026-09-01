from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from chores.models import Chore, User

from .factories import make_chore, make_completion, make_household, make_member


class UserModelTests(TestCase):
    def test_is_household_admin(self):
        hh = make_household()
        admin = make_member(hh, "a", role=User.Role.ADMIN)
        member = make_member(hh, "m")
        self.assertTrue(admin.is_household_admin)
        self.assertFalse(member.is_household_admin)

    def test_str_prefers_display_name(self):
        hh = make_household()
        u = make_member(hh, "jo", display_name="Jo")
        self.assertEqual(str(u), "Jo")

    def test_str_falls_back_to_username(self):
        hh = make_household()
        u = make_member(hh, "jo", display_name="")
        self.assertEqual(str(u), "jo")


class ChoreModelTests(TestCase):
    def setUp(self):
        self.hh = make_household()

    def test_in_pool_when_no_assignee(self):
        chore = make_chore(self.hh)
        self.assertTrue(chore.in_pool)
        chore.assignee = make_member(self.hh)
        self.assertFalse(chore.in_pool)

    def test_is_overdue(self):
        today = timezone.localdate()
        self.assertTrue(make_chore(self.hh, next_due_on=today - timedelta(days=1)).is_overdue())
        self.assertFalse(make_chore(self.hh, next_due_on=today).is_overdue())
        self.assertFalse(make_chore(self.hh, next_due_on=today + timedelta(days=1)).is_overdue())

    def test_is_overdue_with_no_due_date(self):
        self.assertFalse(make_chore(self.hh, next_due_on=None).is_overdue())

    def test_set_initial_due_interval(self):
        chore = Chore(
            household=self.hh, title="x",
            recurrence_type=Chore.Recurrence.INTERVAL, recurrence_config={"days": 4},
        )
        chore.set_initial_due(date(2026, 9, 1))
        self.assertEqual(chore.next_due_on, date(2026, 9, 1))

    def test_advance_due_interval(self):
        chore = make_chore(self.hh, recurrence_config={"days": 3})
        chore.advance_due(date(2026, 9, 10))
        self.assertEqual(chore.next_due_on, date(2026, 9, 13))

    def test_advance_due_fixed_weekly(self):
        chore = make_chore(
            self.hh,
            recurrence_type=Chore.Recurrence.FIXED,
            recurrence_config={"freq": "weekly", "weekdays": [1]},  # Tuesday
        )
        chore.advance_due(date(2026, 9, 1))  # a Tuesday
        self.assertEqual(chore.next_due_on, date(2026, 9, 8))


class ChoreCompletionModelTests(TestCase):
    def test_is_undone(self):
        hh = make_household()
        chore = make_chore(hh)
        member = make_member(hh)
        c = make_completion(chore, member)
        self.assertFalse(c.is_undone)
        c.undone_at = timezone.now()
        self.assertTrue(c.is_undone)
