"""Fixture list helpers."""

from datetime import date

from django.db.models import Max, Min, Q, QuerySet

from ..models import Fixture, Team
from ..utils import dates


def all_fixtures() -> QuerySet[Fixture]:
    return Fixture.objects.select_related("home_team", "away_team")


def matchdays() -> list[int]:
    return list(Fixture.objects.order_by("matchday").values_list("matchday", flat=True).distinct())


def current_matchday() -> int:
    """First matchday that still has a fixture to play, or the last one."""
    upcoming = Fixture.objects.filter(status=Fixture.Status.SCHEDULED).aggregate(md=Min("matchday"))["md"]
    if upcoming is not None:
        return upcoming
    return Fixture.objects.aggregate(md=Max("matchday"))["md"] or 1


def for_team(team: Team) -> QuerySet[Fixture]:
    return all_fixtures().filter(Q(home_team=team) | Q(away_team=team))


def group_by_day(fixtures) -> list[tuple[date, list[Fixture]]]:
    groups: dict[date, list[Fixture]] = {}
    for fixture in fixtures:
        groups.setdefault(dates.match_day(fixture.kickoff), []).append(fixture)
    return sorted(groups.items())


def result_letter(fixture: Fixture, team: Team) -> str:
    if not fixture.is_played:
        return ""
    ours, theirs = (
        (fixture.home_goals, fixture.away_goals)
        if fixture.home_team_id == team.pk
        else (fixture.away_goals, fixture.home_goals)
    )
    if ours > theirs:
        return "W"
    return "D" if ours == theirs else "L"
