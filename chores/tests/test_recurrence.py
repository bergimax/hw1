"""Pure date-math tests for chores.recurrence (no database)."""

from datetime import date

from django.test import SimpleTestCase

from chores.recurrence import (
    compute_initial_due,
    next_due_after,
    next_fixed,
    next_interval,
)

# Reference weekdays in Sept 2026:
#   2026-09-01 Tue, 09-02 Wed, 09-04 Fri, 09-06 Sun, 09-07 Mon


class NextFixedWeeklyTests(SimpleTestCase):
    def test_single_weekday_moves_to_next_week(self):
        cfg = {"freq": "weekly", "weekdays": [1]}  # Tuesday
        self.assertEqual(next_fixed(cfg, date(2026, 9, 1)), date(2026, 9, 8))

    def test_multiple_weekdays_picks_the_nearest(self):
        cfg = {"freq": "weekly", "weekdays": [0, 2, 4]}  # Mon/Wed/Fri
        # from Tuesday the next hit is Wednesday
        self.assertEqual(next_fixed(cfg, date(2026, 9, 1)), date(2026, 9, 2))

    def test_strictly_after_the_reference_date(self):
        cfg = {"freq": "weekly", "weekdays": [1]}  # Tuesday
        # asking from a Tuesday must not return that same Tuesday
        self.assertEqual(next_fixed(cfg, date(2026, 9, 1)), date(2026, 9, 8))

    def test_wraps_across_month_boundary(self):
        cfg = {"freq": "weekly", "weekdays": [2]}  # Wednesday
        self.assertEqual(next_fixed(cfg, date(2026, 9, 30)), date(2026, 10, 7))

    def test_empty_weekdays_returns_none(self):
        self.assertIsNone(next_fixed({"freq": "weekly", "weekdays": []}, date(2026, 9, 1)))


class NextFixedMonthlyTests(SimpleTestCase):
    def test_later_this_month(self):
        cfg = {"freq": "monthly", "day": 15}
        self.assertEqual(next_fixed(cfg, date(2026, 9, 1)), date(2026, 9, 15))

    def test_day_already_passed_rolls_to_next_month(self):
        cfg = {"freq": "monthly", "day": 1}
        self.assertEqual(next_fixed(cfg, date(2026, 9, 1)), date(2026, 10, 1))

    def test_clamps_to_last_day_of_short_month(self):
        cfg = {"freq": "monthly", "day": 31}
        self.assertEqual(next_fixed(cfg, date(2026, 1, 31)), date(2026, 2, 28))

    def test_clamps_day_31_in_30_day_month(self):
        cfg = {"freq": "monthly", "day": 31}
        self.assertEqual(next_fixed(cfg, date(2026, 4, 1)), date(2026, 4, 30))

    def test_rolls_over_year_boundary(self):
        cfg = {"freq": "monthly", "day": 1}
        self.assertEqual(next_fixed(cfg, date(2026, 12, 1)), date(2027, 1, 1))


class IntervalTests(SimpleTestCase):
    def test_adds_days(self):
        self.assertEqual(next_interval({"days": 3}, date(2026, 9, 1)), date(2026, 9, 4))

    def test_interval_of_one(self):
        self.assertEqual(next_interval({"days": 1}, date(2026, 9, 1)), date(2026, 9, 2))


class NextDueAfterTests(SimpleTestCase):
    def test_dispatches_fixed(self):
        cfg = {"freq": "weekly", "weekdays": [1]}
        self.assertEqual(
            next_due_after("fixed", cfg, date(2026, 9, 1)), date(2026, 9, 8)
        )

    def test_dispatches_interval(self):
        self.assertEqual(
            next_due_after("interval", {"days": 5}, date(2026, 9, 1)),
            date(2026, 9, 6),
        )

    def test_unknown_type_returns_none(self):
        self.assertIsNone(next_due_after("weird", {}, date(2026, 9, 1)))


class ComputeInitialDueTests(SimpleTestCase):
    def test_fixed_weekly_can_be_today(self):
        cfg = {"freq": "weekly", "weekdays": [1]}  # Tuesday
        self.assertEqual(
            compute_initial_due("fixed", cfg, date(2026, 9, 1)), date(2026, 9, 1)
        )

    def test_fixed_weekly_next_matching_day(self):
        cfg = {"freq": "weekly", "weekdays": [4]}  # Friday
        self.assertEqual(
            compute_initial_due("fixed", cfg, date(2026, 9, 1)), date(2026, 9, 4)
        )

    def test_fixed_monthly_can_be_today(self):
        cfg = {"freq": "monthly", "day": 1}
        self.assertEqual(
            compute_initial_due("fixed", cfg, date(2026, 9, 1)), date(2026, 9, 1)
        )

    def test_interval_starts_today(self):
        self.assertEqual(
            compute_initial_due("interval", {"days": 7}, date(2026, 9, 1)),
            date(2026, 9, 1),
        )

    def test_unknown_type_returns_none(self):
        self.assertIsNone(compute_initial_due("weird", {}, date(2026, 9, 1)))
