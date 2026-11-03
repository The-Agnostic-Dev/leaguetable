from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=60, unique=True)
    short_name = models.CharField(max_length=4, unique=True)
    colours = models.CharField(max_length=40, blank=True)
    captain = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="captain_of",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Player(models.Model):
    class Position(models.TextChoices):
        GOALKEEPER = "GK", "Goalkeeper"
        DEFENDER = "DF", "Defender"
        MIDFIELDER = "MF", "Midfielder"
        FORWARD = "FW", "Forward"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="players")
    name = models.CharField(max_length=80)
    shirt_number = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(99)])
    position = models.CharField(max_length=2, choices=Position.choices, default=Position.MIDFIELDER)
    # Season tally, kept up to date as results are entered (see services.discipline).
    yellow_cards = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["team__name", "shirt_number"]
        constraints = [
            models.UniqueConstraint(fields=["team", "shirt_number"], name="unique_shirt_per_team"),
        ]

    def __str__(self) -> str:
        return self.name


class Fixture(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        PLAYED = "played", "Played"
        POSTPONED = "postponed", "Postponed"

    matchday = models.PositiveSmallIntegerField()
    home_team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="home_fixtures")
    away_team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="away_fixtures")
    kickoff = models.DateTimeField()
    pitch = models.CharField(max_length=60, default="Pitch 1")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SCHEDULED)
    home_goals = models.PositiveSmallIntegerField(null=True, blank=True)
    away_goals = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["kickoff", "pk"]

    def __str__(self) -> str:
        return f"{self.home_team} v {self.away_team}"

    @property
    def is_played(self) -> bool:
        return self.status == self.Status.PLAYED

    @property
    def score(self) -> str:
        if not self.is_played:
            return ""
        return f"{self.home_goals} - {self.away_goals}"

    def involves(self, team: Team) -> bool:
        return team.pk in (self.home_team_id, self.away_team_id)


class Goal(models.Model):
    fixture = models.ForeignKey(Fixture, on_delete=models.CASCADE, related_name="goals")
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="goals")
    minute = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(60)])

    class Meta:
        ordering = ["minute", "pk"]


class Card(models.Model):
    class Colour(models.TextChoices):
        YELLOW = "Y", "Yellow"
        RED = "R", "Red"

    fixture = models.ForeignKey(Fixture, on_delete=models.CASCADE, related_name="cards")
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="cards")
    colour = models.CharField(max_length=1, choices=Colour.choices)
    minute = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(60)])

    class Meta:
        ordering = ["minute", "pk"]
