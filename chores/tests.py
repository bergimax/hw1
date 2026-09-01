from django.test import TestCase
from django.urls import reverse


class HomeViewTests(TestCase):
    def test_home_renders(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Household Chores")
