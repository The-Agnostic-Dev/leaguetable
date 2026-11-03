from django.contrib import admin

from .models import Card, Fixture, Goal, Player, Team


class PlayerInline(admin.TabularInline):
    model = Player
    extra = 0


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name", "captain")
    inlines = [PlayerInline]


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("name", "team", "shirt_number", "position", "yellow_cards")
    list_filter = ("team", "position")
    search_fields = ("name",)


class GoalInline(admin.TabularInline):
    model = Goal
    extra = 0


class CardInline(admin.TabularInline):
    model = Card
    extra = 0


@admin.register(Fixture)
class FixtureAdmin(admin.ModelAdmin):
    list_display = ("matchday", "home_team", "away_team", "kickoff", "status", "home_goals", "away_goals")
    list_filter = ("matchday", "status")
    inlines = [GoalInline, CardInline]
