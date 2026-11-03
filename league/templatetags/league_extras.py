from django import template

from ..utils import dates

register = template.Library()


@register.filter
def matchdate(kickoff):
    """Day a fixture is played on, e.g. "Friday 13 November 2026"."""
    if not kickoff:
        return ""
    return dates.match_day(kickoff).strftime("%A %-d %B %Y")


@register.filter
def signed(value: int) -> str:
    return f"+{value}" if value > 0 else str(value)


@register.filter
def ordinal(value: int) -> str:
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"
