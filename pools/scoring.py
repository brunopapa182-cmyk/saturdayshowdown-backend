from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from datetime import datetime

from database import get_db
from pools.pool_model import Pool
from pools.models import PoolMember, Pick, Game
from auth.dependencies import get_current_user

router = APIRouter(
    prefix="/pools",
    tags=["scoring"]
)

@router.post("/{pool_id}/score_week")
def score_week(
    pool_id: int,
    week_number: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    # Ensure pool exists
    pool = db.query(Pool).filter(Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    # Fetch all games for this pool + week
    games = db.query(Game).filter(
        Game.pool_id == pool_id
    ).all()

    if not games:
        raise HTTPException(status_code=400, detail="No games found for this pool")

    # Ensure all games are completed
    incomplete = [g for g in games if not g.is_completed]
    if incomplete:
        raise HTTPException(status_code=400, detail="Not all games are completed")

    # Map game_id -> winner
    winners = {g.id: g.winner for g in games}

    # Score each pool member
    members = db.query(PoolMember).filter(
        PoolMember.pool_id == pool_id
    ).all()

    for member in members:
        # Fetch picks for this user
        user_picks = db.query(Pick).filter(
            Pick.user_id == member.user_id
        ).all()

        correct = 0

        for p in user_picks:
            game_winner = winners.get(p.game_id)

            if game_winner is None:
                continue

            # Mark correctness
            p.is_correct = (p.selection == game_winner)

            if p.is_correct:
                correct += 1

        # Survivor logic: lives = correct picks
        member.remaining_lives = correct

    db.commit()

    return {
        "message": "Week scored",
        "pool_id": pool_id,
        "week_number": week_number
    }
