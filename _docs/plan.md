# Build Plan — Shared Household Chores v1

This plan turns [`../SCOPE.md`](../SCOPE.md) into an ordered build sequence. It is
deliberately stack-agnostic; the tech stack is chosen in Phase 0.

## Phase 0 — Foundations

- Choose the stack: web framework, database, auth approach, hosting.
- Set up the project skeleton, linting/formatting, and a test runner.
- Set up CI (lint + test on push).
- Define the environment config (`.env.example`).

## Phase 1 — Data model & migrations

Entities:

- **Household** — `id`, `name`, `created_at`.
- **User** — `id`, `household_id`, `email`, `password_hash`, `display_name`,
  `role` (`admin` | `member`), `must_change_password`, `created_at`.
- **Chore** — `id`, `household_id`, `title`, `description`, `recurrence_type`
  (`fixed` | `interval`), `recurrence_config` (JSON), `assignee_id` (nullable —
  null means it is in the pool), `next_due_on` (date, nullable), `active`.
- **ChoreCompletion** — `id`, `chore_id`, `completed_by`, `completed_on`,
  `undone_by` (nullable), `undone_at` (nullable), `created_at`.

Notes:

- Due dates are **calendar dates only** (no time, no time zone).
- Deleting a chore is a hard delete of the definition; completion history for
  that chore may be retained or cascade — decide in this phase.

## Phase 2 — Auth & household setup

- Admin sign-up creates a Household + the admin User in one step.
- Login / logout / session handling.
- Forced password change when `must_change_password` is true.
- Route guards: authenticated + same-household scoping on every query.

## Phase 3 — Member management (admin)

- Admin creates member accounts with a display name + initial password
  (`must_change_password = true`).
- Admin edits member display name / role, deactivates members.
- No email is sent; the admin shares the initial password out-of-band.

## Phase 4 — Chore definitions (admin)

- CRUD for chores, admin-only.
- Recurrence editor:
  - **Fixed**: weekly (days of week) or monthly (day of month).
  - **Interval**: N days after last completion.
- On create, compute `next_due_on`.

## Phase 5 — The checklist (all members)

- List pending chores for the household, sorted by due date, overdue first.
- Overdue = `next_due_on < today` — flagged visually, no stacking.
- Show assignee, or a "claim" affordance for pool chores.
- Claim a pool chore (sets `assignee_id`); release it (clears `assignee_id`).
- Mark done — by any member, for any chore:
  - Write a `ChoreCompletion`.
  - Recompute `next_due_on` from the recurrence rule (fixed: next matching date
    from today; interval: `completed_on + N days`).
  - Pool chores return to the pool after completion (assignee cleared).

## Phase 6 — Activity log

- Household-visible feed of completions and undos, newest first.
- Admin-only "undo completion": mark the `ChoreCompletion` undone, restore the
  chore's previous `next_due_on` / assignee state, and record the undo in the
  feed.

## Phase 7 — Polish

- Empty states, loading states, form validation and error messages.
- Basic responsive layout.
- Seed script / demo data for review.

## Out of scope for v1

Rotation, points/scoring, email & push notifications, multi-household users,
self-signup / invite links, time-of-day due times and time zones.
See [`../SCOPE.md`](../SCOPE.md) for the full list.

## Suggested milestones

- **M1**: Phases 0–2 — a user can sign up and log in.
- **M2**: Phases 3–4 — an admin can add members and define chores.
- **M3**: Phases 5–6 — members use the checklist; the log works.
- **M4**: Phase 7 — ready for review.
