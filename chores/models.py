from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from .recurrence import compute_initial_due, next_due_after


class Household(models.Model):
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name="members",
        null=True,
        blank=True,
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    display_name = models.CharField(max_length=120, blank=True)
    must_change_password = models.BooleanField(default=False)

    @property
    def is_household_admin(self):
        return self.role == self.Role.ADMIN

    def __str__(self):
        return self.display_name or self.get_username()


class Chore(models.Model):
    class Recurrence(models.TextChoices):
        FIXED = "fixed", "Fixed schedule"
        INTERVAL = "interval", "Interval after completion"

    household = models.ForeignKey(
        Household, on_delete=models.CASCADE, related_name="chores"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    recurrence_type = models.CharField(max_length=10, choices=Recurrence.choices)
    # fixed:    {"freq": "weekly", "weekdays": [0, 3]}  (Mon=0)
    #           {"freq": "monthly", "day": 15}
    # interval: {"days": 3}
    recurrence_config = models.JSONField(default=dict)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_chores",
    )
    next_due_on = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["next_due_on", "title"]

    def __str__(self):
        return self.title

    @property
    def in_pool(self):
        return self.assignee_id is None

    def is_overdue(self, on=None):
        on = on or timezone.localdate()
        return self.next_due_on is not None and self.next_due_on < on

    def set_initial_due(self, on=None):
        self.next_due_on = compute_initial_due(
            self.recurrence_type, self.recurrence_config, on or timezone.localdate()
        )

    def advance_due(self, completed_on):
        self.next_due_on = next_due_after(
            self.recurrence_type, self.recurrence_config, completed_on
        )


class ChoreCompletion(models.Model):
    chore = models.ForeignKey(
        Chore, on_delete=models.CASCADE, related_name="completions"
    )
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="completions",
    )
    completed_on = models.DateField()
    # snapshot of the chore state before this completion, for undo
    prev_due_on = models.DateField(null=True, blank=True)
    prev_assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    undone_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="undone_completions",
    )
    undone_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.chore} completed {self.completed_on}"

    @property
    def is_undone(self):
        return self.undone_at is not None
