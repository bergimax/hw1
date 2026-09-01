from django.test import TestCase
from django.urls import reverse

from chores.models import Household, User

from .factories import DEFAULT_PW, make_admin, make_household, make_member


class SignupTests(TestCase):
    url = "/signup/"

    def _payload(self, **over):
        data = {
            "household_name": "New House",
            "username": "boss",
            "display_name": "Boss",
            "email": "",
            "password1": "s3cret-pass-xy",
            "password2": "s3cret-pass-xy",
        }
        data.update(over)
        return data

    def test_creates_household_and_admin_and_logs_in(self):
        resp = self.client.post(reverse("signup"), self._payload())
        self.assertRedirects(resp, reverse("checklist"))
        user = User.objects.get(username="boss")
        self.assertTrue(user.is_household_admin)
        self.assertFalse(user.must_change_password)
        self.assertEqual(user.household.name, "New House")
        # session is authenticated
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_password_mismatch_creates_nothing(self):
        resp = self.client.post(
            reverse("signup"), self._payload(password2="different-xyz")
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username="boss").exists())
        self.assertFalse(Household.objects.filter(name="New House").exists())

    def test_duplicate_username_rejected(self):
        make_admin(username="boss")
        resp = self.client.post(reverse("signup"), self._payload())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(User.objects.filter(username="boss").count(), 1)

    def test_authenticated_user_is_redirected_away(self):
        make_admin(username="someone")
        self.client.login(username="someone", password=DEFAULT_PW)
        resp = self.client.get(reverse("signup"))
        self.assertRedirects(resp, reverse("checklist"))


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.hh = make_household()
        self.user = make_member(self.hh, "sam")

    def test_login_redirects_to_checklist(self):
        resp = self.client.post(
            reverse("login"), {"username": "sam", "password": DEFAULT_PW}
        )
        self.assertRedirects(resp, reverse("checklist"))

    def test_login_honours_next_parameter(self):
        resp = self.client.post(
            reverse("login") + "?next=/activity/",
            {"username": "sam", "password": DEFAULT_PW},
        )
        self.assertRedirects(resp, "/activity/")

    def test_protected_page_redirects_anonymous_to_login(self):
        resp = self.client.get(reverse("checklist"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)
        self.assertIn("next=", resp.url)

    def test_inactive_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save()
        resp = self.client.post(
            reverse("login"), {"username": "sam", "password": DEFAULT_PW}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_requires_post(self):
        self.client.login(username="sam", password=DEFAULT_PW)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        resp = self.client.post(reverse("logout"))
        self.assertRedirects(resp, reverse("home"), target_status_code=200)


class ForcePasswordChangeTests(TestCase):
    def setUp(self):
        self.hh = make_household()
        self.member = make_member(self.hh, "sam", must_change_password=True)
        self.client.login(username="sam", password=DEFAULT_PW)

    def test_redirected_from_checklist(self):
        resp = self.client.get(reverse("checklist"))
        self.assertRedirects(resp, reverse("password_change"))

    def test_redirected_from_activity(self):
        resp = self.client.get(reverse("activity"))
        self.assertRedirects(resp, reverse("password_change"))

    def test_can_reach_password_change_page(self):
        resp = self.client.get(reverse("password_change"))
        self.assertEqual(resp.status_code, 200)

    def test_can_log_out(self):
        resp = self.client.post(reverse("logout"))
        self.assertEqual(resp.status_code, 302)

    def test_changing_password_clears_flag_and_unblocks(self):
        resp = self.client.post(
            reverse("password_change"),
            {
                "old_password": DEFAULT_PW,
                "new_password1": "brand-new-pass-9",
                "new_password2": "brand-new-pass-9",
            },
        )
        self.assertRedirects(resp, reverse("checklist"))
        self.member.refresh_from_db()
        self.assertFalse(self.member.must_change_password)
        # now the checklist is reachable
        self.assertEqual(self.client.get(reverse("checklist")).status_code, 200)

    def test_normal_user_not_redirected(self):
        make_member(self.hh, "jo")
        self.client.login(username="jo", password=DEFAULT_PW)
        self.assertEqual(self.client.get(reverse("checklist")).status_code, 200)
