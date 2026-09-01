from django.test import TestCase
from django.urls import reverse

from .factories import DEFAULT_PW, make_household, make_member


class HomeViewTests(TestCase):
    def test_anonymous_sees_landing_page(self):
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "home.html")
        self.assertContains(resp, "Household Chores")

    def test_authenticated_user_redirected_to_checklist(self):
        hh = make_household()
        make_member(hh, "sam")
        self.client.login(username="sam", password=DEFAULT_PW)
        resp = self.client.get(reverse("home"))
        self.assertRedirects(resp, reverse("checklist"))
