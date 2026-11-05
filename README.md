# Leaguetable

Leaguetable runs the **Rowe Park Friday Five-a-side League** in Yaba, Lagos: eight community teams,
a double round robin on Friday nights, and one place where everybody can check the table.

- **Table**: points, goal difference, form, with the league's tie-breakers.
- **Fixtures**: by matchday, grouped by day, with results and goalscorers.
- **Results**: the referee, the secretary, or the captain of either team enters the score, the scorers
  and the cards after each game, and can correct it later.
- **Top scorers** and **Discipline** (cards and suspensions).
- **Teams and players**: captains manage their own squad.

Stack: Python 3.13, Django 5.2 (server-rendered templates, a little vanilla JS), SQLite.
WhiteNoise and Gunicorn in the container.

## Running it

### Docker

```bash
docker compose up --build
```

Open http://localhost:5118. The container migrates and loads the demo season on every start
(so any changes you make are reset on restart).

### Locally

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 5118
```

Settings come from environment variables (see `.env.example`): `LEAGUETABLE_DEBUG`, `LEAGUETABLE_SECRET_KEY`,
`LEAGUETABLE_DB_PATH`, `LEAGUETABLE_ALLOWED_HOSTS`.

## Demo logins

All demo accounts use the password `leaguetable2026`.

| Username | Who | Can do |
| --- | --- | --- |
| `secretary` | Funmilayo Adebayo, league secretary | Everything: enter and correct results, clear a result, reschedule or postpone fixtures, manage any squad |
| `referee` | Sule Ibrahim, referee | Enter and correct results |
| `captain.yaba`, `captain.lekki`, `captain.surulere`, `captain.ikoyi`, `captain.ajah`, `captain.ikeja`, `captain.gbagada`, `captain.festac` | Team captains | Add and remove players in their own squad; enter and correct results for matches involving their team |
| `admin` | Superuser | Django admin at `/admin/` |

Captains can enter and correct results for their own team's matches.
Everything else (table, fixtures, scorers, discipline, teams, players) is public, no login needed.

## Demo season

`python manage.py seed_demo` wipes the league and loads a fresh season relative to today:
14 matchdays, one every Friday, kickoffs at 19:00, 20:00, 21:00 and 22:00 on two pitches.
Matchdays 1 to 6 are already played (the last six Fridays); matchday 7 is the coming Friday.

## League rules the app follows

### How the table is sorted

Win 3 points, draw 1, loss 0. Teams level on points are separated, in this order, by:

1. goal difference,
2. head to head: points in the games between the teams that are still level,
3. goals scored,
4. team name (alphabetical).

So head to head only matters when goal difference is level.

P (played) counts only games that have a result. Postponed games are not counted until they are played.

### Results and goalscorers

- Own goals are not credited to any player and do not appear in Top scorers, so a team can have fewer
  scorers listed than goals. It can never have more: each team's scorers must fit inside that team's score.
- A second yellow card in the same game is entered as a single red card.
- Correcting a result replaces the scorers and cards that were entered before.
- The secretary can **clear** a result that was entered against the wrong fixture. The fixture goes
  back to scheduled.

### Discipline

- A red card is a one-match ban.
- Every third yellow card of the season (3rd, 6th, 9th...) is a one-match ban.
- Yellow cards do **not** reset during the season.
- A ban is served in the team's next scheduled fixture. The Discipline page shows who is suspended now
  (from the team's last game) and who is one yellow away from a ban.

### Times

All times are Lagos time (WAT). Fixtures after midnight belong to the day they are actually played on.

## Project layout

```
config/                 Django settings and root URLs
league/
  models.py             Team, Player, Fixture, Goal, Card
  forms.py              result entry (score + scorer and card formsets), fixture and player forms
  permissions.py        secretary / referee / captain rules
  services/             standings (cached table), results, discipline, scorers, fixtures
  utils/dates.py        Lagos date helpers
  views/                public pages, result entry, fixture and squad management
  signals.py            drops the cached table when fixtures or teams change
  management/commands/seed_demo.py
templates/              base layout and league pages
static/                 site.css and the small scripts (result form rows, scorers "Show more", player search)
```

## Tests

```bash
python manage.py test
```

The suite uses Django's test runner and an in-memory SQLite database.
