from django.urls import path

from .views import manage, public, results

urlpatterns = [
    path("", public.standings, name="standings"),
    path("fixtures/", public.fixtures, name="fixtures"),
    path("fixtures/<int:pk>/", public.fixture_detail, name="fixture_detail"),
    path("fixtures/<int:pk>/edit/", manage.edit_fixture, name="edit_fixture"),
    path("fixtures/<int:pk>/result/", results.enter_result, name="enter_result"),
    path("fixtures/<int:pk>/result/clear/", results.clear_result, name="clear_result"),
    path("scorers/", public.scorers, name="scorers"),
    path("scorers/more/", public.scorers_more, name="scorers_more"),
    path("discipline/", public.discipline, name="discipline"),
    path("teams/", public.teams, name="teams"),
    path("teams/<int:pk>/", public.team_detail, name="team_detail"),
    path("teams/<int:pk>/players/new/", manage.add_player, name="add_player"),
    path("players/", public.players, name="players"),
    path("players/<int:pk>/remove/", manage.remove_player, name="remove_player"),
]
