from datetime import date

from django.test import TestCase
from django.urls import reverse

from chores.models import Chore, ChoreCompletion

from .factories import DEFAULT_PW, make_admin, make_chore, make_household, make_member


class ChoreAdminAccessTests(TestCase):
    def setUp(self):
        self.hh = make_household()
        self.admin = make_admin(self.hh, "admin")
        self.member = make_member(self.hh, "sam")
        self.chore = make_chore(self.hh)

    def test_member_forbidden_from_every_management_view(self):
        self.client.login(username="sam", password=DEFAULT_PW)
        for name, args in [
            ("chore_list", []),
            ("chore_create", []),
            ("chore_update", [self.chore.pk]),
            ("chore_archive", [self.chore.pk]),
        ]:
            self.assertEqual(
                self.client.get(reverse(name, args=args)).status_code, 403, name
            )

    def test_anonymous_redirected_to_login(self):
        resp = self.client.get(reverse("chore_list"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)

    def test_admin_cannot_edit_other_household_chore(self):
        other = make_household("Other")
        theirs = make_chore(other)
        self.client.login(username="admin", password=DEFAULT_PW)
        self.assertEqual(
            self.client.get(reverse("chore_update", args=[theirs.pk])).status_code, 404
        )

    def test_chore_list_scoped_to_household(self):
        other = make_household("Other")
        make_chore(other, title="NotYours")
        self.client.login(username="admin", password=DEFAULT_PW)
        resp = self.client.get(reverse("chore_list"))
        self.assertNotContains(resp, "NotYours")


class ChoreCreateTests(TestCase):
    def setUp(self):
        self.hh = make_household()
        self.admin = make_admin(self.hh, "admin")
        self.member = make_member(self.hh, "sam")
        self.client.login(username="admin", password=DEFAULT_PW)

    def test_create_interval_chore(self):
        resp = self.client.post(
            reverse("chore_create"),
            {"title": "Sweep", "description": "", "recurrence_type": "interval",
             "interval_days": 5, "assignee": ""},
        )
        self.assertRedirects(resp, reverse("chore_list"))
        chore = Chore.objects.get(title="Sweep")
        self.assertEqual(chore.recurrence_config, {"days": 5})
        self.assertEqual(chore.household, self.hh)
        self.assertIsNotNone(chore.next_due_on)

    def test_create_weekly_chore(self):
        resp = self.client.post(
            reverse("chore_create"),
            {"title": "Trash", "description": "", "recurrence_type": "fixed",
             "freq": "weekly", "weekdays": ["1", "4"], "assignee": ""},
        )
        self.assertRedirects(resp, reverse("chore_list"))
        chore = Chore.objects.get(title="Trash")
        self.assertEqual(chore.recurrence_config, {"freq": "weekly", "weekdays": [1, 4]})

    def test_create_monthly_chore(self):
        self.client.post(
            reverse("chore_create"),
            {"title": "Rent", "description": "", "recurrence_type": "fixed",
             "freq": "monthly", "month_day": 1, "assignee": ""},
        )
        chore = Chore.objects.get(title="Rent")
        self.assertEqual(chore.recurrence_config, {"freq": "monthly", "day": 1})

    def test_interval_without_days_is_rejected(self):
        resp = self.client.post(
            reverse("chore_create"),
            {"title": "Bad", "description": "", "recurrence_type": "interval",
             "assignee": ""},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp.context["form"], "interval_days", "Required for an interval schedule.")
        self.assertFalse(Chore.objects.filter(title="Bad").exists())

    def test_weekly_without_weekdays_is_rejected(self):
        resp = self.client.post(
            reverse("chore_create"),
            {"title": "Bad", "description": "", "recurrence_type": "fixed",
             "freq": "weekly", "assignee": ""},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp.context["form"], "weekdays", "Pick at least one day.")

    def test_fixed_without_freq_is_rejected(self):
        resp = self.client.post(
            reverse("chore_create"),
            {"title": "Bad", "description": "", "recurrence_type": "fixed",
             "assignee": ""},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp.context["form"], "freq", "Choose weekly or monthly.")

    def test_assignee_choices_limited_to_active_household_members(self):
        make_member(self.hh, "inactive", is_active=False)
        other = make_household("Other")
        make_member(other, "outsider")
        resp = self.client.get(reverse("chore_create"))
        usernames = {u.username for u in resp.context["form"].fields["assignee"].queryset}
        self.assertEqual(usernames, {"admin", "sam"})

    def test_can_assign_chore_on_create(self):
        self.client.post(
            reverse("chore_create"),
            {"title": "Dishes", "description": "", "recurrence_type": "interval",
             "interval_days": 2, "assignee": self.member.pk},
        )
        chore = Chore.objects.get(title="Dishes")
        self.assertEqual(chore.assignee, self.member)


class ChoreUpdateArchiveTests(TestCase):
    def setUp(self):
        self.hh = make_household()
        self.admin = make_admin(self.hh, "admin")
        self.member = make_member(self.hh, "sam")
        self.client.login(username="admin", password=DEFAULT_PW)

    def test_edit_changes_fields_and_recurrence(self):
        chore = make_chore(self.hh, title="Old", recurrence_config={"days": 2})
        self.client.post(
            reverse("chore_update", args=[chore.pk]),
            {"title": "New", "description": "now weekly", "recurrence_type": "fixed",
             "freq": "weekly", "weekdays": ["0"], "assignee": ""},
        )
        chore.refresh_from_db()
        self.assertEqual(chore.title, "New")
        self.assertEqual(chore.recurrence_type, "fixed")
        self.assertEqual(chore.recurrence_config, {"freq": "weekly", "weekdays": [0]})

    def test_edit_keeps_existing_due_date(self):
        chore = make_chore(self.hh, next_due_on=date(2026, 9, 1))
        self.client.post(
            reverse("chore_update", args=[chore.pk]),
            {"title": "Dishes", "description": "", "recurrence_type": "interval",
             "interval_days": 2, "assignee": ""},
        )
        chore.refresh_from_db()
        self.assertEqual(chore.next_due_on, date(2026, 9, 1))

    def test_archive_deactivates_and_clears_assignee(self):
        chore = make_chore(self.hh, assignee=self.member)
        resp = self.client.post(reverse("chore_archive", args=[chore.pk]))
        self.assertRedirects(resp, reverse("chore_list"))
        chore.refresh_from_db()
        self.assertFalse(chore.active)
        self.assertIsNone(chore.assignee)

    def test_archive_keeps_completion_history(self):
        chore = make_chore(self.hh)
        ChoreCompletion.objects.create(
            chore=chore, completed_by=self.member, completed_on=date(2026, 9, 1)
        )
        self.client.post(reverse("chore_archive", args=[chore.pk]))
        self.assertEqual(ChoreCompletion.objects.filter(chore=chore).count(), 1)

    def test_archived_chore_leaves_checklist(self):
        chore = make_chore(self.hh, title="ToArchive")
        self.client.post(reverse("chore_archive", args=[chore.pk]))
        self.client.login(username="sam", password=DEFAULT_PW)
        resp = self.client.get(reverse("checklist"))
        self.assertNotIn(chore, list(resp.context["chores"]))
