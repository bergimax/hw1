from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from chores.models import Chore, ChoreCompletion

from .factories import DEFAULT_PW, make_admin, make_chore, make_household, make_member


class ChecklistViewTests(TestCase):
    def setUp(self):
        self.hh = make_household()
        self.other = make_household("Other")
        self.admin = make_admin(self.hh, "admin")
        self.member = make_member(self.hh, "sam")
        self.client.login(username="sam", password=DEFAULT_PW)

    def test_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("checklist")).status_code, 302)

    def test_only_shows_own_household_active_chores(self):
        make_chore(self.hh, title="Mine")
        make_chore(self.hh, title="Archived", active=False)
        make_chore(self.other, title="Theirs")
        resp = self.client.get(reverse("checklist"))
        self.assertContains(resp, "Mine")
        self.assertNotContains(resp, "Archived")
        self.assertNotContains(resp, "Theirs")

    def test_overdue_sorted_first(self):
        today = timezone.localdate()
        make_chore(self.hh, title="Later", next_due_on=today + timedelta(days=3))
        make_chore(self.hh, title="Overdue", next_due_on=today - timedelta(days=1))
        resp = self.client.get(reverse("checklist"))
        chores = list(resp.context["chores"])
        self.assertEqual(chores[0].title, "Overdue")

    def test_empty_state(self):
        resp = self.client.get(reverse("checklist"))
        self.assertContains(resp, "No chores yet")


class ClaimReleaseTests(TestCase):
    def setUp(self):
        self.hh = make_household()
        self.other_hh = make_household("Other")
        self.admin = make_admin(self.hh, "admin")
        self.sam = make_member(self.hh, "sam")
        self.jo = make_member(self.hh, "jo")
        self.chore = make_chore(self.hh)

    def login(self, who):
        self.client.login(username=who, password=DEFAULT_PW)

    def test_claim_pool_chore(self):
        self.login("sam")
        resp = self.client.post(reverse("chore_claim", args=[self.chore.pk]))
        self.assertRedirects(resp, reverse("checklist"))
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.assignee, self.sam)

    def test_cannot_claim_already_claimed_chore(self):
        self.chore.assignee = self.jo
        self.chore.save()
        self.login("sam")
        self.client.post(reverse("chore_claim", args=[self.chore.pk]))
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.assignee, self.jo)

    def test_release_own_chore(self):
        self.chore.assignee = self.sam
        self.chore.save()
        self.login("sam")
        self.client.post(reverse("chore_release", args=[self.chore.pk]))
        self.chore.refresh_from_db()
        self.assertIsNone(self.chore.assignee)

    def test_member_cannot_release_someone_elses_chore(self):
        self.chore.assignee = self.jo
        self.chore.save()
        self.login("sam")
        self.client.post(reverse("chore_release", args=[self.chore.pk]))
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.assignee, self.jo)

    def test_admin_can_release_any_chore(self):
        self.chore.assignee = self.jo
        self.chore.save()
        self.login("admin")
        self.client.post(reverse("chore_release", args=[self.chore.pk]))
        self.chore.refresh_from_db()
        self.assertIsNone(self.chore.assignee)

    def test_claim_requires_post(self):
        self.login("sam")
        self.assertEqual(
            self.client.get(reverse("chore_claim", args=[self.chore.pk])).status_code, 405
        )

    def test_claim_requires_login(self):
        self.assertEqual(
            self.client.post(reverse("chore_claim", args=[self.chore.pk])).status_code, 302
        )

    def test_cannot_claim_other_household_chore(self):
        theirs = make_chore(self.other_hh)
        self.login("sam")
        resp = self.client.post(reverse("chore_claim", args=[theirs.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_cannot_claim_archived_chore(self):
        self.chore.active = False
        self.chore.save()
        self.login("sam")
        resp = self.client.post(reverse("chore_claim", args=[self.chore.pk]))
        self.assertEqual(resp.status_code, 404)


class CompleteChoreTests(TestCase):
    def setUp(self):
        self.hh = make_household()
        self.other_hh = make_household("Other")
        self.sam = make_member(self.hh, "sam")
        self.client.login(username="sam", password=DEFAULT_PW)

    def test_interval_chore_advances_from_today(self):
        chore = make_chore(self.hh, recurrence_config={"days": 2})
        self.client.post(reverse("chore_complete", args=[chore.pk]))
        chore.refresh_from_db()
        self.assertEqual(chore.next_due_on, timezone.localdate() + timedelta(days=2))

    def test_fixed_chore_advances_by_schedule(self):
        chore = make_chore(
            self.hh,
            recurrence_type=Chore.Recurrence.FIXED,
            recurrence_config={"freq": "monthly", "day": 1},
        )
        self.client.post(reverse("chore_complete", args=[chore.pk]))
        chore.refresh_from_db()
        today = timezone.localdate()
        self.assertGreater(chore.next_due_on, today)
        self.assertEqual(chore.next_due_on.day, 1)

    def test_completion_is_logged_with_snapshot(self):
        member2 = make_member(self.hh, "jo")
        chore = make_chore(self.hh, assignee=member2, next_due_on=date(2026, 9, 1))
        self.client.post(reverse("chore_complete", args=[chore.pk]))
        c = ChoreCompletion.objects.get()
        self.assertEqual(c.completed_by, self.sam)
        self.assertEqual(c.completed_on, timezone.localdate())
        self.assertEqual(c.prev_due_on, date(2026, 9, 1))
        self.assertEqual(c.prev_assignee, member2)

    def test_assigned_chore_returns_to_pool_after_completion(self):
        chore = make_chore(self.hh, assignee=self.sam)
        self.client.post(reverse("chore_complete", args=[chore.pk]))
        chore.refresh_from_db()
        self.assertIsNone(chore.assignee)

    def test_any_member_can_complete_any_chore(self):
        jo = make_member(self.hh, "jo")
        chore = make_chore(self.hh, assignee=jo)
        self.client.post(reverse("chore_complete", args=[chore.pk]))
        self.assertEqual(ChoreCompletion.objects.count(), 1)

    def test_requires_post(self):
        chore = make_chore(self.hh)
        self.assertEqual(
            self.client.get(reverse("chore_complete", args=[chore.pk])).status_code, 405
        )

    def test_cannot_complete_other_household_chore(self):
        theirs = make_chore(self.other_hh)
        resp = self.client.post(reverse("chore_complete", args=[theirs.pk]))
        self.assertEqual(resp.status_code, 404)
