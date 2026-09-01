from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from .models import Chore, ChoreCompletion, Household, User
from .recurrence import compute_initial_due, next_due_after


class RecurrenceTests(TestCase):
    def test_weekly_next_after(self):
        # 2026-09-01 is a Tuesday (weekday 1)
        cfg = {"freq": "weekly", "weekdays": [1]}  # Tuesdays
        self.assertEqual(
            next_due_after("fixed", cfg, date(2026, 9, 1)), date(2026, 9, 8)
        )

    def test_weekly_initial_due_is_on_or_after_today(self):
        cfg = {"freq": "weekly", "weekdays": [1]}
        self.assertEqual(
            compute_initial_due("fixed", cfg, date(2026, 9, 1)), date(2026, 9, 1)
        )

    def test_monthly_clamps_short_month(self):
        cfg = {"freq": "monthly", "day": 31}
        self.assertEqual(
            next_due_after("fixed", cfg, date(2026, 1, 31)), date(2026, 2, 28)
        )

    def test_interval(self):
        self.assertEqual(
            next_due_after("interval", {"days": 3}, date(2026, 9, 1)),
            date(2026, 9, 4),
        )


class BaseData(TestCase):
    def setUp(self):
        self.hh = Household.objects.create(name="Test House")
        self.other_hh = Household.objects.create(name="Other House")
        self.admin = User.objects.create_user(
            "admin", password="pw", household=self.hh, role=User.Role.ADMIN
        )
        self.member = User.objects.create_user(
            "member", password="pw", household=self.hh, role=User.Role.MEMBER
        )
        self.outsider = User.objects.create_user(
            "outsider", password="pw", household=self.other_hh, role=User.Role.ADMIN
        )
        self.chore = Chore.objects.create(
            household=self.hh,
            title="Dishes",
            recurrence_type="interval",
            recurrence_config={"days": 2},
            next_due_on=date(2026, 9, 1),
        )


class SignupTests(TestCase):
    def test_signup_creates_household_and_admin(self):
        resp = self.client.post(
            reverse("signup"),
            {
                "household_name": "New House",
                "username": "boss",
                "display_name": "Boss",
                "password1": "s3cret-pass-xy",
                "password2": "s3cret-pass-xy",
            },
        )
        self.assertRedirects(resp, reverse("checklist"))
        user = User.objects.get(username="boss")
        self.assertTrue(user.is_household_admin)
        self.assertEqual(user.household.name, "New House")


class ChecklistTests(BaseData):
    def test_requires_login(self):
        resp = self.client.get(reverse("checklist"))
        self.assertEqual(resp.status_code, 302)

    def test_member_sees_household_chores_only(self):
        Chore.objects.create(
            household=self.other_hh, title="Secret", recurrence_type="interval",
            recurrence_config={"days": 1}, next_due_on=date(2026, 9, 1),
        )
        self.client.login(username="member", password="pw")
        resp = self.client.get(reverse("checklist"))
        self.assertContains(resp, "Dishes")
        self.assertNotContains(resp, "Secret")

    def test_claim_and_release(self):
        self.client.login(username="member", password="pw")
        self.client.post(reverse("chore_claim", args=[self.chore.pk]))
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.assignee, self.member)
        self.client.post(reverse("chore_release", args=[self.chore.pk]))
        self.chore.refresh_from_db()
        self.assertIsNone(self.chore.assignee)

    def test_complete_advances_due_and_logs(self):
        self.client.login(username="member", password="pw")
        self.client.post(reverse("chore_complete", args=[self.chore.pk]))
        self.chore.refresh_from_db()
        self.assertEqual(ChoreCompletion.objects.count(), 1)
        # interval of 2 days from today
        self.assertEqual(
            self.chore.next_due_on, date.today() + timedelta(days=2)
        )

    def test_cannot_complete_other_household_chore(self):
        other = Chore.objects.create(
            household=self.other_hh, title="X", recurrence_type="interval",
            recurrence_config={"days": 1}, next_due_on=date(2026, 9, 1),
        )
        self.client.login(username="member", password="pw")
        resp = self.client.post(reverse("chore_complete", args=[other.pk]))
        self.assertEqual(resp.status_code, 404)


class AdminAreaTests(BaseData):
    def test_member_cannot_reach_chore_management(self):
        self.client.login(username="member", password="pw")
        resp = self.client.get(reverse("chore_list"))
        self.assertEqual(resp.status_code, 403)

    def test_admin_creates_chore(self):
        self.client.login(username="admin", password="pw")
        resp = self.client.post(
            reverse("chore_create"),
            {
                "title": "Sweep",
                "description": "",
                "recurrence_type": "interval",
                "interval_days": 5,
                "assignee": "",
            },
        )
        self.assertRedirects(resp, reverse("chore_list"))
        chore = Chore.objects.get(title="Sweep")
        self.assertEqual(chore.recurrence_config, {"days": 5})
        self.assertIsNotNone(chore.next_due_on)

    def test_admin_adds_member_with_forced_password_change(self):
        self.client.login(username="admin", password="pw")
        resp = self.client.post(
            reverse("member_create"),
            {
                "username": "newbie",
                "display_name": "Newbie",
                "email": "",
                "role": "member",
                "initial_password": "temp-pass-123",
            },
        )
        self.assertRedirects(resp, reverse("member_list"))
        newbie = User.objects.get(username="newbie")
        self.assertTrue(newbie.must_change_password)
        self.assertEqual(newbie.household, self.hh)

    def test_forced_password_change_redirect(self):
        self.member.must_change_password = True
        self.member.save()
        self.client.login(username="member", password="pw")
        resp = self.client.get(reverse("checklist"))
        self.assertRedirects(resp, reverse("password_change"))

    def test_admin_undo_completion_restores_state(self):
        self.chore.assignee = self.member
        self.chore.save()
        self.client.login(username="member", password="pw")
        self.client.post(reverse("chore_complete", args=[self.chore.pk]))
        completion = ChoreCompletion.objects.get()

        self.client.login(username="admin", password="pw")
        resp = self.client.post(reverse("completion_undo", args=[completion.pk]))
        self.assertRedirects(resp, reverse("activity"))
        self.chore.refresh_from_db()
        completion.refresh_from_db()
        self.assertEqual(self.chore.next_due_on, date(2026, 9, 1))
        self.assertEqual(self.chore.assignee, self.member)
        self.assertTrue(completion.is_undone)

    def test_member_cannot_undo(self):
        self.client.login(username="member", password="pw")
        self.client.post(reverse("chore_complete", args=[self.chore.pk]))
        completion = ChoreCompletion.objects.get()
        resp = self.client.post(reverse("completion_undo", args=[completion.pk]))
        self.assertEqual(resp.status_code, 403)

    def test_archive_keeps_history(self):
        self.client.login(username="member", password="pw")
        self.client.post(reverse("chore_complete", args=[self.chore.pk]))
        self.client.login(username="admin", password="pw")
        self.client.post(reverse("chore_archive", args=[self.chore.pk]))
        self.chore.refresh_from_db()
        self.assertFalse(self.chore.active)
        self.assertEqual(ChoreCompletion.objects.count(), 1)
