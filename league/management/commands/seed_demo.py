"""Load the demo season: 8 teams, 14 matchdays on Friday nights, the first six
played. Dates are relative to today so the demo always looks current.

    python manage.py seed_demo
"""

import random
from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.functional import cached_property

from league import permissions
from league.models import Fixture, Player, Team
from league.services import results, standings
from league.utils import dates

PASSWORD = "leaguetable2026"
PLAYED_MATCHDAYS = 6
KICKOFF_HOURS = (19, 20, 21, 22)

TEAMS = [
    ("Yaba Ballers", "YAB", "Sky blue and white", "captain.yaba", "Chidi", "Okonkwo"),
    ("Lekki Lions", "LEK", "Gold and black", "captain.lekki", "Kunle", "Afolabi"),
    ("Surulere United", "SUR", "Red", "captain.surulere", "Rotimi", "Alade"),
    ("Ikoyi Strikers", "IKO", "Navy", "captain.ikoyi", "Ayo", "Fadipe"),
    ("Ajah Warriors", "AJA", "Green and white", "captain.ajah", "Jide", "Ogundipe"),
    ("Ikeja City", "IKJ", "Maroon", "captain.ikeja", "Rasheed", "Adisa"),
    ("Gbagada Rangers", "GBA", "Orange", "captain.gbagada", "Kunle", "Ajibade"),
    ("Festac Stars", "FES", "Purple", "captain.festac", "Eric", "Ekpo"),
]

GK, DF, MF, FW = (Player.Position.GOALKEEPER, Player.Position.DEFENDER, Player.Position.MIDFIELDER,
                  Player.Position.FORWARD)

SQUADS = {
    "YAB": [(1, "Emeka Okafor", GK), (4, "Tunde Bakare", DF), (5, "Kelechi Nwosu", DF), (7, "Segun Adeyemi", MF),
            (8, "Ifeanyi Obi", MF), (9, "Babatunde Lawal", FW), (10, "Chidi Okonkwo", FW), (11, "Damilare Ogunleye", FW)],
    "LEK": [(1, "Femi Akinola", GK), (3, "Olumide Bello", DF), (5, "Uche Eze", DF), (6, "Abdullahi Musa", MF),
            (8, "Kunle Afolabi", MF), (9, "Ikenna Udeh", FW), (10, "Seun Ojo", FW), (14, "Victor Etim", FW)],
    "SUR": [(1, "Yusuf Garba", GK), (2, "Gbenga Fashola", DF), (4, "Obinna Chukwu", DF), (6, "Rotimi Alade", MF),
            (7, "Sodiq Balogun", MF), (9, "Kayode Ajayi", FW), (10, "Nnamdi Agu", FW), (17, "Dapo Oyewole", FW)],
    "IKO": [(1, "Tobenna Ibe", GK), (3, "Wale Ogunbiyi", DF), (5, "Chuka Nnaji", DF), (6, "Kola Oyedepo", MF),
            (8, "Ayo Fadipe", MF), (10, "Musa Danjuma", FW), (11, "Tobi Ademola", FW), (19, "Efe Omoregie", FW)],
    "AJA": [(1, "Ebuka Mba", GK), (2, "Lanre Shittu", DF), (4, "Paul Effiong", DF), (7, "Jide Ogundipe", MF),
            (8, "Sani Abubakar", MF), (9, "Kenneth Onu", FW), (10, "Bayo Ogunsanya", FW), (15, "Chukwuma Ani", FW)],
    "IKJ": [(1, "Moses Edet", GK), (3, "Ibrahim Yakubu", DF), (4, "Felix Okoro", DF), (6, "Rasheed Adisa", MF),
            (8, "Olamide Coker", MF), (9, "Ikechukwu Ezeh", FW), (10, "Taiwo Kehinde", FW), (11, "Peter Odili", FW)],
    "GBA": [(1, "Adewale Ige", GK), (2, "Sunday Okpara", DF), (5, "Ugochukwu Onyeka", DF), (6, "Kunle Ajibade", MF),
            (8, "Ademola Salami", MF), (9, "Chibuzor Okeke", FW), (10, "Femi Olatunji", FW), (12, "Godwin Akpan", FW)],
    "FES": [(1, "Oluwaseun Dada", GK), (3, "Ekene Ude", DF), (4, "Bolaji Sanni", DF), (7, "Eric Ekpo", MF),
            (8, "Habeeb Ola", MF), (9, "Chinedu Anyanwu", FW), (10, "Gbolahan Osho", FW), (11, "Lucky Ighodaro", FW)],
}

# (home, home goals, away goals, away) for matchdays 1 to 6, four games each.
PLAYED_SCORES = [
    [("YAB", 4, 2, "FES"), ("GBA", 3, 4, "LEK"), ("SUR", 0, 0, "IKJ"), ("AJA", 2, 4, "IKO")],
    [("GBA", 2, 1, "YAB"), ("FES", 1, 3, "IKJ"), ("AJA", 4, 1, "LEK"), ("SUR", 3, 2, "IKO")],
    [("YAB", 3, 2, "IKJ"), ("AJA", 2, 2, "GBA"), ("FES", 0, 6, "IKO"), ("SUR", 3, 1, "LEK")],
    [("AJA", 3, 3, "YAB"), ("IKJ", 2, 2, "IKO"), ("SUR", 1, 4, "GBA"), ("FES", 2, 2, "LEK")],
    [("YAB", 3, 1, "IKO"), ("SUR", 3, 2, "AJA"), ("IKJ", 1, 4, "LEK"), ("FES", 3, 2, "GBA")],
    [("SUR", 2, 3, "YAB"), ("IKO", 4, 2, "LEK"), ("FES", 1, 3, "AJA"), ("IKJ", 2, 2, "GBA")],
]

# (matchday, home team, player, colour, minute)
CARDS = [
    (1, "YAB", "Bolaji Sanni", "Y", 22), (1, "YAB", "Tunde Bakare", "Y", 31),
    (2, "AJA", "Lanre Shittu", "Y", 15), (2, "AJA", "Uche Eze", "Y", 30),
    (2, "SUR", "Gbenga Fashola", "Y", 12), (2, "SUR", "Chuka Nnaji", "R", 35),
    (3, "YAB", "Tunde Bakare", "Y", 18),
    (3, "AJA", "Sunday Okpara", "Y", 25), (3, "AJA", "Lanre Shittu", "Y", 33),
    (4, "SUR", "Gbenga Fashola", "Y", 9), (4, "SUR", "Sunday Okpara", "Y", 38),
    (4, "FES", "Bolaji Sanni", "Y", 27),
    (5, "IKJ", "Felix Okoro", "Y", 14), (5, "IKJ", "Olumide Bello", "Y", 29),
    (5, "SUR", "Lanre Shittu", "Y", 20),
    (6, "SUR", "Tunde Bakare", "Y", 26),
    (6, "IKO", "Seun Ojo", "R", 33),
]

SCORER_WEIGHTS = {GK: 0, DF: 1, MF: 3, FW: 6}


def round_robin(codes: list[str]) -> list[list[tuple[str, str]]]:
    """Double round robin by the circle method; second half mirrors the first."""
    order = codes[:]
    half: list[list[tuple[str, str]]] = []
    for rnd in range(len(order) - 1):
        pairs = []
        for i in range(len(order) // 2):
            home, away = order[i], order[-1 - i]
            if (rnd + i) % 2:
                home, away = away, home
            pairs.append((home, away))
        half.append(pairs)
        order = [order[0], order[-1], *order[1:-1]]
    return half + [[(away, home) for home, away in pairs] for pairs in half]


class Command(BaseCommand):
    help = "Replace all league data with the demo season."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        Fixture.objects.all().delete()
        Team.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        User.objects.filter(username="admin").delete()

        secretary_group, _ = Group.objects.get_or_create(name=permissions.SECRETARY_GROUP)
        referee_group, _ = Group.objects.get_or_create(name=permissions.REFEREE_GROUP)
        self._user("secretary", "Funmilayo", "Adebayo", secretary_group)
        self._user("referee", "Sule", "Ibrahim", referee_group)
        admin = self._user("admin", "League", "Admin")
        admin.is_staff = admin.is_superuser = True
        admin.save()

        teams: dict[str, Team] = {}
        players: dict[str, Player] = {}
        for name, code, colours, username, first, last in TEAMS:
            captain = self._user(username, first, last)
            team = Team.objects.create(name=name, short_name=code, colours=colours, captain=captain)
            teams[code] = team
            for number, player_name, position in SQUADS[code]:
                players[player_name] = Player.objects.create(
                    team=team, name=player_name, shirt_number=number, position=position
                )

        first_upcoming = dates.friday_on_or_after(dates.today())
        fixtures: dict[tuple[int, str], Fixture] = {}
        for matchday, pairs in enumerate(round_robin(list(teams)), start=1):
            night = first_upcoming + timedelta(weeks=matchday - PLAYED_MATCHDAYS - 1)
            for slot, (home, away) in enumerate(pairs):
                fixtures[(matchday, home)] = Fixture.objects.create(
                    matchday=matchday,
                    home_team=teams[home],
                    away_team=teams[away],
                    kickoff=dates.at_lagos_time(night, KICKOFF_HOURS[slot]),
                    pitch=f"Pitch {slot % 2 + 1}",
                )

        rng = random.Random(2026)
        for matchday, games in enumerate(PLAYED_SCORES, start=1):
            for home, home_goals, away_goals, away in games:
                fixture = fixtures[(matchday, home)]
                assert fixture.away_team.short_name == away, (matchday, home, away)
                goals = self._scorers(rng, teams[home], home_goals) + self._scorers(rng, teams[away], away_goals)
                cards = [
                    results.CardEntry(player=players[name], colour=colour, minute=minute)
                    for md, code, name, colour, minute in CARDS
                    if md == matchday and code == home
                ]
                results.save_result(fixture, home_goals, away_goals, goals, cards)

        standings.invalidate()
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(teams)} teams, {len(players)} players, {len(fixtures)} fixtures. "
                f"Logins: secretary, referee, captain.<area> / {PASSWORD}"
            )
        )

    @cached_property
    def _password_hash(self) -> str:
        # Hash once: every demo account shares the same password.
        return make_password(PASSWORD)

    def _user(self, username: str, first: str, last: str, group: Group | None = None) -> User:
        user = User.objects.create(username=username, email=f"{username}@leaguetable.local",
                                   first_name=first, last_name=last, password=self._password_hash)
        if group:
            user.groups.add(group)
        return user

    @staticmethod
    def _scorers(rng: random.Random, team: Team, count: int) -> list[results.GoalEntry]:
        squad = list(team.players.all())
        weights = [SCORER_WEIGHTS[p.position] for p in squad]
        minutes = sorted(rng.sample(range(1, 41), count))
        return [results.GoalEntry(player=rng.choices(squad, weights)[0], minute=m) for m in minutes]
