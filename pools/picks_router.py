from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import uuid

from database import get_db
from pools.models import Pick, Game, PoolMember
from auth.dependencies import get_current_user

router = APIRouter(prefix="/pools", tags=["picks"])


# ---------------------------------------------------------
# Helper: Find next Saturday
# ---------------------------------------------------------
def _next_saturday(dt: datetime) -> datetime:
    days_ahead = (5 - dt.weekday()) % 7  # Saturday = 5
    return dt + timedelta(days=days_ahead)


# ---------------------------------------------------------
# ⭐ GET PICKS (Flutter uses this)
# ---------------------------------------------------------
@router.get("/{pool_id}/picks")
def get_user_picks_for_pool(
    pool_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # Ensure user is in the pool
    member = db.query(PoolMember).filter(
        PoolMember.pool_id == pool_id,
        PoolMember.user_id == user.id
    ).first()

    if not member:
        raise HTTPException(status_code=403, detail="User is not a member of this pool")

    rows = (
        db.query(Pick, Game)
        .join(Game, Game.id == Pick.game_id)
        .filter(Game.pool_id == pool_id)
        .filter(Pick.user_id == str(user.id))
        .all()
    )

    result = []

    for pick, game in rows:
        date_key = game.game_date.date().isoformat()

        result.append({
            "team_id": int(user.id),
            "matchup_id": int(pick.game_id),
            "selected_team_id": int(pick.selection),
            "date": date_key
        })

    return result


# ---------------------------------------------------------
# ⭐ POST PICKS (Batch submission)
# ---------------------------------------------------------
@router.post("/{pool_id}/picks")
def save_picks_for_pool(
    pool_id: int,
    payload: dict = Body(..., media_type="application/json"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    picks = payload.get("picks")

    if not picks or not isinstance(picks, list):
        raise HTTPException(status_code=400, detail="picks must be a list")

    # Ensure user is in the pool
    member = db.query(PoolMember).filter(
        PoolMember.pool_id == pool_id,
        PoolMember.user_id == user.id
    ).first()

    if not member:
        raise HTTPException(status_code=403, detail="User is not a member of this pool")

    if member.is_eliminated:
        raise HTTPException(status_code=403, detail="You are eliminated and cannot make picks")

    now = datetime.now().astimezone()
    target_saturday = _next_saturday(now).date()

    # Get all Saturday games for validation
    saturday_games = db.query(Game).filter(
        Game.pool_id == pool_id,
        func.date(Game.game_date) == target_saturday
    ).all()

    saturday_game_ids = [g.id for g in saturday_games]

    # Lives check
    existing_count = db.query(Pick).filter(
        Pick.user_id == str(user.id),
        Pick.game_id.in_(saturday_game_ids)
    ).count()

    if member.remaining_lives is not None:
        if len(picks) > member.remaining_lives:
            raise HTTPException(
                status_code=400,
                detail=f"You can only make {member.remaining_lives} picks this Saturday",
            )

    # Clear existing Saturday picks
    db.query(Pick).filter(
        Pick.user_id == str(user.id),
        Pick.game_id.in_(saturday_game_ids)
    ).delete()

    # Insert new picks
    for p in picks:
        matchup_id = p.get("matchup_id")
        selected_team_id = p.get("selected_team_id")

        if matchup_id is None or selected_team_id is None:
            raise HTTPException(status_code=400, detail="Each pick requires matchup_id and selected_team_id")

        game = db.query(Game).filter(
            Game.id == matchup_id,
            Game.pool_id == pool_id
        ).first()

        if not game:
            raise HTTPException(status_code=404, detail=f"Game {matchup_id} not found")

        game_time = game.game_date.astimezone()

        if now >= game_time:
            raise HTTPException(status_code=400, detail=f"Game {matchup_id} is locked")

        if game_time.date() != target_saturday:
            raise HTTPException(status_code=400, detail="Picks are only allowed for Saturday games")

        new_pick = Pick(
            id=str(uuid.uuid4()),
            user_id=str(user.id),
            game_id=matchup_id,
            selection=str(selected_team_id),
            is_correct=None,
        )

        db.add(new_pick)

    db.commit()

    return {"status": "success", "count": len(picks)}
