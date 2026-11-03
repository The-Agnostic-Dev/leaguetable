"""Pages anyone can open: table, fixtures, scorers, discipline, teams."""

from django.db.models import Count
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string

from .. import permissions
from ..models import Fixture, Player, Team
from ..services import discipline as discipline_service
from ..services import fixtures as fixture_service
from ..services import scorers as scorer_service
from ..services import standings as standings_service


def standings(request: HttpRequest) -> HttpResponse:
    return render(request, "league/standings.html", {"table": standings_service.get_table()})


def fixtures(request: HttpRequest) -> HttpResponse:
    matchdays = fixture_service.matchdays()
    try:
        matchday = int(request.GET.get("matchday", ""))
    except ValueError:
        matchday = fixture_service.current_matchday()
    fixture_list = fixture_service.all_fixtures().filter(matchday=matchday).order_by("kickoff", "pk")
    return render(
        request,
        "league/fixtures.html",
        {
            "matchday": matchday,
            "matchdays": matchdays,
            "days": fixture_service.group_by_day(fixture_list),
        },
    )


def fixture_detail(request: HttpRequest, pk: int) -> HttpResponse:
    fixture = get_object_or_404(fixture_service.all_fixtures(), pk=pk)
    goals = fixture.goals.select_related("player", "player__team")
    cards = fixture.cards.select_related("player", "player__team")
    return render(
        request,
        "league/fixture_detail.html",
        {
            "fixture": fixture,
            "home_goals": [g for g in goals if g.player.team_id == fixture.home_team_id],
            "away_goals": [g for g in goals if g.player.team_id == fixture.away_team_id],
            "cards": cards,
        },
    )


def scorers(request: HttpRequest) -> HttpResponse:
    rows, has_more = scorer_service.page(0)
    return render(
        request,
        "league/scorers.html",
        {"rows": rows, "has_more": has_more, "total": len(scorer_service.top_scorers())},
    )


def scorers_more(request: HttpRequest) -> JsonResponse:
    try:
        offset = int(request.GET.get("offset", "0"))
    except ValueError:
        offset = 0
    rows, has_more = scorer_service.page(offset)
    html = render_to_string("league/_scorer_rows.html", {"rows": rows}, request=request)
    return JsonResponse({"html": html, "has_more": has_more})


def discipline(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "league/discipline.html",
        {"rows": discipline_service.discipline_table(), "per_ban": discipline_service.YELLOWS_PER_BAN},
    )


def teams(request: HttpRequest) -> HttpResponse:
    team_list = Team.objects.select_related("captain").annotate(squad_size=Count("players"))
    return render(request, "league/teams.html", {"teams": team_list})


def team_detail(request: HttpRequest, pk: int) -> HttpResponse:
    team = get_object_or_404(Team, pk=pk)
    squad = team.players.annotate(goals_scored=Count("goals")).order_by("shirt_number")
    team_fixtures = list(fixture_service.for_team(team).order_by("kickoff"))
    results = [(f, fixture_service.result_letter(f, team)) for f in team_fixtures if f.is_played]
    upcoming = [f for f in team_fixtures if f.status == Fixture.Status.SCHEDULED]
    return render(
        request,
        "league/team_detail.html",
        {
            "team": team,
            "squad": squad,
            "row": standings_service.position_of(team),
            "results": results[-5:][::-1],
            "next_fixture": upcoming[0] if upcoming else None,
            "can_manage": permissions.can_manage_squad(request.user, team),
        },
    )


def players(request: HttpRequest) -> HttpResponse:
    player_list = (
        Player.objects.select_related("team").annotate(goals_scored=Count("goals")).order_by("name")
    )
    return render(request, "league/players.html", {"players": player_list})
