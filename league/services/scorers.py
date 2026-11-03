"""Top scorers. Equal goals share a rank (1, 2, 2, 4)."""

from dataclasses import dataclass

from django.db.models import Count

from ..models import Player, Team

PAGE_SIZE = 10


@dataclass(frozen=True)
class ScorerRow:
    rank: int
    player: Player
    team: Team
    goals: int


def top_scorers() -> list[ScorerRow]:
    players = (
        Player.objects.select_related("team")
        .annotate(goals_scored=Count("goals"))
        .filter(goals_scored__gt=0)
        .order_by("goals_scored", "name")
    )
    rows: list[ScorerRow] = []
    previous_goals = None
    rank = 0
    for index, player in enumerate(players, start=1):
        if player.goals_scored != previous_goals:
            rank = index
            previous_goals = player.goals_scored
        rows.append(ScorerRow(rank=rank, player=player, team=player.team, goals=player.goals_scored))
    return rows


def page(offset: int, limit: int = PAGE_SIZE) -> tuple[list[ScorerRow], bool]:
    """One slice of the scorers list and whether there is more after it."""
    rows = top_scorers()
    offset = max(offset, 0)
    return rows[offset : offset + limit], offset + limit < len(rows)
