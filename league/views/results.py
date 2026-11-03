"""Result entry for the secretary and referees."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .. import permissions
from ..forms import ResultEntry
from ..models import Fixture
from ..services import results as result_service


@login_required
def enter_result(request: HttpRequest, pk: int) -> HttpResponse:
    if not permissions.can_enter_results(request.user):
        raise PermissionDenied
    fixture = get_object_or_404(Fixture.objects.select_related("home_team", "away_team"), pk=pk)
    if fixture.status == Fixture.Status.POSTPONED:
        messages.error(request, "This fixture is postponed. Reschedule it before entering a result.")
        return redirect("fixture_detail", pk=fixture.pk)

    entry = ResultEntry(fixture, request.POST if request.method == "POST" else None)
    if request.method == "POST" and entry.is_valid():
        result_service.save_result(
            fixture,
            home_goals=entry.score.cleaned_data["home_goals"],
            away_goals=entry.score.cleaned_data["away_goals"],
            goals=entry.goal_entries(),
            cards=entry.card_entries(),
        )
        messages.success(request, f"Result saved: {fixture.home_team} {fixture.score} {fixture.away_team}.")
        return redirect("fixture_detail", pk=fixture.pk)
    return render(request, "league/result_form.html", {"fixture": fixture, "entry": entry})


@login_required
@require_POST
def clear_result(request: HttpRequest, pk: int) -> HttpResponse:
    if not permissions.is_secretary(request.user):
        raise PermissionDenied
    fixture = get_object_or_404(Fixture, pk=pk)
    if fixture.is_played:
        result_service.clear_result(fixture)
        messages.success(request, "Result cleared. The fixture is back to scheduled.")
    return redirect("fixture_detail", pk=fixture.pk)
