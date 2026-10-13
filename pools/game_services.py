from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import requests
import pytz
import time  # ⭐ Added for API delay

from pools.models import Game

# ---------------------------------------------------------
# FETCH NHL SCHEDULE FOR A SPECIFIC DATE
# ---------------------------------------------------------
def fetch_nhl_schedule_by_date(date_str: str):
    url = f"https://api-web.nhle.com/v1/schedule/{date_str}"
    resp = requests.get(url, timeout=10)

    # ⭐ Delay to avoid NHL API rate limits
    time.sleep(0.2)

    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()

# ---------------------------------------------------------
# FETCH BOXSCORE FOR COMPLETED GAMES
# ---------------------------------------------------------
def fetch_boxscore(game_id: int):
    url = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore"
    resp = requests.get(url, timeout=10)

    # ⭐ Delay to avoid NHL API rate limits
    time.sleep(0.2)

    if resp.status_code != 200:
        return None
    return resp.json()

# ---------------------------------------------------------
# GENERATE ALL DATES IN THE SEASON
# ---------------------------------------------------------
def generate_season_dates(start: str, end: str):
    start_date = datetime.fromisoformat(start)
    end_date = datetime.fromisoformat(end)

    dates = []
    current = start_date

    while current <= end_date:
        dates.append(current.date().isoformat())
        current += timedelta(days=1)

    return dates

# ---------------------------------------------------------
# INGEST NHL SEASON FOR A POOL (SATURDAY ONLY)
# ---------------------------------------------------------
def ingest_season_for_pool(db: Session, pool_id: int, season: str = "20262027"):

    season_dates = generate_season_dates("2026-10-03", "2027-04-15")
    total_games = 0

    eastern = pytz.timezone("America/New_York")

    for date_str in season_dates:
        date_obj = datetime.fromisoformat(date_str)

        # Only Saturdays
        if date_obj.weekday() != 5:
            continue

        data = fetch_nhl_schedule_by_date(date_str)
        if not data or "gameWeek" not in data:
            continue

        for block in data["gameWeek"]:
            if block.get("date") != date_str:
                continue

            for g in block.get("games", []):

                if "homeTeam" not in g or "awayTeam" not in g:
                    continue

                # IDs
                home_team_id = g["homeTeam"]["id"]
                away_team_id = g["awayTeam"]["id"]

                # Names + abbrevs
                home_team_name = g["homeTeam"].get("name")
                away_team_name = g["awayTeam"].get("name")
                home_abbrev = g["homeTeam"].get("abbrev")
                away_abbrev = g["awayTeam"].get("abbrev")

                # ---------------------------------------------------------
                # CORRECT START TIME FIELD (RESTORED)
                # ---------------------------------------------------------
                start_time_str = (
                    g.get("gameDateTimeUTC")
                    or g.get("startTimeUTC")
                    or g.get("gameDate")
                )

                if start_time_str:
                    try:
                        start_time_utc = datetime.fromisoformat(
                            start_time_str.replace("Z", "+00:00")
                        )
                        start_time_local = start_time_utc.astimezone(eastern)
                    except Exception:
                        start_time_local = datetime.combine(
                            date_obj.date(), datetime.min.time()
                        )
                else:
                    start_time_local = datetime.combine(
                        date_obj.date(), datetime.min.time()
                    )

                # ---------------------------------------------------------
                # ⭐ NEW: Correct final-state detection
                # ---------------------------------------------------------
                game_state = g.get("gameState", "").upper()
                is_final = game_state in ["FINAL", "OFF", "END", "CRIT", "OVER"]

                # ---------------------------------------------------------
                # ⭐ NEW: Fetch real scores for completed games
                # ---------------------------------------------------------
                home_score = 0
                away_score = 0
                winner_team_id = None

                if is_final:
                    box = fetch_boxscore(g["id"])
                    if box:
                        try:
                            home_score = box["homeTeam"]["score"]
                            away_score = box["awayTeam"]["score"]
                            winner_team_id = box.get("winningTeam")
                        except Exception:
                            home_score = 0
                            away_score = 0
                else:
                    home_score = (
                        g["homeTeam"].get("score")
                        or g["homeTeam"].get("goals")
                        or g["homeTeam"].get("sog")
                        or 0
                    )
                    away_score = (
                        g["awayTeam"].get("score")
                        or g["awayTeam"].get("goals")
                        or g["awayTeam"].get("sog")
                        or 0
                    )

                # UPSERT
                existing_game = (
                    db.query(Game)
                    .filter(
                        Game.pool_id == pool_id,
                        Game.home_team == str(home_team_id),
                        Game.away_team == str(away_team_id),
                        func.date(Game.game_date) == start_time_local.date(),
                    )
                    .first()
                )

                if existing_game:
                    existing_game.home_team_name = home_team_name
                    existing_game.away_team_name = away_team_name
                    existing_game.home_abbrev = home_abbrev
                    existing_game.away_abbrev = away_abbrev

                    existing_game.game_date = start_time_local
                    existing_game.game_time = start_time_local.time()

                    existing_game.is_completed = is_final
                    existing_game.winner = (
                        str(winner_team_id) if winner_team_id is not None else None
                    )
                    existing_game.home_score = home_score
                    existing_game.away_score = away_score

                else:
                    game = Game(
                        pool_id=pool_id,
                        home_team=str(home_team_id),
                        away_team=str(away_team_id),

                        home_team_name=home_team_name,
                        away_team_name=away_team_name,
                        home_abbrev=home_abbrev,
                        away_abbrev=away_abbrev,

                        game_date=start_time_local,
                        game_time=start_time_local.time(),
                        is_completed=is_final,
                        winner=str(winner_team_id) if winner_team_id is not None else None,
                        home_score=home_score,
                        away_score=away_score,
                    )
                    db.add(game)

                total_games += 1

    db.commit()
    return {"total_games": total_games}

# ---------------------------------------------------------
# GET GAMES GROUPED BY DATE
# ---------------------------------------------------------
def get_games_by_date_for_pool(db: Session, pool_id: int):
    games = db.query(Game).filter(Game.pool_id == pool_id).all()

    grouped = {}

    for g in games:
        date_key = g.game_date.date().isoformat()

        start_time_str = (
            g.game_time.strftime("%I:%M %p") + " EST" if g.game_time else "TBD"
        )

        grouped.setdefault(date_key, []).append({
            "id": g.id,
            "home_team_id": int(g.home_team),
            "away_team_id": int(g.away_team),

            "home_team_name": g.home_team_name,
            "away_team_name": g.away_team_name,
            "home_abbrev": g.home_abbrev,
            "away_abbrev": g.away_abbrev,

            "start_time": start_time_str,
            "is_completed": g.is_completed,
            "winner": str(g.winner) if g.winner is not None else None,
            "home_score": g.home_score,
            "away_score": g.away_score,
        })

    return grouped

# ---------------------------------------------------------
# GET SATURDAY DATES
# ---------------------------------------------------------
def get_saturday_dates_for_pool(db: Session, pool_id: int):
    games = db.query(Game).filter(Game.pool_id == pool_id).all()
    saturdays = set()

    for g in games:
        if g.game_date.weekday() == 5:
            saturdays.add(g.game_date.date().isoformat())

    return sorted(list(saturdays))

# ---------------------------------------------------------
# GET SATURDAY MATCHUPS
# ---------------------------------------------------------
def get_saturday_games_for_pool(db: Session, pool_id: int):
    saturdays = get_saturday_dates_for_pool(db, pool_id)
    if not saturdays:
        return []

    target_date = saturdays[0]
    target_date_obj = datetime.fromisoformat(target_date).date()

    games = (
        db.query(Game)
        .filter(Game.pool_id == pool_id)
        .filter(func.date(Game.game_date) == target_date_obj)
        .all()
    )

    result = []
    for g in games:
        start_time_str = (
            g.game_time.strftime("%I:%M %p") + " EST" if g.game_time else "TBD"
        )

        result.append({
            "id": g.id,
            "home_team_id": int(g.home_team),
            "away_team_id": int(g.away_team),

            "home_team_name": g.home_team_name,
            "away_team_name": g.away_team_name,
            "home_abbrev": g.home_abbrev,
            "away_abbrev": g.away_abbrev,

            "start_time": start_time_str,
            "is_completed": g.is_completed,
            "winner": str(g.winner) if g.winner is not None else None,
            "home_score": g.home_score,
            "away_score": g.away_score,
        })

    return result

# ---------------------------------------------------------
# UPDATE GAME RESULT
# ---------------------------------------------------------
def update_game_result(db: Session, pool_id: int, game_id: int, is_completed: bool, winner: str | None):
    game = db.query(Game).filter(
        Game.id == game_id,
        Game.pool_id == pool_id
    ).first()

    if not game:
        return False

    game.is_completed = is_completed
    game.winner = winner if is_completed else None

    db.commit()
    return True
