from sqlalchemy import Column, Integer, String, ForeignKey
from database import Base

class Team(Base):
    __tablename__ = "fantasy_teams"

    id = Column(Integer, primary_key=True, index=True)

    # The name the USER chooses (e.g., "Bruno’s Legends")
    name = Column(String, nullable=False)

    # The pool this fantasy team belongs to
    pool_id = Column(Integer, ForeignKey("pools.id"), nullable=False)

    # The user who owns this fantasy team
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
