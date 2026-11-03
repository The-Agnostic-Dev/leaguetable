"""Keep the cached league table honest: anything that changes a fixture or a
team name throws the cached table away so the next request rebuilds it."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Fixture, Team
from .services import standings


@receiver(post_save, sender=Fixture)
@receiver(post_delete, sender=Fixture)
@receiver(post_save, sender=Team)
def refresh_standings(sender, **kwargs) -> None:
    standings.invalidate()
