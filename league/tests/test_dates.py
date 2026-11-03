from datetime import date

from django.test import SimpleTestCase

from league.utils import dates


class DateHelperTests(SimpleTestCase):
    def test_friday_on_or_after(self):
        self.assertEqual(dates.friday_on_or_after(date(2026, 11, 3)), date(2026, 11, 6))
        self.assertEqual(dates.friday_on_or_after(date(2026, 11, 6)), date(2026, 11, 6))
        self.assertEqual(dates.friday_on_or_after(date(2026, 11, 7)), date(2026, 11, 13))

    def test_lagos_evening_kickoff(self):
        kickoff = dates.at_lagos_time(date(2026, 11, 6), 20)
        self.assertEqual(kickoff.utcoffset().total_seconds(), 3600)
        self.assertEqual(dates.match_day(kickoff), date(2026, 11, 6))
