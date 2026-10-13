from pydantic import BaseModel
from typing import Optional


# ---------------------------------------------------------
# PICK SCHEMAS (your existing logic, unchanged)
# ---------------------------------------------------------
class PickBase(BaseModel):
    userId: str
    gameId: Optional[str] = None
    selection: Optional[str] = None
    isCorrect: Optional[bool] = None


class PickCreate(PickBase):
    pass


class PickRead(PickBase):
    id: str


# ---------------------------------------------------------
# FANTASY TEAM SCHEMAS (new)
# ---------------------------------------------------------
class FantasyTeamCreate(BaseModel):
    name: str
    pool_id: int
    user_id: int


class FantasyTeamRead(BaseModel):
    id: int
    name: str
    pool_id: int
    user_id: int

    class Config:
        from_attributes = True

# ---------------------------------------------------------
# POOL SCHEMAS (new)
# ---------------------------------------------------------
class PoolCreate(BaseModel):
    name: str
    owner_id: int
    pool_type: Optional[str] = "standard"
    starting_lives: Optional[int] = 3
    picks_per_week: Optional[int] = 1
    total_games_per_week: Optional[int] = 5


class PoolRead(BaseModel):
    id: int
    name: str
    owner_id: int
    pool_type: str
    starting_lives: int
    picks_per_week: int
    total_games_per_week: int

    class Config:
        from_attributes = True

