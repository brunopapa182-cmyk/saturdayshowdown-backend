from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from auth.dependencies import get_current_user
from teams.models import Team
from teams.schemas import FantasyTeamCreate, FantasyTeamRead

router = APIRouter(
    prefix="/fantasy-teams",
    tags=["Fantasy Teams"]
)

# ---------------------------------------------------------
# LIST FANTASY TEAMS (NEW ENDPOINT)
# ---------------------------------------------------------
@router.get("/", summary="List fantasy teams", response_model=list[FantasyTeamRead])
def list_fantasy_teams(
    user_id: int | None = None,
    pool_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Allows filtering by:
    - user_id
    - pool_id
    """

    query = db.query(Team)

    if user_id is not None:
        query = query.filter(Team.user_id == user_id)

    if pool_id is not None:
        query = query.filter(Team.pool_id == pool_id)

    teams = query.all()

    return teams


# ---------------------------------------------------------
# CREATE FANTASY TEAM
# ---------------------------------------------------------
@router.post("/", response_model=FantasyTeamRead, summary="Create a fantasy team")
def create_team(
    team: FantasyTeamCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if team.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot create team for another user")

    db_team = Team(
        name=team.name,
        pool_id=team.pool_id,
        user_id=team.user_id
    )

    db.add(db_team)
    db.commit()
    db.refresh(db_team)

    return db_team


# ---------------------------------------------------------
# GET TEAM BY ID
# ---------------------------------------------------------
@router.get("/{team_id}", response_model=FantasyTeamRead, summary="Get a fantasy team by ID")
def get_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    team = db.query(Team).filter(Team.id == team_id).first()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if team.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to view this team")

    return team


# ---------------------------------------------------------
# DELETE TEAM BY ID
# ---------------------------------------------------------
@router.delete("/{team_id}", summary="Delete a fantasy team")
def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    team = db.query(Team).filter(Team.id == team_id).first()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if team.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to delete this team")

    db.delete(team)
    db.commit()

    return {"detail": "Deleted"}
