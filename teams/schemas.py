from pydantic import BaseModel

class FantasyTeamBase(BaseModel):
    name: str
    user_id: int
    pool_id: int

class FantasyTeamCreate(FantasyTeamBase):
    pass

class FantasyTeamRead(FantasyTeamBase):
    id: int

    class Config:
        orm_mode = True
