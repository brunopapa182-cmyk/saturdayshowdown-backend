from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from auth.dependencies import get_current_user
from pools.models import Pool

from pools.game_services import (
    ingest_season_for_pool,
    get_games_by_date_for_pool,
    get_saturday_dates_for_pool,
    get_saturday_games_for_pool,
    update_game_result,
)

from .game_schemas import (
    GamesByDateResponse,
    SaturdayDatesResponse,
    GameUpdateRequest,
    IngestResponse,
)

router = APIRouter(tags=["games"])


# ---------------------------------------------------------
# Helper: Ensure user is commissioner (owner)
# ---------------------------------------------------------
def ensure_commissioner(db: Session, pool_id: int, user_id: int):
    pool = db.query(Pool).filter(Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    if pool.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Only the pool owner can perform this action")

    return pool


# ---------------------------------------------------------
# INGEST GAMES (Commissioner Only)
# ---------------------------------------------------------
@router.post("/{pool_id}/games/ingest/", response_model=IngestResponse)
def ingest_games(pool_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ensure_commissioner(db, pool_id, user.id)

    result = ingest_season_for_pool(db, pool_id)
    return {"message": f"Schedule ingested for pool {pool_id}", "total_games": result["total_games"]}


# ---------------------------------------------------------
# GET ALL GAMES (Open to all members)
# ---------------------------------------------------------
@router.get("/{pool_id}/games/", response_model=GamesByDateResponse)
def get_games(pool_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return {"gamesByDate": get_games_by_date_for_pool(db, pool_id)}


# ---------------------------------------------------------
# GET SATURDAY DATES (Open to all members)
# ---------------------------------------------------------
@router.get("/{pool_id}/games/saturdays/", response_model=SaturdayDatesResponse)
def get_saturdays(pool_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return {"saturdays": get_saturday_dates_for_pool(db, pool_id)}


# ---------------------------------------------------------
# GET SATURDAY GAMES (Open to all members)
# ---------------------------------------------------------
@router.get("/{pool_id}/games/saturday-games/")
def get_saturday_games(pool_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return {"games": get_saturday_games_for_pool(db, pool_id)}


# ---------------------------------------------------------
# UPDATE GAME RESULT (Commissioner Only)
# ---------------------------------------------------------
@router.post("/{pool_id}/games/update_result/", response_model=None)
def update_result(pool_id: int, payload: GameUpdateRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ensure_commissioner(db, pool_id, user.id)

    updated = update_game_result(db, pool_id, payload.game_id, payload.is_completed, payload.winner)
    if not updated:
        raise HTTPException(status_code=404, detail="Game not found")

    return {"message": "Game updated successfully"}
