"""Who may do what. The league has three kinds of logins: the secretary,
referees and team captains. Everything else is public."""

from django.contrib.auth.models import AnonymousUser, User

from .models import Fixture, Team

SECRETARY_GROUP = "Secretary"
REFEREE_GROUP = "Referees"


def _in_group(user: User | AnonymousUser, *names: str) -> bool:
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.groups.filter(name__in=names).exists()


def is_secretary(user: User | AnonymousUser) -> bool:
    return _in_group(user, SECRETARY_GROUP)


def can_enter_results(user: User | AnonymousUser) -> bool:
    return _in_group(user, SECRETARY_GROUP, REFEREE_GROUP)


def can_enter_result(user: User | AnonymousUser, fixture: Fixture) -> bool:
    if can_enter_results(user):
        return True
    if not user.is_authenticated:
        return False
    return user.pk in (fixture.home_team.captain_id, fixture.away_team.captain_id)


def can_manage_squad(user: User | AnonymousUser, team: Team) -> bool:
    if not user.is_authenticated:
        return False
    return is_secretary(user) or team.captain_id == user.pk
