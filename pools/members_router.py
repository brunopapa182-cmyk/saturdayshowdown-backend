from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from pools.models import Pool, PoolMember
from teams.models import Team
from auth.dependencies import get_current_user

router = APIRouter(tags=["pool_members"])


# ---------------------------------------------------------
# Helper: Ensure user is commissioner (owner)
# ---------------------------------------------------------
def ensure_commissioner(db: Session, pool_id: int, user_id: int):
    pool = db.query(Pool).filter(Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    if pool.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Only the pool owner can manage members")

    return pool


# ---------------------------------------------------------
# JOIN POOL (Open to all users)
# ---------------------------------------------------------
@router.post("/{pool_id}/join")
def join_pool(
    pool_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    pool = db.query(Pool).filter(Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    existing = db.query(PoolMember).filter(
        PoolMember.pool_id == pool_id,
        PoolMember.user_id == user.id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="User already joined this pool")

    member = PoolMember(pool_id=pool_id, user_id=user.id)
    db.add(member)
    db.commit()
    db.refresh(member)

    return {"message": "Joined pool successfully", "member_id": member.id}


# ---------------------------------------------------------
# LIST MEMBERS (Open to all members)
# ---------------------------------------------------------
@router.get("/{pool_id}/members")
def list_members(
    pool_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    # Ensure user is a member
    member = db.query(PoolMember).filter(
        PoolMember.pool_id == pool_id,
        PoolMember.user_id == user.id
    ).first()

    if not member:
        raise HTTPException(status_code=403, detail="User is not a member of this pool")

    rows = (
        db.query(PoolMember, Team)
        .join(Team, Team.user_id == PoolMember.user_id)
        .filter(PoolMember.pool_id == pool_id)
        .filter(Team.pool_id == pool_id)   # ⭐ FIX: Only show teams from THIS pool
        .all()
    )

    result = []
    for member, team in rows:
        result.append({
            "user_id": member.user_id,
            "fantasy_team_name": team.name,
            "remaining_lives": member.remaining_lives
        })

    return result
