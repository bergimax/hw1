from django.shortcuts import redirect
from django.urls import reverse


class ForcePasswordChangeMiddleware:
    """Redirect users with ``must_change_password`` to the change form."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and user.must_change_password:
            allowed = {
                reverse("password_change"),
                reverse("logout"),
            }
            if request.path not in allowed and not request.path.startswith(
                ("/static/", "/admin/")
            ):
                return redirect("password_change")
        return self.get_response(request)
