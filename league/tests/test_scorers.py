from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from league.models import Fixture, Player, Team
from league.services import results, scorers


class TopScorersTests(TestCase):
    def test_players_ordered_by_goals_descending_with_ranks(self):
        User = get_user_model()
        captain1 = User.objects.create_user(username="cap1", password="test")
        captain2 = User.objects.create_user(username="cap2", password="test")

        team1 = Team.objects.create(name="Team One", short_name="ONE", colours="Red", captain=captain1)
        team2 = Team.objects.create(name="Team Two", short_name="TWO", colours="Blue", captain=captain2)

        player1 = Player.objects.create(team=team1, name="Player One", shirt_number=9, position=Player.Position.FORWARD)
        player2 = Player.objects.create(team=team2, name="Player Two", shirt_number=10, position=Player.Position.FORWARD)
        player3 = Player.objects.create(team=team1, name="Player Three", shirt_number=7, position=Player.Position.MIDFIELDER)

        fixture1 = Fixture.objects.create(
            matchday=1,
            home_team=team1,
            away_team=team2,
            kickoff=timezone.now(),
            pitch="Main Pitch",
        )
        fixture2 = Fixture.objects.create(
            matchday=2,
            home_team=team2,
            away_team=team1,
            kickoff=timezone.now() + timedelta(days=7),
            pitch="Main Pitch",
        )

        goals1 = [
            results.GoalEntry(player=player1, minute=10),
            results.GoalEntry(player=player1, minute=20),
            results.GoalEntry(player=player2, minute=15),
        ]
        goals2 = [
            results.GoalEntry(player=player2, minute=30),
            results.GoalEntry(player=player3, minute=40),
            results.GoalEntry(player=player1, minute=50),
        ]

        results.save_result(fixture1, 2, 1, goals1, [])
        results.save_result(fixture2, 1, 2, goals2, [])

        scorers_list = list(scorers.top_scorers())
        self.assertEqual(len(scorers_list), 3)
        self.assertEqual([s.goals_scored for s in scorers_list], [3, 2, 1])
        self.assertEqual([s.rank for s in scorers_list], [1, 2, 3])
        self.assertEqual(scorers_list[0].name, "Player One")
        self.assertEqual(scorers_list[1].name, "Player Two")
        self.assertEqual(scorers_list[2].name, "Player Three")

    def test_tied_players_share_rank_and_next_skips(self):
        User = get_user_model()
        captain1 = User.objects.create_user(username="cap3", password="test")
        captain2 = User.objects.create_user(username="cap4", password="test")

        team1 = Team.objects.create(name="Team Alpha", short_name="ALP", colours="Green", captain=captain1)
        team2 = Team.objects.create(name="Team Beta", short_name="BET", colours="Yellow", captain=captain2)

        player1 = Player.objects.create(team=team1, name="Alpha One", shirt_number=9, position=Player.Position.FORWARD)
        player2 = Player.objects.create(team=team2, name="Beta One", shirt_number=10, position=Player.Position.FORWARD)
        player3 = Player.objects.create(team=team1, name="Alpha Two", shirt_number=7, position=Player.Position.MIDFIELDER)

        fixture1 = Fixture.objects.create(
            matchday=1,
            home_team=team1,
            away_team=team2,
            kickoff=timezone.now(),
            pitch="Main Pitch",
        )
        fixture2 = Fixture.objects.create(
            matchday=2,
            home_team=team2,
            away_team=team1,
            kickoff=timezone.now() + timedelta(days=7),
            pitch="Main Pitch",
        )

        goals1 = [
            results.GoalEntry(player=player1, minute=10),
            results.GoalEntry(player=player1, minute=20),
            results.GoalEntry(player=player2, minute=15),
        ]
        goals2 = [
            results.GoalEntry(player=player2, minute=30),
            results.GoalEntry(player=player3, minute=40),
        ]

        results.save_result(fixture1, 2, 1, goals1, [])
        results.save_result(fixture2, 1, 1, goals2, [])

        scorers_list = list(scorers.top_scorers())
        self.assertEqual(len(scorers_list), 3)
        self.assertEqual([s.goals_scored for s in scorers_list], [2, 2, 1])
        self.assertEqual([s.rank for s in scorers_list], [1, 1, 3])
