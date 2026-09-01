from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from chores.models import ChoreCompletion

from .factories import (
    DEFAULT_PW,
    make_admin,
    make_chore,
    make_completion,
    make_household,
    make_member,
)


class ActivityLogViewTests(TestCase):
    def setUp(self):
        self.hh = make_household()
        self.other = make_household("Other")
        self.admin = make_admin(self.hh, "admin")
        self.member = make_member(self.hh, "sam")
        self.chore = make_chore(self.hh, title="Dishes")

    def test_requires_login(self):
        self.assertEqual(self.client.get(reverse("activity")).status_code, 302)

    def test_lists_household_completions_only(self):
        make_completion(self.chore, self.member)
        theirs = make_chore(self.other, title="TheirChore")
        make_completion(theirs, make_member(self.other, "outsider"))
        self.client.login(username="sam", password=DEFAULT_PW)
        resp = self.client.get(reverse("activity"))
        self.assertContains(resp, "Dishes")
        self.assertNotContains(resp, "TheirChore")

    def test_newest_first(self):
        old = make_completion(self.chore, self.member, on=date(2026, 8, 1))
        new = make_completion(self.chore, self.member, on=date(2026, 9, 1))
        self.client.login(username="sam", password=DEFAULT_PW)
        resp = self.client.get(reverse("activity"))
        ids = [c.id for c in resp.context["completions"]]
        self.assertEqual(ids, [new.id, old.id])

    def test_pagination(self):
        for i in range(30):
            make_completion(self.chore, self.member, on=date(2026, 9, 1) + timedelta(days=i))
        self.client.login(username="sam", password=DEFAULT_PW)
        page1 = self.client.get(reverse("activity"))
        self.assertEqual(len(page1.context["completions"]), 25)
        page2 = self.client.get(reverse("activity") + "?page=2")
        self.assertEqual(len(page2.context["completions"]), 5)

    def test_empty_state(self):
        self.client.login(username="sam", password=DEFAULT_PW)
        resp = self.client.get(reverse("activity"))
        self.assertContains(resp, "Nothing done yet")

    def test_member_sees_no_undo_link(self):
        make_completion(self.chore, self.member)
        self.client.login(username="sam", password=DEFAULT_PW)
        resp = self.client.get(reverse("activity"))
        self.assertNotContains(resp, "Undo")

    def test_admin_sees_undo_link(self):
        make_completion(self.chore, self.member)
        self.client.login(username="admin", password=DEFAULT_PW)
        resp = self.client.get(reverse("activity"))
        self.assertContains(resp, "Undo")


class CompletionUndoTests(TestCase):
    def setUp(self):
        self.hh = make_household()
        self.other = make_household("Other")
        self.admin = make_admin(self.hh, "admin")
        self.member = make_member(self.hh, "sam")
        self.chore = make_chore(self.hh, assignee=self.member, next_due_on=date(2026, 9, 1))

    def _complete(self):
        self.client.login(username="sam", password=DEFAULT_PW)
        self.client.post(reverse("chore_complete", args=[self.chore.pk]))
        self.client.logout()
        return ChoreCompletion.objects.get()

    def test_admin_undo_restores_due_date_and_assignee(self):
        completion = self._complete()
        self.client.login(username="admin", password=DEFAULT_PW)
        resp = self.client.post(reverse("completion_undo", args=[completion.pk]))
        self.assertRedirects(resp, reverse("activity"))
        self.chore.refresh_from_db()
        completion.refresh_from_db()
        self.assertEqual(self.chore.next_due_on, date(2026, 9, 1))
        self.assertEqual(self.chore.assignee, self.member)
        self.assertTrue(completion.is_undone)
        self.assertEqual(completion.undone_by, self.admin)

    def test_member_cannot_undo(self):
        completion = self._complete()
        self.client.login(username="sam", password=DEFAULT_PW)
        resp = self.client.post(reverse("completion_undo", args=[completion.pk]))
        self.assertEqual(resp.status_code, 403)
        completion.refresh_from_db()
        self.assertFalse(completion.is_undone)

    def test_cannot_undo_twice(self):
        completion = self._complete()
        self.client.login(username="admin", password=DEFAULT_PW)
        self.client.post(reverse("completion_undo", args=[completion.pk]))
        self.chore.refresh_from_db()
        due_after_first_undo = self.chore.next_due_on
        # tamper then try again — second undo must be a no-op
        self.chore.next_due_on = date(2030, 1, 1)
        self.chore.save()
        self.client.post(reverse("completion_undo", args=[completion.pk]))
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.next_due_on, date(2030, 1, 1))
        self.assertNotEqual(due_after_first_undo, date(2030, 1, 1))

    def test_cannot_undo_other_household_completion(self):
        theirs_chore = make_chore(self.other)
        theirs = make_completion(theirs_chore, make_member(self.other, "outsider"))
        self.client.login(username="admin", password=DEFAULT_PW)
        resp = self.client.post(reverse("completion_undo", args=[theirs.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_undo_requires_post(self):
        completion = self._complete()
        self.client.login(username="admin", password=DEFAULT_PW)
        self.assertEqual(
            self.client.get(reverse("completion_undo", args=[completion.pk])).status_code,
            405,
        )
