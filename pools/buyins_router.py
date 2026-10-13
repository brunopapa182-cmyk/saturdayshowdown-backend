from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from auth.dependencies import get_current_user

from pools.models import Pool, PoolMember, BuyIn

router = APIRouter(tags=["buyins"])


# ---------------------------------------------------------
# Helper: Ensure user is commissioner (owner)
# ---------------------------------------------------------
def ensure_commissioner(db: Session, pool_id: int, user_id: int):
    pool = db.query(Pool).filter(Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    if pool.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Only the pool owner can manage buy-ins")

    return pool


# ---------------------------------------------------------
# GET BUY-INS FOR A POOL (Open to all members)
# ---------------------------------------------------------
@router.get("/{pool_id}/buyins")
def get_buyins(
    pool_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    # Ensure pool exists
    pool = db.query(Pool).filter(Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    # Ensure user is a member
    member = db.query(PoolMember).filter(
        PoolMember.pool_id == pool_id,
        PoolMember.user_id == user.id
    ).first()

    if not member:
        raise HTTPException(status_code=403, detail="User is not a member of this pool")

    # Fetch buy-ins
    buyins = db.query(BuyIn).filter(BuyIn.pool_id == pool_id).all()

    return {
        "pool_id": pool_id,
        "buyins": [
            {
                "id": b.id,
                "user_id": b.user_id,
                "amount": b.amount,
                "timestamp": b.date_paid
            }
            for b in buyins
        ]
    }


# ---------------------------------------------------------
# ADD BUY-IN (Commissioner Only)
# ---------------------------------------------------------
@router.post("/{pool_id}/buyins")
def add_buyin(
    pool_id: int,
    amount: float,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    # ⭐ Commissioner check added
    ensure_commissioner(db, pool_id, user.id)

    # Ensure user is a member (commissioner is always a member)
    member = db.query(PoolMember).filter(
        PoolMember.pool_id == pool_id,
        PoolMember.user_id == user.id
    ).first()

    if not member:
        raise HTTPException(status_code=403, detail="User is not a member of this pool")

    # Create buy-in
    buyin = BuyIn(
        pool_id=pool_id,
        user_id=user.id,
        amount=amount
    )

    db.add(buyin)
    db.commit()
    db.refresh(buyin)

    return {
        "id": buyin.id,
        "pool_id": buyin.pool_id,
        "user_id": buyin.user_id,
        "amount": buyin.amount,
        "timestamp": buyin.date_paid
    }
