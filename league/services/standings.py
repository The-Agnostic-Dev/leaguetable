"""The league table.

Order (see README, "How the table is sorted"): points, then goal difference,
then goals scored, then head-to-head points between the teams still level,
then team name.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from django.conf import settings
from django.core.cache import cache

from ..models import Fixture, Team

CACHE_KEY = "standings:table"
POINTS_FOR_WIN = 3
POINTS_FOR_DRAW = 1
FORM_LENGTH = 5


@dataclass
class Row:
    team: Team
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    form: list[str] = field(default_factory=list)
    position: int = 0

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def points(self) -> int:
        return self.won * POINTS_FOR_WIN + self.drawn * POINTS_FOR_DRAW

    @property
    def recent_form(self) -> list[str]:
        return self.form[-FORM_LENGTH:]


def _record(row: Row, scored: int, conceded: int) -> None:
    row.goals_for += scored
    row.goals_against += conceded
    if scored > conceded:
        row.won += 1
        row.form.append("W")
    elif scored == conceded:
        row.drawn += 1
        row.form.append("D")
    else:
        row.lost += 1
        row.form.append("L")


def _head_to_head_points(tied: list[Row], fixtures: list[Fixture]) -> dict[int, int]:
    """Points each tied team took from the matches between the tied teams only."""
    team_ids = {row.team.pk for row in tied}
    points: dict[int, int] = defaultdict(int)
    for fixture in fixtures:
        if fixture.home_team_id not in team_ids or fixture.away_team_id not in team_ids:
            continue
        if fixture.home_goals > fixture.away_goals:
            points[fixture.home_team_id] += POINTS_FOR_WIN
        elif fixture.home_goals < fixture.away_goals:
            points[fixture.away_team_id] += POINTS_FOR_WIN
        else:
            points[fixture.home_team_id] += POINTS_FOR_DRAW
            points[fixture.away_team_id] += POINTS_FOR_DRAW
    return points


def _sort_rows(rows: list[Row], played: list[Fixture]) -> list[Row]:
    by_points: dict[int, list[Row]] = defaultdict(list)
    for row in rows:
        by_points[row.points].append(row)

    ordered: list[Row] = []
    for points in sorted(by_points, reverse=True):
        tied = by_points[points]
        h2h = _head_to_head_points(tied, played) if len(tied) > 1 else {}
        tied.sort(
            key=lambda row: (
                -row.goal_difference,
                -row.goals_for,
                -h2h.get(row.team.pk, 0),
                row.team.name,
            )
        )
        ordered.extend(tied)
    return ordered


def build_table() -> list[Row]:
    rows = {team.pk: Row(team=team) for team in Team.objects.all()}
    fixtures = list(Fixture.objects.select_related("home_team", "away_team").order_by("kickoff", "pk"))
    played: list[Fixture] = []

    for fixture in fixtures:
        home, away = rows[fixture.home_team_id], rows[fixture.away_team_id]
        if not fixture.is_played:
            continue
        home.played += 1
        away.played += 1
        _record(home, fixture.home_goals, fixture.away_goals)
        _record(away, fixture.away_goals, fixture.home_goals)
        played.append(fixture)

    ordered = _sort_rows(list(rows.values()), played)
    for position, row in enumerate(ordered, start=1):
        row.position = position
    return ordered


def get_table() -> list[Row]:
    return cache.get_or_set(CACHE_KEY, build_table, settings.STANDINGS_CACHE_SECONDS)


def invalidate() -> None:
    cache.delete(CACHE_KEY)


def position_of(team: Team) -> Row | None:
    return next((row for row in get_table() if row.team.pk == team.pk), None)
