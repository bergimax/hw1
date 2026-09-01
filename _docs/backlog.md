# Backlog — Shared Household Chores (Django)

Small, ordered tasks derived from [`plan.md`](plan.md). Each task is meant to be
one focused commit / PR. Stack: Django 6.1, `config` project, `chores` app,
SQLite for dev.

Status key: `[ ]` todo · `[~]` in progress · `[x]` done

---

## M1 — Auth & household setup

- [x] **T1 · Base template + static setup**
  Add `templates/base.html`, configure `TEMPLATES` dirs and `STATIC_URL`,
  wire a placeholder home view + URL.
- [x] **T2 · Household & User models**
  `Household` model. Custom `User` (extend `AbstractUser`) with
  `household` FK, `role` (`admin`/`member`), `must_change_password` bool.
  Set `AUTH_USER_MODEL = "chores.User"`. Initial migration.
- [x] **T3 · Admin signup**
  Form + view + template: creates a `Household` and its admin `User` in one
  transaction, logs the user in.
- [x] **T4 · Login / logout**
  Use Django auth views with project templates; redirect rules for
  authenticated/anonymous users.
- [x] **T5 · Forced password change**
  Middleware or decorator: if `must_change_password`, redirect all requests to
  a change-password view until it is cleared.
- [x] **T6 · Household scoping helper**
  A `login_required` + same-household mixin/util used by every later view;
  tests that cross-household access 404s.

## M2 — Members & chore definitions (admin)

- [x] **T7 · Member list + create (admin only)**
  Admin view to list members and add one (display name + initial password,
  sets `must_change_password=True`). No email sent.
- [x] **T8 · Member edit / deactivate**
  Edit display name and role; deactivate (set `is_active=False`) instead of
  delete.
- [x] **T9 · Chore model**
  `Chore`: `household` FK, `title`, `description`, `recurrence_type`
  (`fixed`/`interval`), `recurrence_config` (JSON), `assignee` FK (nullable =
  pool), `next_due_on` (date, nullable), `active`. Migration.
- [x] **T10 · Recurrence logic module**
  `chores/recurrence.py`: `next_fixed(config, from_date)` and
  `next_interval(config, completed_on)`. Unit tests, no DB.
- [x] **T11 · Chore CRUD (admin only)**
  List / create / edit views + forms. Recurrence sub-form for fixed (weekly
  days / monthly day) and interval (N days). Compute `next_due_on` on save.
  "Delete" is a soft archive (`active=False`) so completion history survives.

## M3 — Checklist & activity log

- [x] **T12 · ChoreCompletion model**
  `chore` FK, `completed_by`, `completed_on`, `undone_by` (nullable),
  `undone_at` (nullable), timestamps. Migration.
- [x] **T13 · Checklist view**
  List active chores for the household, sorted by `next_due_on`, overdue
  (`next_due_on < today`) flagged and sorted first. Show assignee or "in pool".
- [x] **T14 · Claim / release pool chore**
  POST endpoints: claim sets `assignee` to current user; release clears it.
  Only allowed while the chore is not yet completed for the period.
- [x] **T15 · Mark chore done**
  Any member, any chore. Create `ChoreCompletion`, recompute `next_due_on`
  from recurrence, clear `assignee` for pool chores. Transaction + tests.
- [x] **T16 · Activity log view**
  Household-visible feed of completions and undos, newest first, paginated.
- [x] **T17 · Admin undo completion**
  Admin-only action: mark `ChoreCompletion` undone, restore prior
  `next_due_on` / `assignee`, record the undo so it shows in the feed.

## M4 — Polish & ship

- [x] **T18 · Empty / loading / error states**
  Friendly empty states for checklist, members, log; form validation messages.
- [x] **T19 · Responsive layout pass**
  Make the checklist and forms usable on a phone screen.
- [x] **T20 · Seed command**
  `manage.py seed_demo` — one household, an admin, a few members, assorted
  chores and completions for review.
- [x] **T21 · Test + CI baseline**
  `pytest`/`django test` green; GitHub Actions workflow running lint + tests
  on push.
- [x] **T22 · Deploy config**
  `.env.example`, `DEBUG`/`ALLOWED_HOSTS`/`SECRET_KEY` from env, `whitenoise`
  for static, basic deploy notes in the README.

---

## Explicitly not in this backlog (v1 out of scope)

Rotation scheduling, points/scoring, email & push notifications,
multi-household users, self-signup / invite links, time-of-day due times and
time zones. See [`../SCOPE.md`](../SCOPE.md).
