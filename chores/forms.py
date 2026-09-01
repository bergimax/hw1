from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Chore, Household, User

WEEKDAYS = [
    (0, "Mon"),
    (1, "Tue"),
    (2, "Wed"),
    (3, "Thu"),
    (4, "Fri"),
    (5, "Sat"),
    (6, "Sun"),
]


class AdminSignupForm(UserCreationForm):
    household_name = forms.CharField(max_length=120, label="Household name")
    display_name = forms.CharField(max_length=120)
    email = forms.EmailField(required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "display_name")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.display_name = self.cleaned_data["display_name"]
        user.role = User.Role.ADMIN
        user.must_change_password = False
        if commit:
            household = Household.objects.create(
                name=self.cleaned_data["household_name"]
            )
            user.household = household
            user.save()
        return user


class MemberForm(forms.ModelForm):
    """Admin creates / edits a member. Password only on create."""

    initial_password = forms.CharField(
        widget=forms.PasswordInput, required=False,
        help_text="Set on create; leave blank when editing to keep the current one.",
    )

    class Meta:
        model = User
        fields = ("username", "display_name", "email", "role")

    def __init__(self, *args, **kwargs):
        self.creating = kwargs.pop("creating", False)
        super().__init__(*args, **kwargs)
        if self.creating:
            self.fields["initial_password"].required = True

    def save(self, commit=True, household=None):
        user = super().save(commit=False)
        if household is not None:
            user.household = household
        pw = self.cleaned_data.get("initial_password")
        if pw:
            user.set_password(pw)
            user.must_change_password = True
        if commit:
            user.save()
        return user


class ChoreForm(forms.ModelForm):
    freq = forms.ChoiceField(
        choices=[("weekly", "Weekly"), ("monthly", "Monthly")],
        required=False,
        label="Fixed frequency",
    )
    weekdays = forms.MultipleChoiceField(
        choices=WEEKDAYS,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    month_day = forms.IntegerField(min_value=1, max_value=31, required=False)
    interval_days = forms.IntegerField(min_value=1, required=False)

    class Meta:
        model = Chore
        fields = ("title", "description", "recurrence_type", "assignee")

    def __init__(self, *args, household=None, **kwargs):
        super().__init__(*args, **kwargs)
        if household is not None:
            self.fields["assignee"].queryset = household.members.filter(is_active=True)
        self.fields["assignee"].required = False
        self.fields["assignee"].empty_label = "— pool (unassigned) —"
        cfg = self.instance.recurrence_config or {}
        if cfg:
            self.fields["freq"].initial = cfg.get("freq")
            self.fields["weekdays"].initial = [str(d) for d in cfg.get("weekdays", [])]
            self.fields["month_day"].initial = cfg.get("day")
            self.fields["interval_days"].initial = cfg.get("days")

    def clean(self):
        data = super().clean()
        rtype = data.get("recurrence_type")
        if rtype == Chore.Recurrence.FIXED:
            freq = data.get("freq")
            if freq == "weekly":
                if not data.get("weekdays"):
                    self.add_error("weekdays", "Pick at least one day.")
                data["recurrence_config"] = {
                    "freq": "weekly",
                    "weekdays": sorted(int(d) for d in data.get("weekdays", [])),
                }
            elif freq == "monthly":
                if not data.get("month_day"):
                    self.add_error("month_day", "Required for a monthly schedule.")
                data["recurrence_config"] = {
                    "freq": "monthly",
                    "day": data.get("month_day"),
                }
            else:
                self.add_error("freq", "Choose weekly or monthly.")
        elif rtype == Chore.Recurrence.INTERVAL:
            if not data.get("interval_days"):
                self.add_error("interval_days", "Required for an interval schedule.")
            data["recurrence_config"] = {"days": data.get("interval_days")}
        return data

    def save(self, commit=True, household=None):
        chore = super().save(commit=False)
        if household is not None:
            chore.household = household
        chore.recurrence_config = self.cleaned_data["recurrence_config"]
        if chore.next_due_on is None:
            chore.set_initial_due()
        if commit:
            chore.save()
        return chore
