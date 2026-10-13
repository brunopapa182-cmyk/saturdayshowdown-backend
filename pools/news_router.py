from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from pools.models import NewsEvent, PoolMember, Pool
from auth.dependencies import get_current_user

# ⭐ No prefix here — prefix is applied in pools/router.py
router = APIRouter(tags=["news"])


# ---------------------------------------------------------
# Helper: Ensure user is a member of the pool
# ---------------------------------------------------------
def ensure_pool_member(db: Session, pool_id: int, user_id: int):
    member = db.query(PoolMember).filter(
        PoolMember.pool_id == pool_id,
        PoolMember.user_id == user_id
    ).first()

    if not member:
        raise HTTPException(status_code=403, detail="User is not a member of this pool")

    return member


# ---------------------------------------------------------
# Helper: Ensure user is commissioner (owner)
# ---------------------------------------------------------
def ensure_commissioner(db: Session, pool_id: int, user_id: int):
    pool = db.query(Pool).filter(Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    if pool.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Only the pool owner can manage news")

    return pool


# ---------------------------------------------------------
# GET NEWS EVENTS FOR A POOL (Open to all members)
# ---------------------------------------------------------
@router.get("/{pool_id}/news")
def get_news_events(
    pool_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    # Ensure requester is a member of the pool
    ensure_pool_member(db, pool_id, user.id)

    # Fetch all news events for the pool
    events = db.query(NewsEvent).filter(
        NewsEvent.pool_id == pool_id
    ).order_by(NewsEvent.id.desc()).all()

    # Convert to Flutter format
    formatted = [
        {
            "date": event.date,
            "message": event.message
        }
        for event in events
    ]

    return {
        "pool_id": pool_id,
        "news_events": formatted
    }
