"""Small builders for tests."""

from datetime import timedelta
from itertools import count

from django.contrib.auth.models import Group, User
from django.utils import timezone

from league import permissions
from league.models import Fixture, Player, Team

_seq = count(1)


def team(name: str | None = None, **kwargs) -> Team:
    n = next(_seq)
    return Team.objects.create(name=name or f"Team {n}", short_name=kwargs.pop("short_name", f"T{n}"), **kwargs)


def player(team: Team, name: str | None = None, **kwargs) -> Player:
    n = next(_seq)
    return Player.objects.create(team=team, name=name or f"Player {n}", shirt_number=kwargs.pop("shirt_number", n % 99 + 1), **kwargs)


def fixture(home: Team, away: Team, days: int = 7, matchday: int = 1, **kwargs) -> Fixture:
    kickoff = kwargs.pop("kickoff", timezone.now() + timedelta(days=days))
    return Fixture.objects.create(home_team=home, away_team=away, kickoff=kickoff, matchday=matchday, **kwargs)


def played(home: Team, away: Team, home_goals: int, away_goals: int, days_ago: int = 7, matchday: int = 1) -> Fixture:
    return fixture(
        home, away, days=-days_ago, matchday=matchday,
        status=Fixture.Status.PLAYED, home_goals=home_goals, away_goals=away_goals,
    )


def user(username: str, group: str | None = None) -> User:
    account = User.objects.create_user(username, password="pass-for-tests")
    if group:
        account.groups.add(Group.objects.get_or_create(name=group)[0])
    return account


def secretary() -> User:
    return user("sec", permissions.SECRETARY_GROUP)


def referee() -> User:
    return user("ref", permissions.REFEREE_GROUP)
