from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from pools.models import Pool

router = APIRouter(
    prefix="/scoring",
    tags=["scoring"]
)

@router.get("/{pool_id}/summary")
def scoring_summary(pool_id: int, db: Session = Depends(get_db)):
    pool = db.query(Pool).filter(Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    return {"pool_id": pool_id, "message": "Scoring summary placeholder"}
