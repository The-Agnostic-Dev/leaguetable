from django.core.cache import cache
from django.test import TestCase

from league.services import standings

from . import factories as f


class StandingsTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_points_goals_and_results(self):
        a, b, c = f.team("Alpha", short_name="ALP"), f.team("Bravo", short_name="BRA"), f.team("Charlie", short_name="CHA")
        f.played(a, b, 3, 1)
        f.played(b, c, 2, 2, days_ago=6)
        table = {row.team.name: row for row in standings.build_table()}

        self.assertEqual((table["Alpha"].won, table["Alpha"].drawn, table["Alpha"].lost), (1, 0, 0))
        self.assertEqual(table["Alpha"].points, 3)
        self.assertEqual((table["Bravo"].goals_for, table["Bravo"].goals_against), (3, 5))
        self.assertEqual(table["Bravo"].goal_difference, -2)
        self.assertEqual(table["Bravo"].points, 1)
        self.assertEqual(table["Charlie"].points, 1)
        self.assertEqual(table["Bravo"].form, ["L", "D"])

    def test_more_points_ranks_higher(self):
        a, b = f.team("Alpha", short_name="ALP"), f.team("Bravo", short_name="BRA")
        f.played(b, a, 2, 0)
        table = standings.build_table()
        self.assertEqual([row.team.name for row in table], ["Bravo", "Alpha"])
        self.assertEqual([row.position for row in table], [1, 2])

    def test_head_to_head_separates_teams_level_on_everything_else(self):
        a, b, c, d = (f.team(n, short_name=n[:3].upper()) for n in ("Alpha", "Bravo", "Charlie", "Delta"))
        f.played(b, a, 1, 0, days_ago=9)  # Bravo beat Alpha
        f.played(a, c, 1, 0, days_ago=8)
        f.played(d, b, 1, 0, days_ago=7)
        # Alpha and Bravo: 3 points, GD 0, GF 1 each.
        order = [row.team.name for row in standings.build_table()]
        self.assertLess(order.index("Bravo"), order.index("Alpha"))

    def test_played_counts_only_fixtures_with_result(self):
        a, b = f.team("Alpha", short_name="ALP"), f.team("Bravo", short_name="BRA")
        f.played(a, b, 2, 1)  # played: Alpha 2-1 Bravo
        scheduled = f.fixture(a, b)
        postponed = f.fixture(a, b)
        postponed.matchday = 2  # avoid unique constraint if any
        postponed.status = "postponed"
        postponed.save()
        table = {row.team.name: row for row in standings.build_table()}
        self.assertEqual(table["Alpha"].played, 1)
        self.assertEqual(table["Bravo"].played, 1)
        self.assertEqual(table["Alpha"].points, 3)
        self.assertEqual(table["Bravo"].points, 0)
        self.assertEqual(table["Alpha"].goal_difference, 1)
        self.assertEqual(table["Bravo"].goal_difference, -1)

    def test_goal_difference_ranks_before_head_to_head(self):
        a, b, c = (f.team(n, short_name=n[:3].upper()) for n in ("Alpha", "Bravo", "Charlie"))
        f.played(a, b, 1, 0)   # Alpha beat Bravo (head-to-head favours Alpha)
        f.played(c, a, 3, 1)   # Charlie beat Alpha
        f.played(b, c, 2, 0)   # Bravo beat Charlie
        # Alpha: 3 pts, GF 2, GA 3, GD -1; Bravo: 3 pts, GF 2, GA 1, GD +1.
        order = [row.team.name for row in standings.build_table()]
        self.assertLess(order.index("Bravo"), order.index("Alpha"))

    def test_alphabetical_when_nothing_separates(self):
        f.team("Zulu", short_name="ZUL")
        f.team("Alpha", short_name="ALP")
        self.assertEqual([row.team.name for row in standings.build_table()], ["Alpha", "Zulu"])

    def test_saving_a_fixture_refreshes_cached_table(self):
        a, b = f.team("Alpha", short_name="ALP"), f.team("Bravo", short_name="BRA")
        fixture = f.fixture(a, b)
        self.assertEqual(standings.position_of(a).points, 0)
        fixture.status, fixture.home_goals, fixture.away_goals = "played", 1, 0
        fixture.save()
        self.assertEqual(standings.position_of(a).points, 3)
