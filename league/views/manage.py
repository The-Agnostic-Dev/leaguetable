"""Fixture and squad management (secretary and captains)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .. import permissions
from ..forms import FixtureForm, PlayerForm
from ..models import Fixture, Player, Team


@login_required
def edit_fixture(request: HttpRequest, pk: int) -> HttpResponse:
    if not permissions.is_secretary(request.user):
        raise PermissionDenied
    fixture = get_object_or_404(Fixture.objects.select_related("home_team", "away_team"), pk=pk)
    form = FixtureForm(request.POST or None, instance=fixture)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Fixture updated.")
        return redirect("fixture_detail", pk=fixture.pk)
    return render(request, "league/fixture_form.html", {"fixture": fixture, "form": form})


@login_required
def add_player(request: HttpRequest, pk: int) -> HttpResponse:
    team = get_object_or_404(Team, pk=pk)
    if not permissions.can_manage_squad(request.user, team):
        raise PermissionDenied
    form = PlayerForm(request.POST or None, team=team)
    if request.method == "POST" and form.is_valid():
        player = form.save()
        messages.success(request, f"{player.name} added to {team.name}.")
        return redirect("team_detail", pk=team.pk)
    return render(request, "league/player_form.html", {"team": team, "form": form})


@login_required
@require_POST
def remove_player(request: HttpRequest, pk: int) -> HttpResponse:
    player = get_object_or_404(Player.objects.select_related("team"), pk=pk)
    if not permissions.can_manage_squad(request.user, player.team):
        raise PermissionDenied
    if player.goals.exists() or player.cards.exists():
        messages.error(request, f"{player.name} has goals or cards this season and can't be removed.")
    else:
        player.delete()
        messages.success(request, f"{player.name} removed from the squad.")
    return redirect("team_detail", pk=player.team_id)
