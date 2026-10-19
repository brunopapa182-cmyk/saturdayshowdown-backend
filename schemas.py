from typing import Optional, List
from pydantic import BaseModel

# ---------------------------------------------------------
# POOL SETTINGS READ
# ---------------------------------------------------------
class PoolSettingsRead(BaseModel):
    starting_lives: int
    picks_per_week: int
    total_games_per_week: int

    class Config:
        from_attributes = True


# ---------------------------------------------------------
# POOL MEMBER READ
# ---------------------------------------------------------
class PoolMemberRead(BaseModel):
    user_id: int
    remaining_lives: int
    buyin_adjustment: int
    is_eliminated: bool

    class Config:
        from_attributes = True


# ---------------------------------------------------------
# POOL CREATE
# ---------------------------------------------------------
class PoolCreate(BaseModel):
    name: str
    owner_id: int
    pool_type: Optional[str] = "standard"
    starting_lives: Optional[int] = 5
    picks_per_week: Optional[int] = 1
    total_games_per_week: Optional[int] = 5


# ---------------------------------------------------------
# POOL READ (⭐ FIXED — CORRECT SOURCE OF TRUTH)
# ---------------------------------------------------------
class PoolRead(BaseModel):
    id: int
    name: str
    owner_id: int
    pool_type: str

    # ⭐ Correct values from PoolSettings
    settings: List[PoolSettingsRead]

    # ⭐ Correct values per member
    members: List[PoolMemberRead]

    class Config:
        from_attributes = True
