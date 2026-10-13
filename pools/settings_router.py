from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from pools.models import Pool, PoolSettings
from auth.dependencies import get_current_user

router = APIRouter(tags=["settings"])


# ---------------------------------------------------------
# Helper: Ensure user is commissioner (owner) of the pool
# ---------------------------------------------------------
def ensure_commissioner(db: Session, pool_id: int, user_id: int):
    pool = db.query(Pool).filter(Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    if pool.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Only the pool owner can modify settings")

    return pool


# ---------------------------------------------------------
# GET ADMIN SETTINGS (Owner Only)
# ---------------------------------------------------------
@router.get("/{pool_id}/settings")
def get_settings(
    pool_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    # ⭐ Add commissioner check here
    ensure_commissioner(db, pool_id, user.id)

    pool = db.query(Pool).filter(Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    return {
        "pool_id": pool_id,
        "pool_type": pool.pool_type,
        "starting_lives": pool.starting_lives,
        "picks_per_week": pool.picks_per_week,
        "total_games_per_week": pool.total_games_per_week,
    }


# ---------------------------------------------------------
# UPDATE ADMIN SETTINGS (Owner Only)
# ---------------------------------------------------------
@router.post("/{pool_id}/settings")
def update_settings(
    pool_id: int,
    pool_type: str,
    starting_lives: int,
    picks_per_week: int,
    total_games_per_week: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    pool = ensure_commissioner(db, pool_id, user.id)

    pool.pool_type = pool_type
    pool.starting_lives = starting_lives
    pool.picks_per_week = picks_per_week
    pool.total_games_per_week = total_games_per_week

    db.commit()
    db.refresh(pool)

    return {
        "message": "Settings updated",
        "pool_id": pool_id,
        "pool_type": pool.pool_type,
        "starting_lives": pool.starting_lives,
        "picks_per_week": pool.picks_per_week,
        "total_games_per_week": pool.total_games_per_week,
    }
