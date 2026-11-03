from django.core.cache import cache
from django.test import TestCase

from league.forms import ResultEntry
from league.models import Card, Fixture
from league.services import discipline, results

from . import factories as f


class SaveResultTests(TestCase):
    def setUp(self):
        cache.clear()
        self.home, self.away = f.team("Home FC", short_name="HOM"), f.team("Away FC", short_name="AWY")
        self.striker = f.player(self.home, "Ade Striker", shirt_number=9)
        self.defender = f.player(self.away, "Bayo Defender", shirt_number=4)
        self.fixture = f.fixture(self.home, self.away, days=-1)

    def test_new_result_is_stored_with_scorers_and_cards(self):
        results.save_result(
            self.fixture, 2, 0,
            goals=[results.GoalEntry(self.striker, 10), results.GoalEntry(self.striker, 30)],
            cards=[results.CardEntry(self.defender, Card.Colour.YELLOW, 25)],
        )
        self.fixture.refresh_from_db()
        self.assertEqual(self.fixture.status, Fixture.Status.PLAYED)
        self.assertEqual(self.fixture.score, "2 - 0")
        self.assertEqual(self.fixture.goals.count(), 2)
        self.defender.refresh_from_db()
        self.assertEqual(self.defender.yellow_cards, 1)

    def test_clearing_a_result_puts_the_fixture_back(self):
        results.save_result(
            self.fixture, 1, 0,
            goals=[results.GoalEntry(self.striker, 5)],
            cards=[results.CardEntry(self.defender, Card.Colour.YELLOW, 25)],
        )
        results.clear_result(self.fixture)
        self.fixture.refresh_from_db()
        self.assertEqual(self.fixture.status, Fixture.Status.SCHEDULED)
        self.assertIsNone(self.fixture.home_goals)
        self.assertFalse(self.fixture.goals.exists())
        self.defender.refresh_from_db()
        self.assertEqual(self.defender.yellow_cards, 0)


class ResultEntryFormTests(TestCase):
    def setUp(self):
        self.home, self.away = f.team("Home FC", short_name="HOM"), f.team("Away FC", short_name="AWY")
        self.striker = f.player(self.home, "Ade Striker", shirt_number=9)
        self.fixture = f.fixture(self.home, self.away)

    def data(self, home, away, scorers=()):
        payload = {
            "home_goals": str(home), "away_goals": str(away),
            "goals-TOTAL_FORMS": str(len(scorers)), "goals-INITIAL_FORMS": "0",
            "cards-TOTAL_FORMS": "0", "cards-INITIAL_FORMS": "0",
        }
        for i, (player, minute) in enumerate(scorers):
            payload[f"goals-{i}-player"] = str(player.pk)
            payload[f"goals-{i}-minute"] = str(minute)
        return payload

    def test_valid_result(self):
        entry = ResultEntry(self.fixture, self.data(1, 0, [(self.striker, 12)]))
        self.assertTrue(entry.is_valid())
        self.assertEqual(entry.goal_entries()[0].player, self.striker)

    def test_fewer_scorers_than_goals_is_allowed(self):
        self.assertTrue(ResultEntry(self.fixture, self.data(3, 1, [(self.striker, 12)])).is_valid())

    def test_more_scorers_than_goals_is_refused(self):
        entry = ResultEntry(self.fixture, self.data(1, 0, [(self.striker, 12), (self.striker, 20)]))
        self.assertFalse(entry.is_valid())

    def test_negative_score_is_refused(self):
        self.assertFalse(ResultEntry(self.fixture, self.data(-1, 0)).is_valid())

    def test_player_from_another_team_is_refused(self):
        stranger = f.player(f.team("Other FC", short_name="OTH"), "Stranger")
        self.assertFalse(ResultEntry(self.fixture, self.data(1, 0, [(stranger, 12)])).is_valid())


class DisciplineTests(TestCase):
    def setUp(self):
        self.home, self.away = f.team("Home FC", short_name="HOM"), f.team("Away FC", short_name="AWY")
        self.hothead = f.player(self.home, "Hot Head", shirt_number=5)

    def test_red_card_bans_player_for_next_fixture(self):
        last = f.fixture(self.home, self.away, days=-2)
        results.save_result(last, 0, 0, [], [results.CardEntry(self.hothead, Card.Colour.RED, 30)])
        upcoming = f.fixture(self.away, self.home, days=5, matchday=2)
        row = discipline.discipline_table()[0]
        self.assertTrue(row.suspended)
        self.assertEqual(row.misses, upcoming)

    def test_two_yellows_is_a_warning(self):
        for days_ago, md in ((9, 1), (2, 2)):
            fixture = f.fixture(self.home, self.away, days=-days_ago, matchday=md)
            results.save_result(fixture, 1, 1, [], [results.CardEntry(self.hothead, Card.Colour.YELLOW, 10)])
        row = discipline.discipline_table()[0]
        self.assertEqual(row.yellows, 2)
        self.assertFalse(row.suspended)
        self.assertTrue(row.warning)
