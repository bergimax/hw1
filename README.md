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
- [`_docs/backlog.md`](_docs/backlog.md) — task breakdown (T1–T22)

## Stack

Django 6.1 (Python 3.13). Project: `config`. App: `chores`. SQLite for dev,
WhiteNoise for static files. Custom user model (`chores.User`).

## Local setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env            # optional; sane defaults without it
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo   # optional demo data
.venv/bin/python manage.py runserver
```

Demo login after `seed_demo`: `alex` / `demo-pass-123` (admin), plus members
`sam` and `jo` (same password, prompted to change on first login).

Run the checks:

```bash
.venv/bin/ruff check .
.venv/bin/python manage.py test
```

## Deployment notes

Set in the environment (or `.env`): `SECRET_KEY`, `DEBUG=False`,
`ALLOWED_HOSTS`. Then `python manage.py collectstatic --noinput` and run under
a WSGI server (`config.wsgi:application`). WhiteNoise serves static files.

## Key URLs

| Path | Who | What |
|---|---|---|
| `/` | anyone | landing / redirects to checklist |
| `/signup/` | anyone | create a household (become its admin) |
| `/checklist/` | members | the shared checklist; claim / release / done |
| `/activity/` | members | completion history; admin can undo |
| `/manage/chores/` | admin | define and archive chores |
| `/manage/members/` | admin | add / edit / deactivate members |
| `/admin/` | superuser | Django admin |

## Status

v1 feature-complete per the backlog. 17 tests passing.
