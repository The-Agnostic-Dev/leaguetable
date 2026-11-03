"""Entering and clearing match results."""

from dataclasses import dataclass

from django.db import transaction

from ..models import Card, Fixture, Goal, Player
from . import discipline


@dataclass(frozen=True)
class GoalEntry:
    player: Player
    minute: int


@dataclass(frozen=True)
class CardEntry:
    player: Player
    colour: str
    minute: int


@transaction.atomic
def save_result(
    fixture: Fixture,
    home_goals: int,
    away_goals: int,
    goals: list[GoalEntry],
    cards: list[CardEntry],
) -> Fixture:
    """Store the final score, scorers and cards. Used for new results and corrections."""
    fixture.goals.all().delete()
    fixture.cards.all().delete()

    fixture.home_goals = home_goals
    fixture.away_goals = away_goals
    fixture.status = Fixture.Status.PLAYED
    fixture.save()

    Goal.objects.bulk_create(Goal(fixture=fixture, player=g.player, minute=g.minute) for g in goals)
    new_cards = Card.objects.bulk_create(
        Card(fixture=fixture, player=c.player, colour=c.colour, minute=c.minute) for c in cards
    )
    discipline.record_cards(new_cards)
    return fixture


@transaction.atomic
def clear_result(fixture: Fixture) -> None:
    """Undo a result that was entered against the wrong fixture."""
    discipline.unrecord_cards(fixture.cards.all())
    fixture.goals.all().delete()
    fixture.cards.all().delete()
    Fixture.objects.filter(pk=fixture.pk).update(
        status=Fixture.Status.SCHEDULED,
        home_goals=None,
        away_goals=None,
    )
