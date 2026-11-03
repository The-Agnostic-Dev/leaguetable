"""Cards and suspensions.

League rules (README, "Discipline"):
- A red card means the player misses his team's next fixture.
- Every third yellow card of the season (3rd, 6th, 9th...) also means a
  one-match ban, served in the team's next fixture.
- Yellow cards do not reset during the season.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from django.db.models import Count, F, Q

from ..models import Card, Fixture, Player

YELLOWS_PER_BAN = 3


def record_cards(cards: Iterable[Card]) -> None:
    """Add newly shown yellow cards to each player's season tally."""
    for card in cards:
        if card.colour == Card.Colour.YELLOW:
            Player.objects.filter(pk=card.player_id).update(yellow_cards=F("yellow_cards") + 1)


def unrecord_cards(cards: Iterable[Card]) -> None:
    """Take yellow cards that are being withdrawn back off the tally."""
    for card in cards:
        if card.colour == Card.Colour.YELLOW:
            Player.objects.filter(pk=card.player_id, yellow_cards__gt=0).update(
                yellow_cards=F("yellow_cards") - 1
            )


@dataclass
class DisciplineRow:
    player: Player
    yellows: int
    reds: int
    suspended: bool
    misses: Fixture | None
    warning: bool


def _last_played(team_id: int) -> Fixture | None:
    return (
        Fixture.objects.filter(Q(home_team_id=team_id) | Q(away_team_id=team_id), status=Fixture.Status.PLAYED)
        .order_by("-kickoff")
        .first()
    )


def next_fixture(team_id: int, after: Fixture | None = None) -> Fixture | None:
    fixtures = Fixture.objects.select_related("home_team", "away_team").filter(
        Q(home_team_id=team_id) | Q(away_team_id=team_id), status=Fixture.Status.SCHEDULED
    )
    if after is not None:
        fixtures = fixtures.filter(kickoff__gt=after.kickoff)
    return fixtures.order_by("kickoff").first()


def is_banned(player: Player, last: Fixture | None) -> bool:
    if last is None:
        return False
    shown = [card.colour for card in last.cards.all() if card.player_id == player.pk]
    if Card.Colour.RED in shown:
        return True
    return Card.Colour.YELLOW in shown and player.yellow_cards > 0 and player.yellow_cards % YELLOWS_PER_BAN == 0


def discipline_table() -> list[DisciplineRow]:
    players = (
        Player.objects.select_related("team")
        .annotate(reds=Count("cards", filter=Q(cards__colour=Card.Colour.RED)))
        .filter(Q(yellow_cards__gt=0) | Q(reds__gt=0))
        .order_by("team__name", "name")
    )
    last_by_team: dict[int, Fixture | None] = {}
    rows: list[DisciplineRow] = []
    for player in players:
        if player.team_id not in last_by_team:
            last_by_team[player.team_id] = _last_played(player.team_id)
        last = last_by_team[player.team_id]
        banned = is_banned(player, last)
        rows.append(
            DisciplineRow(
                player=player,
                yellows=player.yellow_cards,
                reds=player.reds,
                suspended=banned,
                misses=next_fixture(player.team_id, after=last) if banned else None,
                warning=not banned and player.yellow_cards % YELLOWS_PER_BAN == YELLOWS_PER_BAN - 1,
            )
        )
    rows.sort(key=lambda row: (not row.suspended, not row.warning, row.player.team.name, row.player.name))
    return rows
