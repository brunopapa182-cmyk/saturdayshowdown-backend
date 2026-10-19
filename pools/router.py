from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from pools.models import Pool, PoolMember, PoolSettings
from auth.dependencies import get_current_user

from schemas import PoolCreate, PoolRead

# Sub‑routers
from pools.settings_router import router as settings_router
from pools.members_router import router as members_router
from pools.buyins_router import router as buyins_router
from pools.news_router import router as news_router
from pools.scoring_router import router as scoring_router
from pools.games_router import router as games_router
from pools.picks_router import router as picks_router

router = APIRouter(tags=["pools"])


# ---------------------------------------------------------
# CREATE POOL (commissioner = owner_id)
# ---------------------------------------------------------
@router.post("/pools/", response_model=PoolRead)
def create_pool(
    pool_data: PoolCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # 1️⃣ Create pool WITHOUT starting_lives on Pool itself
    pool = Pool(
        name=pool_data.name,
        owner_id=user.id,
        pool_type=pool_data.pool_type,
        picks_per_week=pool_data.picks_per_week,
        total_games_per_week=pool_data.total_games_per_week,
    )
    db.add(pool)
    db.commit()
    db.refresh(pool)

    # 2️⃣ Create PoolSettings as the source of truth
    settings = PoolSettings(
        pool_id=pool.id,
        starting_lives=pool_data.starting_lives,
        picks_per_week=pool_data.picks_per_week,
        total_games_per_week=pool_data.total_games_per_week,
    )
    db.add(settings)

    # 3️⃣ Add commissioner as a member with correct lives
    commissioner_member = PoolMember(
        pool_id=pool.id,
        user_id=user.id,
        remaining_lives=pool_data.starting_lives,
    )
    db.add(commissioner_member)

    db.commit()
    db.refresh(pool)

    return pool


# ---------------------------------------------------------
# LIST POOLS (return pools user is a member of)
# ---------------------------------------------------------
@router.get("/pools/", response_model=list[PoolRead])
def list_pools(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return (
        db.query(Pool)
        .join(Pool.members)
        .filter(PoolMember.user_id == user.id)
        .all()
    )


# ---------------------------------------------------------
# GET SINGLE POOL
# ---------------------------------------------------------
@router.get("/pools/{pool_id}", response_model=PoolRead)
def get_pool(
    pool_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    pool = (
        db.query(Pool)
        .filter(Pool.id == pool_id)
        .first()
    )

    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    # Ensure user is a member
    member = (
        db.query(PoolMember)
        .filter(
            PoolMember.pool_id == pool_id,
            PoolMember.user_id == user.id,
        )
        .first()
    )

    if not member:
        raise HTTPException(status_code=403, detail="User is not a member of this pool")

    return pool


# ---------------------------------------------------------
# INCLUDE SUB‑ROUTERS
# ---------------------------------------------------------
router.include_router(settings_router, prefix="/pools")
router.include_router(members_router, prefix="/pools")
router.include_router(buyins_router, prefix="/pools")
router.include_router(news_router, prefix="/pools")
router.include_router(scoring_router, prefix="/pools")
router.include_router(games_router, prefix="/pools")
router.include_router(picks_router, prefix="/pools")
