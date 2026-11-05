from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from league.models import Player
from league.services import scorers, standings as standings_service

from . import factories as f


class PublicPagesTests(TestCase):
    def setUp(self):
        cache.clear()
        self.home, self.away = f.team("Yaba Ballers", short_name="YAB"), f.team("Lekki Lions", short_name="LEK")
        f.player(self.home, "Tunde Bakare", shirt_number=4)
        self.fixture = f.fixture(self.home, self.away)

    def test_pages_render(self):
        for name, args in [
            ("standings", []), ("fixtures", []), ("fixture_detail", [self.fixture.pk]), ("scorers", []),
            ("discipline", []), ("teams", []), ("team_detail", [self.home.pk]), ("players", []),
        ]:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 200)

    def test_fixtures_page_shows_requested_matchday(self):
        response = self.client.get(reverse("fixtures"), {"matchday": 1})
        self.assertContains(response, "Matchday 1")
        self.assertContains(response, "Yaba Ballers")

    def test_scorers_more_returns_json(self):
        data = self.client.get(reverse("scorers_more"), {"offset": 0}).json()
        self.assertEqual(set(data), {"html", "has_more"})

    def test_scorer_pages_do_not_overlap(self):
        for i in range(scorers.PAGE_SIZE + 3):
            f.player(self.away, f"Scorer {i}", shirt_number=i + 10)
        fixture = f.played(self.home, self.away, 0, 0)
        for player in Player.objects.filter(name__startswith="Scorer"):
            fixture.goals.create(player=player, minute=5)
        first, more = scorers.page(0)
        second, more_after = scorers.page(scorers.PAGE_SIZE)
        self.assertTrue(more)
        self.assertFalse(more_after)
        self.assertEqual(len(first) + len(second), scorers.PAGE_SIZE + 3)
        self.assertFalse({r.player.pk for r in first} & {r.player.pk for r in second})


class PermissionTests(TestCase):
    def setUp(self):
        self.home, self.away = f.team("Yaba Ballers", short_name="YAB"), f.team("Lekki Lions", short_name="LEK")
        self.fixture = f.fixture(self.home, self.away, days=-1)

    def test_result_entry_needs_login(self):
        response = self.client.get(reverse("enter_result", args=[self.fixture.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_home_captain_can_enter_and_post_result(self):
        captain = f.user("captain.yaba")
        self.home.captain = captain
        self.home.save()
        self.client.force_login(captain)
        url = reverse("enter_result", args=[self.fixture.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.post(url, {
            "home_goals": "2",
            "away_goals": "1",
            "goals-TOTAL_FORMS": "0",
            "goals-INITIAL_FORMS": "0",
            "goals-MIN_NUM_FORMS": "0",
            "goals-MAX_NUM_FORMS": "1000",
            "cards-TOTAL_FORMS": "0",
            "cards-INITIAL_FORMS": "0",
            "cards-MIN_NUM_FORMS": "0",
            "cards-MAX_NUM_FORMS": "1000",
        })
        self.assertRedirects(response, reverse("fixture_detail", args=[self.fixture.pk]))
        self.fixture.refresh_from_db()
        self.assertTrue(self.fixture.is_played)
        self.assertEqual(self.fixture.home_goals, 2)
        self.assertEqual(self.fixture.away_goals, 1)
        table = standings_service.get_table()
        home_row = next(row for row in table if row.team.pk == self.home.pk)
        self.assertEqual((home_row.played, home_row.won, home_row.goals_for, home_row.goals_against), (1, 1, 2, 1))

    def test_unrelated_captain_cannot_enter_results(self):
        other_team = f.team("Ajah Warriors", short_name="AJA")
        captain = f.user("captain.ajah")
        other_team.captain = captain
        other_team.save()
        self.client.force_login(captain)
        self.assertEqual(self.client.get(reverse("enter_result", args=[self.fixture.pk])).status_code, 403)

    def test_fixture_detail_shows_result_entry_to_home_captain(self):
        captain = f.user("captain.yaba")
        self.home.captain = captain
        self.home.save()
        self.client.force_login(captain)
        response = self.client.get(reverse("fixture_detail", args=[self.fixture.pk]))
        self.assertContains(response, reverse("enter_result", args=[self.fixture.pk]))

    def test_fixture_detail_hides_result_entry_from_unrelated_captain(self):
        other_team = f.team("Ajah Warriors", short_name="AJA")
        captain = f.user("captain.ajah")
        other_team.captain = captain
        other_team.save()
        self.client.force_login(captain)
        response = self.client.get(reverse("fixture_detail", args=[self.fixture.pk]))
        self.assertNotContains(response, reverse("enter_result", args=[self.fixture.pk]))

    def test_fixture_detail_hides_result_entry_from_anonymous_user(self):
        response = self.client.get(reverse("fixture_detail", args=[self.fixture.pk]))
        self.assertNotContains(response, reverse("enter_result", args=[self.fixture.pk]))

    def test_referee_can_enter_results(self):
        self.client.force_login(f.referee())
        self.assertEqual(self.client.get(reverse("enter_result", args=[self.fixture.pk])).status_code, 200)

    def test_captain_adds_player_to_own_team_only(self):
        captain = f.user("captain.yaba")
        self.home.captain = captain
        self.home.save()
        self.client.force_login(captain)
        response = self.client.post(
            reverse("add_player", args=[self.home.pk]), {"name": "Segun  Adeyemi", "shirt_number": 7, "position": "MF"}
        )
        self.assertRedirects(response, reverse("team_detail", args=[self.home.pk]))
        self.assertTrue(self.home.players.filter(name="Segun Adeyemi").exists())
        other = self.client.get(reverse("add_player", args=[self.away.pk]))
        self.assertEqual(other.status_code, 403)

    def test_shirt_numbers_are_unique_per_squad(self):
        f.player(self.home, "Existing", shirt_number=7)
        self.client.force_login(f.secretary())
        response = self.client.post(
            reverse("add_player", args=[self.home.pk]), {"name": "New Boy", "shirt_number": 7, "position": "MF"}
        )
        self.assertContains(response, "already taken")

    def test_only_secretary_can_reschedule(self):
        self.client.force_login(f.referee())
        self.assertEqual(self.client.get(reverse("edit_fixture", args=[self.fixture.pk])).status_code, 403)

    def test_result_form_has_empty_form_templates_matching_formset_prefixes(self):
        self.client.force_login(f.referee())
        response = self.client.get(reverse("enter_result", args=[self.fixture.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="goals-rows"')
        self.assertContains(response, 'id="goals-empty-form"')
        self.assertContains(response, 'id="cards-rows"')
        self.assertContains(response, 'id="cards-empty-form"')
        self.assertContains(response, 'id_goals-TOTAL_FORMS')
        self.assertContains(response, 'id_cards-TOTAL_FORMS')
