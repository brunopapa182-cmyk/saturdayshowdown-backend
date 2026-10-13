from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from database import get_db
from auth.dependencies import get_current_user

from pools.models import (
    PoolMember,
    Pick,
    Game,
    NewsEvent,
    Pool
)

router = APIRouter(tags=["scoring"])


# ---------------------------------------------------------
# ⭐ Helper: Ensure user is commissioner (owner)
# ---------------------------------------------------------
def ensure_commissioner(db: Session, pool_id: int, user_id: int):
    pool = db.query(Pool).filter(Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    if pool.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Only the pool owner can perform scoring actions")

    return pool


# ---------------------------------------------------------
# ⭐ GRADE PICKS + UPDATE LIVES + CREATE NEWS (Commissioner Only)
# ---------------------------------------------------------
@router.post("/{pool_id}/scoring/grade")
def grade_pool_scoring(
    pool_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    # ⭐ Commissioner check added
    ensure_commissioner(db, pool_id, user.id)

    # Validate membership
    member = db.query(PoolMember).filter(
        PoolMember.pool_id == pool_id,
        PoolMember.user_id == user.id
    ).first()

    if not member:
        raise HTTPException(status_code=403, detail="User is not a member of this pool")

    # 1) Get completed games
    completed_games = (
        db.query(Game)
        .filter(Game.pool_id == pool_id)
        .filter(Game.is_completed == True)
        .all()
    )

    if not completed_games:
        raise HTTPException(status_code=400, detail="No completed games to grade")

    # Map game_id -> winner
    winners = {g.id: g.winner for g in completed_games}

    # 2) Get picks for those games
    game_ids = list(winners.keys())
    picks = (
        db.query(Pick)
        .filter(Pick.game_id.in_(game_ids))
        .all()
    )

    if not picks:
        raise HTTPException(status_code=400, detail="No picks found for completed games")

    # Track lives lost
    lives_lost_by_user = {}

    # 3) Grade picks
    for p in picks:
        winner = winners.get(p.game_id)
        if winner is None:
            continue

        selection = p.selection
        is_correct = (selection == winner)
        p.is_correct = is_correct

        if not is_correct:
            lives_lost_by_user[p.user_id] = lives_lost_by_user.get(p.user_id, 0) + 1

    # 4) Apply lives lost + elimination flag
    if lives_lost_by_user:
        members = (
            db.query(PoolMember)
            .filter(PoolMember.pool_id == pool_id)
            .all()
        )
        members_by_user = {str(m.user_id): m for m in members}

        for user_id_str, lost in lives_lost_by_user.items():
            m = members_by_user.get(user_id_str)
            if not m:
                continue

            m.remaining_lives = max(0, m.remaining_lives - lost)

            # ⭐ NEW: mark eliminated when lives reach 0
            if m.remaining_lives <= 0:
                m.is_eliminated = True

    # 5) Create news events
    for g in completed_games:
        if g.home_score is None or g.away_score is None:
            continue

        msg = (
            f"{g.home_team_name} ({g.home_abbrev}) {g.home_score} - "
            f"{g.away_team_name} ({g.away_abbrev}) {g.away_score}"
        )

        news = NewsEvent(
            pool_id=pool_id,
            date=g.game_date.date().isoformat(),
            message=msg
        )
        db.add(news)

    db.commit()

    return {
        "message": "Scoring graded successfully",
        "completed_games": len(completed_games),
        "graded_picks": len(picks),
        "users_lives_changed": len(lives_lost_by_user),
    }


# ---------------------------------------------------------
# ⭐ ORIGINAL ENDPOINT — PRESERVED EXACTLY
# GET USER SCORING FOR A POOL
# ---------------------------------------------------------
@router.get("/{pool_id}/scoring")
def get_pool_scoring(
    pool_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    # Validate membership
    member = db.query(PoolMember).filter(
        PoolMember.pool_id == pool_id,
        PoolMember.user_id == user.id
    ).first()

    if not member:
        raise HTTPException(status_code=403, detail="User is not a member of this pool")

    picks = (
        db.query(Pick)
        .join(Game, Pick.game_id == Game.id)
        .filter(
            Game.pool_id == pool_id,
            Pick.user_id == user.id
        )
        .all()
    )

    correct = sum(1 for p in picks if p.is_correct is True)
    incorrect = sum(1 for p in picks if p.is_correct is False)

    return {
        "pool_id": pool_id,
        "user_id": user.id,
        "correct": correct,
        "incorrect": incorrect,
        "total_picks": len(picks),
    }


# ---------------------------------------------------------
# ⭐ POOL-WIDE STANDINGS (Open to all members)
# ---------------------------------------------------------
@router.get("/{pool_id}/scoring/standings")
def get_pool_standings(
    pool_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    member = db.query(PoolMember).filter(
        PoolMember.pool_id == pool_id,
        PoolMember.user_id == user.id
    ).first()

    if not member:
        raise HTTPException(status_code=403, detail="User is not a member of this pool")

    members = (
        db.query(PoolMember)
        .filter(PoolMember.pool_id == pool_id)
        .all()
    )

    picks = (
        db.query(Pick)
        .join(Game, Pick.game_id == Game.id)
        .filter(Game.pool_id == pool_id)
        .all()
    )

    stats_by_user = {}
    for p in picks:
        uid = p.user_id
        if uid not in stats_by_user:
            stats_by_user[uid] = {"correct": 0, "incorrect": 0}
        if p.is_correct is True:
            stats_by_user[uid]["correct"] += 1
        elif p.is_correct is False:
            stats_by_user[uid]["incorrect"] += 1

    standings = []
    for m in members:
        uid_str = str(m.user_id)
        stats = stats_by_user.get(uid_str, {"correct": 0, "incorrect": 0})
        standings.append({
            "user_id": uid_str,
            "remaining_lives": m.remaining_lives,
            "is_eliminated": m.is_eliminated,
            "correct_picks": stats["correct"],
            "incorrect_picks": stats["incorrect"],
        })

    standings.sort(
        key=lambda x: (
            x["is_eliminated"],
            -x["remaining_lives"],
            -x["correct_picks"],
        )
    )

    return {"standings": standings}


# ---------------------------------------------------------
# ⭐ WEEKLY SUMMARY (Open to all members)
# ---------------------------------------------------------
def _next_saturday(dt: datetime) -> datetime:
    days_ahead = (5 - dt.weekday()) % 7
    return dt + timedelta(days=days_ahead)


@router.get("/{pool_id}/scoring/week-summary")
def get_week_summary(
    pool_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    member = db.query(PoolMember).filter(
        PoolMember.pool_id == pool_id,
        PoolMember.user_id == user.id
    ).first()

    if not member:
        raise HTTPException(status_code=403, detail="User is not a member of this pool")

    now = datetime.utcnow()
    target_saturday = _next_saturday(now).date()

    saturday_games = (
        db.query(Game)
        .filter(Game.pool_id == pool_id)
        .filter(func.date(Game.game_date) == target_saturday)
        .all()
    )

    game_ids = [g.id for g in saturday_games]

    saturday_picks = []
    if game_ids:
        saturday_picks = (
            db.query(Pick)
            .filter(Pick.game_id.in_(game_ids))
            .all()
        )

    correct = sum(1 for p in saturday_picks if p.is_correct is True)
    incorrect = sum(1 for p in saturday_picks if p.is_correct is False)

    news = (
        db.query(NewsEvent)
        .filter(NewsEvent.pool_id == pool_id)
        .filter(NewsEvent.date == target_saturday.isoformat())
        .all()
    )

    news_items = [{"id": n.id, "date": n.date, "message": n.message} for n in news]

    return {
        "pool_id": pool_id,
        "target_saturday": target_saturday.isoformat(),
        "games_count": len(saturday_games),
        "picks_count": len(saturday_picks),
        "correct": correct,
        "incorrect": incorrect,
        "news": news_items,
    }


# ---------------------------------------------------------
# ⭐ WEEKLY RESET (Open to all members — optional to restrict later)
# ---------------------------------------------------------
@router.post("/{pool_id}/scoring/reset-week")
def reset_week_scoring(
    pool_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    member = db.query(PoolMember).filter(
        PoolMember.pool_id == pool_id,
        PoolMember.user_id == user.id
    ).first()

    if not member:
        raise HTTPException(status_code=403, detail="User is not a member of this pool")

    now = datetime.utcnow()
    target_saturday = _next_saturday(now).date()

    saturday_games = (
        db.query(Game)
        .filter(Game.pool_id == pool_id)
        .filter(func.date(Game.game_date) == target_saturday)
        .all()
    )

    game_ids = [g.id for g in saturday_games]

    if game_ids:
        picks = (
            db.query(Pick)
            .filter(Pick.game_id.in_(game_ids))
            .all()
        )
        for p in picks:
            p.is_correct = None

    news = (
        db.query(NewsEvent)
        .filter(NewsEvent.pool_id == pool_id)
        .filter(NewsEvent.date == target_saturday.isoformat())
        .all()
    )
    for n in news:
        db.delete(n)

    db.commit()

    return {
        "message": "Week scoring reset for Saturday",
        "pool_id": pool_id,
        "target_saturday": target_saturday.isoformat(),
        "games_reset": len(saturday_games),
    }
