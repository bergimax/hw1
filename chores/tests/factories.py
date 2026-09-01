"""Small helpers for building test data without external dependencies."""

from datetime import date

from chores.models import Chore, ChoreCompletion, Household, User

DEFAULT_PW = "test-pass-123"


def make_household(name="Test House"):
    return Household.objects.create(name=name)


def _make_user(household, username, default_role, **kwargs):
    return User.objects.create_user(
        username=username,
        password=kwargs.pop("password", DEFAULT_PW),
        household=household,
        role=kwargs.pop("role", default_role),
        display_name=kwargs.pop("display_name", username.title()),
        **kwargs,
    )


def make_admin(household=None, username="admin", **kwargs):
    household = household or make_household()
    return _make_user(household, username, User.Role.ADMIN, **kwargs)


def make_member(household, username="member", **kwargs):
    return _make_user(household, username, User.Role.MEMBER, **kwargs)


def make_chore(household, **kwargs):
    kwargs.setdefault("title", "Dishes")
    kwargs.setdefault("recurrence_type", Chore.Recurrence.INTERVAL)
    kwargs.setdefault("recurrence_config", {"days": 2})
    kwargs.setdefault("next_due_on", date(2026, 9, 1))
    return Chore.objects.create(household=household, **kwargs)


def make_completion(chore, user, on=date(2026, 9, 1), **kwargs):
    kwargs.setdefault("prev_due_on", chore.next_due_on)
    kwargs.setdefault("prev_assignee", chore.assignee)
    return ChoreCompletion.objects.create(
        chore=chore, completed_by=user, completed_on=on, **kwargs
    )
