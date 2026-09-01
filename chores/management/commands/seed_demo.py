from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from chores.models import Chore, ChoreCompletion, Household, User


class Command(BaseCommand):
    help = "Create a demo household with members, chores, and some history."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete an existing demo household first.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            Household.objects.filter(name="Maple Street").delete()

        if Household.objects.filter(name="Maple Street").exists():
            self.stdout.write(self.style.WARNING("Demo household already exists; use --reset."))
            return

        household = Household.objects.create(name="Maple Street")
        today = timezone.localdate()

        admin = User.objects.create_user(
            username="alex", password="demo-pass-123", display_name="Alex",
            household=household, role=User.Role.ADMIN,
        )
        sam = User.objects.create_user(
            username="sam", password="demo-pass-123", display_name="Sam",
            household=household, role=User.Role.MEMBER, must_change_password=True,
        )
        jo = User.objects.create_user(
            username="jo", password="demo-pass-123", display_name="Jo",
            household=household, role=User.Role.MEMBER, must_change_password=True,
        )

        specs = [
            ("Take out the trash", "fixed", {"freq": "weekly", "weekdays": [1]}, sam),
            ("Vacuum living room", "fixed", {"freq": "weekly", "weekdays": [5]}, None),
            ("Clean the bathroom", "interval", {"days": 7}, jo),
            ("Water the plants", "interval", {"days": 3}, None),
            ("Pay rent", "fixed", {"freq": "monthly", "day": 1}, admin),
        ]
        chores = []
        for title, rtype, cfg, assignee in specs:
            chore = Chore(
                household=household, title=title, recurrence_type=rtype,
                recurrence_config=cfg, assignee=assignee,
            )
            chore.set_initial_due(today)
            chore.save()
            chores.append(chore)

        # a little history
        trash = chores[0]
        ChoreCompletion.objects.create(
            chore=trash, completed_by=sam, completed_on=today - timedelta(days=7),
            prev_due_on=today - timedelta(days=7), prev_assignee=sam,
        )
        # make one chore overdue for demo purposes
        chores[3].next_due_on = today - timedelta(days=2)
        chores[3].save(update_fields=["next_due_on"])

        self.stdout.write(self.style.SUCCESS(
            "Seeded 'Maple Street': admin=alex, members=sam/jo, password 'demo-pass-123'."
        ))
