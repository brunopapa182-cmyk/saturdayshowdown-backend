from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Pool(Base):
    __tablename__ = "pools"

    id = Column(Integer, primary_key=True, index=True)

    # Basic info
    name = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Pool configuration
    pool_type = Column(String, default="standard")
    starting_lives = Column(Integer, default=5)
    picks_per_week = Column(Integer, default=1)
    total_games_per_week = Column(Integer, default=5)

    # Relationships
    members = relationship("PoolMember", backref="pool")
    buyins = relationship("BuyIn", backref="pool")
    settings = relationship("PoolSettings", backref="pool")
    news = relationship("NewsEvent", backref="pool")
    games = relationship("Game", backref="pool")
