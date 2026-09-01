# Shared Household Chores — v1 Scope

_Last updated: 2026-09-01_

A multi-tenant web app for managing shared household chores. Trust-based, no
scoring — just a clear shared checklist with a history of who did what.

## Users & households

- Multi-tenant: many independent households.
- One user belongs to **exactly one** household (no switcher, no multi-membership).
- Two roles:
  - **Admin** — one per household. Manages members and chore definitions.
  - **Member** — participates in the checklist.
- **Onboarding:** admin creates each member account and sets an initial password,
  shared out-of-band (chat, in person). Member is forced to change it on first
  login. No email infrastructure in v1.
- Every member signs in with their own credentials and has a personal view.

## Chores

- Chore **definitions** are created, edited, and deleted by the **admin only**.
- **Recurrence** (both supported):
  - Fixed schedule — e.g. every Monday, the 1st of each month.
  - Interval after completion — e.g. "3 days after it was last done".
- **Due dates are calendar dates only** — no time-of-day, no time zones.
  "Overdue" flips at local midnight.
- **Assignment modes in v1:**
  - **Manual** — admin assigns a chore to a specific member.
  - **Self-serve pool** — unassigned chores sit in a pool; any member can claim one.
    The claimer can **release it back to the pool** any time before it is done.
- Rotation / automatic turn-taking is **deferred** to a later version.

## Doing chores

- Shared checklist view of everything pending.
- **Any member can mark any chore done** — whether assigned to them or claimed
  from the pool.
- Completing a recurring chore automatically schedules its next occurrence.
- **Overdue chores** stay on the list, visually flagged. No stacking of missed
  occurrences, no auto-reassignment.
- **Undoing a completion is admin-only.** The activity log records the reversal.

## Tracking

- **No points, weights, or balances.** Fairness is left to the household.
- **Full activity log:** who completed (or un-completed) what, and when.
  Browsable by everyone in the household.

## Notifications

- **In-app only.** Members see state when they open the app.
- No email or push notifications in v1.

## Explicitly out of scope for v1

- Rotation / automatic turn-taking
- Points or any fairness scoring
- Email and push notifications
- Multiple households per user / household switcher
- Self-signup, invite links, invite codes
- Time-of-day due times and time zones

## Deferred decisions

- Tech stack / framework — not chosen yet.
