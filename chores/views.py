from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import AdminSignupForm, ChoreForm, MemberForm
from .mixins import HouseholdAdminMixin, HouseholdScopedMixin
from .models import Chore, ChoreCompletion, User


def home(request):
    if request.user.is_authenticated:
        return redirect("checklist")
    return render(request, "home.html")


class ClearFlagPasswordChangeView(PasswordChangeView):
    """Clears ``must_change_password`` once the user picks a new password."""

    success_url = reverse_lazy("checklist")
    template_name = "registration/password_change_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.user
        if user.must_change_password:
            user.must_change_password = False
            user.save(update_fields=["must_change_password"])
        messages.success(self.request, "Password updated.")
        return response


class AdminSignupView(CreateView):
    form_class = AdminSignupForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("checklist")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("checklist")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, "Household created. Welcome!")
        return response


# --- Checklist -------------------------------------------------------------


@login_required
def checklist(request):
    household = request.user.household
    chores = (
        Chore.objects.filter(household=household, active=True)
        .select_related("assignee")
        .order_by("next_due_on", "title")
    )
    today = timezone.localdate()
    return render(
        request,
        "checklist.html",
        {"chores": chores, "today": today},
    )


def _get_chore(request, pk):
    return get_object_or_404(
        Chore, pk=pk, household=request.user.household, active=True
    )


@login_required
@require_POST
def chore_claim(request, pk):
    chore = _get_chore(request, pk)
    if chore.assignee_id is None:
        chore.assignee = request.user
        chore.save(update_fields=["assignee"])
        messages.success(request, f"You claimed “{chore.title}”.")
    else:
        messages.error(request, "That chore is already claimed.")
    return redirect("checklist")


@login_required
@require_POST
def chore_release(request, pk):
    chore = _get_chore(request, pk)
    if chore.assignee_id == request.user.id or request.user.is_household_admin:
        chore.assignee = None
        chore.save(update_fields=["assignee"])
        messages.success(request, f"“{chore.title}” is back in the pool.")
    else:
        messages.error(request, "You can only release a chore you claimed.")
    return redirect("checklist")


@login_required
@require_POST
def chore_complete(request, pk):
    chore = _get_chore(request, pk)
    today = timezone.localdate()
    with transaction.atomic():
        ChoreCompletion.objects.create(
            chore=chore,
            completed_by=request.user,
            completed_on=today,
            prev_due_on=chore.next_due_on,
            prev_assignee=chore.assignee,
        )
        chore.advance_due(today)
        chore.assignee = None  # pool chores return to the pool
        chore.save(update_fields=["next_due_on", "assignee"])
    messages.success(request, f"Marked “{chore.title}” done.")
    return redirect("checklist")


# --- Chore definitions (admin) -------------------------------------------


class ChoreListView(HouseholdAdminMixin, ListView):
    model = Chore
    template_name = "chore_list.html"
    context_object_name = "chores"


class ChoreCreateView(HouseholdAdminMixin, CreateView):
    model = Chore
    form_class = ChoreForm
    template_name = "chore_form.html"
    success_url = reverse_lazy("chore_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["household"] = self.household
        return kwargs

    def form_valid(self, form):
        form.save(household=self.household)
        messages.success(self.request, "Chore created.")
        return redirect(self.success_url)


class ChoreUpdateView(HouseholdAdminMixin, UpdateView):
    model = Chore
    form_class = ChoreForm
    template_name = "chore_form.html"
    success_url = reverse_lazy("chore_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["household"] = self.household
        return kwargs

    def form_valid(self, form):
        form.save(household=self.household)
        messages.success(self.request, "Chore updated.")
        return redirect(self.success_url)


class ChoreArchiveView(HouseholdAdminMixin, DeleteView):
    """Soft delete: deactivate the chore so its completion history is kept."""

    model = Chore
    template_name = "chore_confirm_delete.html"
    success_url = reverse_lazy("chore_list")

    def form_valid(self, form):
        self.object = self.get_object()
        self.object.active = False
        self.object.assignee = None
        self.object.save(update_fields=["active", "assignee"])
        messages.success(self.request, f"Archived “{self.object.title}”.")
        return redirect(self.success_url)


# --- Member management (admin) ------------------------------------------


class MemberListView(HouseholdAdminMixin, ListView):
    template_name = "member_list.html"
    context_object_name = "members"

    def get_queryset(self):
        return User.objects.filter(household=self.household).order_by(
            "-is_active", "display_name", "username"
        )


class MemberCreateView(HouseholdAdminMixin, CreateView):
    model = User
    form_class = MemberForm
    template_name = "member_form.html"
    success_url = reverse_lazy("member_list")

    def get_queryset(self):
        return User.objects.filter(household=self.household)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["creating"] = True
        return kwargs

    def form_valid(self, form):
        form.save(household=self.household)
        messages.success(self.request, "Member added. Share the initial password with them.")
        return redirect(self.success_url)


class MemberUpdateView(HouseholdAdminMixin, UpdateView):
    model = User
    form_class = MemberForm
    template_name = "member_form.html"
    success_url = reverse_lazy("member_list")

    def get_queryset(self):
        return User.objects.filter(household=self.household)

    def form_valid(self, form):
        form.save(household=self.household)
        messages.success(self.request, "Member updated.")
        return redirect(self.success_url)


@login_required
@require_POST
def member_set_active(request, pk):
    if not request.user.is_household_admin:
        return HttpResponseForbidden()
    member = get_object_or_404(User, pk=pk, household=request.user.household)
    if member.id == request.user.id:
        messages.error(request, "You can't deactivate yourself.")
        return redirect("member_list")
    member.is_active = not member.is_active
    member.save(update_fields=["is_active"])
    messages.success(
        request,
        f"{member} { 'reactivated' if member.is_active else 'deactivated' }.",
    )
    return redirect("member_list")


# --- Activity log -------------------------------------------------------


class ActivityLogView(HouseholdScopedMixin, ListView):
    template_name = "activity.html"
    context_object_name = "completions"
    paginate_by = 25
    household_field = "chore__household"

    def get_queryset(self):
        return ChoreCompletion.objects.filter(
            chore__household=self.household
        ).select_related("chore", "completed_by", "undone_by")


@login_required
@require_POST
def completion_undo(request, pk):
    if not request.user.is_household_admin:
        return HttpResponseForbidden()
    completion = get_object_or_404(
        ChoreCompletion, pk=pk, chore__household=request.user.household
    )
    if completion.is_undone:
        messages.error(request, "That completion was already undone.")
        return redirect("activity")
    with transaction.atomic():
        chore = completion.chore
        chore.next_due_on = completion.prev_due_on
        chore.assignee = completion.prev_assignee
        chore.save(update_fields=["next_due_on", "assignee"])
        completion.undone_by = request.user
        completion.undone_at = timezone.now()
        completion.save(update_fields=["undone_by", "undone_at"])
    messages.success(request, f"Undid completion of “{chore.title}”.")
    return redirect("activity")
