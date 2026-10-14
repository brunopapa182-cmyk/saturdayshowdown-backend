from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from pools.models import Pool, PoolSettings, PoolMember
from auth.dependencies import get_current_user

router = APIRouter(tags=["settings"])


# ---------------------------------------------------------
# Helper: Ensure user is commissioner (owner)
# ---------------------------------------------------------
def ensure_commissioner(db: Session, pool_id: int, user_id: int):
    pool = db.query(Pool).filter(Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    if pool.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Only the pool owner can modify settings")

    return pool


# ---------------------------------------------------------
# Pydantic model for settings update
# ---------------------------------------------------------
class SettingsUpdate(BaseModel):
    starting_lives: int
    picks_per_week: int
    total_games_per_week: int


# ---------------------------------------------------------
# GET ADMIN SETTINGS (Owner Only)
# ---------------------------------------------------------
@router.get("/{pool_id}/settings")
def get_settings(
    pool_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    ensure_commissioner(db, pool_id, user.id)

    pool = db.query(Pool).filter(Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    # Pull from PoolSettings if it exists
    settings = db.query(PoolSettings).filter(PoolSettings.pool_id == pool_id).first()

    return {
        "pool_id": pool_id,
        "pool_type": pool.pool_type,  # still readable, but no longer updated here
        "starting_lives": settings.starting_lives if settings else pool.starting_lives,
        "picks_per_week": settings.picks_per_week if settings else pool.picks_per_week,
        "total_games_per_week": settings.total_games_per_week if settings else pool.total_games_per_week,
    }


# ---------------------------------------------------------
# UPDATE ADMIN SETTINGS (Owner Only)
# ---------------------------------------------------------
@router.post("/{pool_id}/settings")
def update_settings(
    pool_id: int,
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    pool = ensure_commissioner(db, pool_id, user.id)

    # Update Pool table (legacy fields) — pool_type no longer touched
    pool.starting_lives = payload.starting_lives
    pool.picks_per_week = payload.picks_per_week
    pool.total_games_per_week = payload.total_games_per_week

    # Update PoolSettings table (primary settings)
    settings = db.query(PoolSettings).filter(PoolSettings.pool_id == pool_id).first()

    if not settings:
        settings = PoolSettings(
            pool_id=pool_id,
            starting_lives=payload.starting_lives,
            picks_per_week=payload.picks_per_week,
            total_games_per_week=payload.total_games_per_week,
            updated_at=datetime.utcnow()
        )
        db.add(settings)
    else:
        settings.starting_lives = payload.starting_lives
        settings.picks_per_week = payload.picks_per_week
        settings.total_games_per_week = payload.total_games_per_week
        settings.updated_at = datetime.utcnow()

    # ⭐ Sync all members' lives to new starting_lives
    members = db.query(PoolMember).filter(PoolMember.pool_id == pool_id).all()
    for m in members:
        m.remaining_lives = payload.starting_lives + m.buyin_adjustment

    db.commit()
    db.refresh(pool)
    db.refresh(settings)

    return {
        "message": "Settings updated",
        "pool_id": pool_id,
        "pool_type": pool.pool_type,  # unchanged, still returned
        "starting_lives": settings.starting_lives,
        "picks_per_week": settings.picks_per_week,
        "total_games_per_week": settings.total_games_per_week,
    }


# ---------------------------------------------------------
# ⭐ NEW: Update a member's lives (commissioner or user)
# ---------------------------------------------------------
class LivesUpdate(BaseModel):
    remaining_lives: int


@router.post("/{pool_id}/members/{user_id}/lives")
def update_member_lives(
    pool_id: int,
    user_id: int,
    payload: LivesUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    # Only commissioner can modify other users
    if user.id != user_id:
        ensure_commissioner(db, pool_id, user.id)

    member = db.query(PoolMember).filter(
        PoolMember.pool_id == pool_id,
        PoolMember.user_id == user_id
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="Pool member not found")

    member.remaining_lives = payload.remaining_lives

    db.commit()
    db.refresh(member)

    return {
        "message": "Member lives updated",
        "user_id": user_id,
        "remaining_lives": member.remaining_lives
    }
