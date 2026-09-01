from django.test import TestCase
from django.urls import reverse

from chores.models import User

from .factories import DEFAULT_PW, make_admin, make_household, make_member


class MemberListTests(TestCase):
    def setUp(self):
        self.hh = make_household()
        self.admin = make_admin(self.hh, "admin")
        self.member = make_member(self.hh, "sam")

    def test_admin_sees_only_own_household(self):
        other = make_household("Other")
        make_member(other, "outsider")
        self.client.login(username="admin", password=DEFAULT_PW)
        resp = self.client.get(reverse("member_list"))
        self.assertContains(resp, "sam")
        self.assertNotContains(resp, "outsider")

    def test_member_forbidden(self):
        self.client.login(username="sam", password=DEFAULT_PW)
        self.assertEqual(self.client.get(reverse("member_list")).status_code, 403)


class MemberCreateTests(TestCase):
    def setUp(self):
        self.hh = make_household()
        self.admin = make_admin(self.hh, "admin")
        self.client.login(username="admin", password=DEFAULT_PW)

    def test_create_member_with_initial_password(self):
        resp = self.client.post(
            reverse("member_create"),
            {"username": "newbie", "display_name": "Newbie", "email": "",
             "role": "member", "initial_password": "temp-pass-123"},
        )
        self.assertRedirects(resp, reverse("member_list"))
        newbie = User.objects.get(username="newbie")
        self.assertEqual(newbie.household, self.hh)
        self.assertEqual(newbie.role, "member")
        self.assertTrue(newbie.must_change_password)
        self.assertTrue(newbie.check_password("temp-pass-123"))

    def test_new_member_can_log_in_with_initial_password(self):
        self.client.post(
            reverse("member_create"),
            {"username": "newbie", "display_name": "Newbie", "email": "",
             "role": "member", "initial_password": "temp-pass-123"},
        )
        self.client.logout()
        ok = self.client.login(username="newbie", password="temp-pass-123")
        self.assertTrue(ok)

    def test_password_required_on_create(self):
        resp = self.client.post(
            reverse("member_create"),
            {"username": "newbie", "display_name": "Newbie", "email": "",
             "role": "member", "initial_password": ""},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username="newbie").exists())

    def test_can_create_a_second_admin(self):
        self.client.post(
            reverse("member_create"),
            {"username": "coadmin", "display_name": "Co", "email": "",
             "role": "admin", "initial_password": "temp-pass-123"},
        )
        self.assertTrue(User.objects.get(username="coadmin").is_household_admin)


class MemberUpdateTests(TestCase):
    def setUp(self):
        self.hh = make_household()
        self.admin = make_admin(self.hh, "admin")
        self.member = make_member(self.hh, "sam", display_name="Sam")
        self.client.login(username="admin", password=DEFAULT_PW)

    def test_edit_without_password_keeps_it(self):
        self.client.post(
            reverse("member_update", args=[self.member.pk]),
            {"username": "sam", "display_name": "Samuel", "email": "", "role": "member",
             "initial_password": ""},
        )
        self.member.refresh_from_db()
        self.assertEqual(self.member.display_name, "Samuel")
        self.assertTrue(self.member.check_password(DEFAULT_PW))
        self.assertFalse(self.member.must_change_password)

    def test_edit_with_new_password_forces_change(self):
        self.client.post(
            reverse("member_update", args=[self.member.pk]),
            {"username": "sam", "display_name": "Sam", "email": "", "role": "member",
             "initial_password": "reset-pass-456"},
        )
        self.member.refresh_from_db()
        self.assertTrue(self.member.check_password("reset-pass-456"))
        self.assertTrue(self.member.must_change_password)

    def test_cannot_edit_other_household_member(self):
        other = make_household("Other")
        outsider = make_member(other, "outsider")
        resp = self.client.get(reverse("member_update", args=[outsider.pk]))
        self.assertEqual(resp.status_code, 404)


class MemberToggleActiveTests(TestCase):
    def setUp(self):
        self.hh = make_household()
        self.admin = make_admin(self.hh, "admin")
        self.member = make_member(self.hh, "sam")

    def test_admin_deactivates_and_reactivates(self):
        self.client.login(username="admin", password=DEFAULT_PW)
        self.client.post(reverse("member_toggle", args=[self.member.pk]))
        self.member.refresh_from_db()
        self.assertFalse(self.member.is_active)
        self.client.post(reverse("member_toggle", args=[self.member.pk]))
        self.member.refresh_from_db()
        self.assertTrue(self.member.is_active)

    def test_admin_cannot_deactivate_self(self):
        self.client.login(username="admin", password=DEFAULT_PW)
        self.client.post(reverse("member_toggle", args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_member_cannot_toggle(self):
        self.client.login(username="sam", password=DEFAULT_PW)
        resp = self.client.post(reverse("member_toggle", args=[self.admin.pk]))
        self.assertEqual(resp.status_code, 403)

    def test_toggle_requires_post(self):
        self.client.login(username="admin", password=DEFAULT_PW)
        self.assertEqual(
            self.client.get(reverse("member_toggle", args=[self.member.pk])).status_code,
            405,
        )

    def test_cannot_toggle_other_household_member(self):
        other = make_household("Other")
        outsider = make_member(other, "outsider")
        self.client.login(username="admin", password=DEFAULT_PW)
        resp = self.client.post(reverse("member_toggle", args=[outsider.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_deactivated_member_cannot_log_in(self):
        self.member.is_active = False
        self.member.save()
        self.assertFalse(self.client.login(username="sam", password=DEFAULT_PW))
