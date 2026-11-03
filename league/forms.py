from django import forms
from django.db.models import Q

from .models import Card, Fixture, Player
from .services.results import CardEntry, GoalEntry

MAX_GOALS = 40
MATCH_MINUTES = 60


class ScoreForm(forms.Form):
    home_goals = forms.IntegerField(min_value=0, max_value=MAX_GOALS)
    away_goals = forms.IntegerField(min_value=0, max_value=MAX_GOALS)


class _MatchEventForm(forms.Form):
    player = forms.ModelChoiceField(queryset=Player.objects.none(), empty_label="Choose player")
    minute = forms.IntegerField(min_value=1, max_value=MATCH_MINUTES)

    def __init__(self, *args, fixture: Fixture, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["player"].queryset = (
            Player.objects.select_related("team")
            .filter(Q(team=fixture.home_team) | Q(team=fixture.away_team))
            .order_by("team__name", "shirt_number")
        )
        self.fields["player"].label_from_instance = lambda p: f"{p.name} ({p.team.short_name})"


class GoalRowForm(_MatchEventForm):
    pass


class CardRowForm(_MatchEventForm):
    colour = forms.ChoiceField(choices=Card.Colour.choices)


GoalFormSet = forms.formset_factory(GoalRowForm, extra=0, can_delete=True)
CardFormSet = forms.formset_factory(CardRowForm, extra=0, can_delete=True)


class ResultEntry:
    """The result screen: score, scorers and cards, validated together."""

    def __init__(self, fixture: Fixture, data=None):
        self.fixture = fixture
        initial_score, initial_goals, initial_cards = None, None, None
        if data is None and fixture.is_played:
            initial_score = {"home_goals": fixture.home_goals, "away_goals": fixture.away_goals}
            initial_goals = [{"player": g.player_id, "minute": g.minute} for g in fixture.goals.all()]
            initial_cards = [
                {"player": c.player_id, "colour": c.colour, "minute": c.minute} for c in fixture.cards.all()
            ]
        self.score = ScoreForm(data, initial=initial_score)
        self.goals = GoalFormSet(data, prefix="goals", initial=initial_goals, form_kwargs={"fixture": fixture})
        self.cards = CardFormSet(data, prefix="cards", initial=initial_cards, form_kwargs={"fixture": fixture})
        self.errors: list[str] = []

    @staticmethod
    def _kept(formset) -> list[dict]:
        return [
            form.cleaned_data
            for form in formset.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE")
        ]

    def is_valid(self) -> bool:
        valid = all([self.score.is_valid(), self.goals.is_valid(), self.cards.is_valid()])
        if not valid:
            return False
        home_goals = self.score.cleaned_data["home_goals"]
        away_goals = self.score.cleaned_data["away_goals"]
        # Own goals are not credited to anyone, so there can be fewer scorers
        # than goals, but never more.
        if len(self.goal_entries()) > home_goals + away_goals:
            self.errors.append("There are more scorers than goals in the score.")
        return not self.errors

    def goal_entries(self) -> list[GoalEntry]:
        return [GoalEntry(player=row["player"], minute=row["minute"]) for row in self._kept(self.goals)]

    def card_entries(self) -> list[CardEntry]:
        return [
            CardEntry(player=row["player"], colour=row["colour"], minute=row["minute"])
            for row in self._kept(self.cards)
        ]


class FixtureForm(forms.ModelForm):
    kickoff = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"],
        help_text="Lagos time.",
    )
    status = forms.ChoiceField(
        choices=[(Fixture.Status.SCHEDULED, "Scheduled"), (Fixture.Status.POSTPONED, "Postponed")]
    )

    class Meta:
        model = Fixture
        fields = ["kickoff", "pitch", "status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.is_played:
            del self.fields["status"]


class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ["name", "shirt_number", "position"]

    def __init__(self, *args, team, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team

    def clean_name(self) -> str:
        return " ".join(self.cleaned_data["name"].split())

    def clean_shirt_number(self) -> int:
        number = self.cleaned_data["shirt_number"]
        if Player.objects.filter(team=self.team, shirt_number=number).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(f"Number {number} is already taken in this squad.")
        return number

    def save(self, commit: bool = True) -> Player:
        self.instance.team = self.team
        return super().save(commit=commit)
