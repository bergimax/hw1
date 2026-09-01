from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("signup/", views.AdminSignupView.as_view(), name="signup"),

    path("checklist/", views.checklist, name="checklist"),
    path("chores/<int:pk>/claim/", views.chore_claim, name="chore_claim"),
    path("chores/<int:pk>/release/", views.chore_release, name="chore_release"),
    path("chores/<int:pk>/complete/", views.chore_complete, name="chore_complete"),

    path("manage/chores/", views.ChoreListView.as_view(), name="chore_list"),
    path("manage/chores/new/", views.ChoreCreateView.as_view(), name="chore_create"),
    path("manage/chores/<int:pk>/edit/", views.ChoreUpdateView.as_view(), name="chore_update"),
    path("manage/chores/<int:pk>/archive/", views.ChoreArchiveView.as_view(), name="chore_archive"),

    path("manage/members/", views.MemberListView.as_view(), name="member_list"),
    path("manage/members/new/", views.MemberCreateView.as_view(), name="member_create"),
    path("manage/members/<int:pk>/edit/", views.MemberUpdateView.as_view(), name="member_update"),
    path("manage/members/<int:pk>/toggle/", views.member_set_active, name="member_toggle"),

    path("activity/", views.ActivityLogView.as_view(), name="activity"),
    path("activity/<int:pk>/undo/", views.completion_undo, name="completion_undo"),
]
