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

    # Query user's picks joined with games
    rows = (
        db.query(Pick, Game)
        .join(Game, Game.id == Pick.game_id)
        .filter(Game.pool_id == pool_id)
        .filter(Pick.user_id == str(user.id))
        .all()
    )

    result = []

    for pick, game in rows:
        # Convert game_date → "YYYY-MM-DD"
        date_key = game.game_date.date().isoformat()

        result.append({
            "team_id": int(pick.user_id),               # user/team who made the pick
            "matchup_id": int(pick.game_id),           # game ID
            "selected_team_id": int(pick.selection),   # team they picked
            "date": date_key                           # Saturday date key
        })

    return result


# ---------------------------------------------------------
# ⭐ POST PICK (Flutter uses this)
# ---------------------------------------------------------
@router.post("/{pool_id}/picks")
def save_pick_for_pool(
    pool_id: int,
    payload: dict = Body(..., media_type="application/json"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    matchup_id = payload.get("matchup_id")
    selected_team_id = payload.get("selected_team_id")

    if matchup_id is None or selected_team_id is None:
        raise HTTPException(status_code=400, detail="matchup_id and selected_team_id required")

    # Ensure user is in the pool
    member = db.query(PoolMember).filter(
        PoolMember.pool_id == pool_id,
        PoolMember.user_id == user.id
    ).first()

    if not member:
        raise HTTPException(status_code=403, detail="User is not a member of this pool")

    if member.is_eliminated:
        raise HTTPException(status_code=403, detail="You are eliminated and cannot make picks")

    # Validate game
    game = db.query(Game).filter(
        Game.id == matchup_id,
        Game.pool_id == pool_id
    ).first()

    if not game:
        raise HTTPException(status_code=404, detail="Game not found for this pool")

    # Time lock
    now = datetime.now().astimezone()
    game_time = game.game_date.astimezone()

    if game_time is not None and now >= game_time:
        raise HTTPException(status_code=400, detail="Picks are locked for this game")

    # Saturday validation
    target_saturday = _next_saturday(now).date()
    game_date = game_time.date()

    if game_date != target_saturday:
        raise HTTPException(status_code=400, detail="Picks are only allowed for Saturday games")

    # Lives check
    saturday_game_ids = [
        g.id
        for g in db.query(Game)
        .filter(Game.pool_id == pool_id)
        .filter(func.date(Game.game_date) == target_saturday)
        .all()
    ]

    if saturday_game_ids:
        user_saturday_picks_count = db.query(Pick).filter(
            Pick.user_id == str(user.id),
            Pick.game_id.in_(saturday_game_ids)
        ).count()
    else:
        user_saturday_picks_count = 0

    if member.remaining_lives is not None and user_saturday_picks_count >= member.remaining_lives:
        raise HTTPException(
            status_code=400,
            detail=f"You have used all your lives for this Saturday ({member.remaining_lives})",
        )

    # Update existing pick
    existing = db.query(Pick).filter(
        Pick.user_id == str(user.id),
        Pick.game_id == matchup_id
    ).first()

    if existing:
        existing.selection = str(selected_team_id)
        db.commit()
        return {"status": "updated", "pick_id": existing.id}

    # Create new pick
    pick_id = str(uuid.uuid4())

    new_pick = Pick(
        id=pick_id,
        user_id=str(user.id),
        game_id=matchup_id,
        selection=str(selected_team_id),
        is_correct=None,
    )

    db.add(new_pick)
    db.commit()

    return {"status": "created", "pick_id": pick_id}
