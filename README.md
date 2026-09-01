# hw1 — Shared Household Chores

A multi-tenant web app for managing shared household chores. Trust-based, no
scoring — a clear shared checklist with a history of who did what.

## Core features

1. **Shared chore checklist** — every member sees all pending chores; anyone can
   mark any chore done; overdue chores are flagged.
2. **Two assignment modes** — the admin assigns chores manually, or chores sit in
   a self-serve pool that members claim (and can release back).
3. **Recurring chores** — fixed schedules (e.g. every Monday) and
   interval-after-completion (e.g. 3 days after last done); completing a chore
   schedules its next occurrence.
4. **Activity log** — a full, household-visible history of who completed or
   un-completed what, and when.

Supporting frame: one admin per household manages members and chore definitions;
every member has their own login; notifications are in-app only.

## Documentation

- [`SCOPE.md`](SCOPE.md) — locked v1 scope, out-of-scope items, deferred decisions
- [`_docs/plan.md`](_docs/plan.md) — build plan

## Status

Planning. No tech stack chosen yet.
