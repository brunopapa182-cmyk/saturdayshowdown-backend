from pydantic import BaseModel
from typing import Optional, List, Dict

# ---------------------------------------------------------
# BASE GAME SCHEMA (matches backend output EXACTLY)
# ---------------------------------------------------------
class GameBase(BaseModel):
    id: int

    # IDs
    home_team_id: int
    away_team_id: int

    # ⭐ NEW FIELDS — REAL NHL TEAM DATA
    home_team_name: Optional[str]
    away_team_name: Optional[str]
    home_abbrev: Optional[str]
    away_abbrev: Optional[str]

    # Formatted start time (e.g., "7:00 PM EST")
    start_time: Optional[str]

    # Game status
    is_completed: bool
    winner: Optional[str] = None

    # Scores
    home_score: Optional[int] = None
    away_score: Optional[int] = None

    class Config:
        orm_mode = True

# ---------------------------------------------------------
# RESPONSE: LIST OF GAMES FOR A POOL
# ---------------------------------------------------------
class GamesByDateResponse(BaseModel):
    gamesByDate: Dict[str, List[GameBase]]

# ---------------------------------------------------------
# RESPONSE: SATURDAY DATES
# ---------------------------------------------------------
class SaturdayDatesResponse(BaseModel):
    saturdays: List[str]

# ---------------------------------------------------------
# REQUEST: UPDATE GAME RESULT
# ---------------------------------------------------------
class GameUpdateRequest(BaseModel):
    game_id: int
    is_completed: bool
    winner: Optional[str] = None

# ---------------------------------------------------------
# RESPONSE: INGEST RESULT
# ---------------------------------------------------------
class IngestResponse(BaseModel):
    message: str
    total_games: int
