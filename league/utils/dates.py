"""Date helpers. The league plays in Lagos, so everything a user sees is in
Africa/Lagos (settings.TIME_ZONE); the database stores UTC."""

from datetime import date, datetime, timedelta

from django.utils import timezone


def match_day(kickoff: datetime) -> date:
    """The calendar day a fixture is played on."""
    return kickoff.date()


def today() -> date:
    return timezone.localdate()


def friday_on_or_after(day: date) -> date:
    """League nights are Fridays."""
    return day + timedelta(days=(4 - day.weekday()) % 7)


def at_lagos_time(day: date, hour: int, minute: int = 0) -> datetime:
    """An aware datetime for a wall-clock time in Lagos on the given day."""
    naive = datetime(day.year, day.month, day.day, hour, minute)
    return timezone.make_aware(naive, timezone.get_default_timezone())
