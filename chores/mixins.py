from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class HouseholdScopedMixin(LoginRequiredMixin):
    """Restrict a view's queryset to the current user's household.

    The model (or an explicitly set ``household_field``) must have a path to a
    ``Household`` so cross-household access returns 404 instead of leaking rows.
    """

    household_field = "household"

    @property
    def household(self):
        return self.request.user.household

    def get_queryset(self):
        qs = super().get_queryset()
        if self.household is None:
            return qs.none()
        return qs.filter(**{self.household_field: self.household})


class HouseholdAdminMixin(HouseholdScopedMixin, UserPassesTestMixin):
    """Household-scoped and admin-only."""

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_household_admin
