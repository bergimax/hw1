from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Chore, ChoreCompletion, Household, User


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")


@admin.register(User)
class ChoresUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Household", {"fields": ("household", "role", "display_name", "must_change_password")}),
    )
    list_display = ("username", "display_name", "household", "role", "is_active")
    list_filter = ("role", "is_active", "household")


@admin.register(Chore)
class ChoreAdmin(admin.ModelAdmin):
    list_display = ("title", "household", "recurrence_type", "assignee", "next_due_on", "active")
    list_filter = ("household", "recurrence_type", "active")


@admin.register(ChoreCompletion)
class ChoreCompletionAdmin(admin.ModelAdmin):
    list_display = ("chore", "completed_by", "completed_on", "undone_at")
    list_filter = ("completed_on",)
