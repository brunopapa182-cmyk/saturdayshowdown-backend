from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Time
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base

# ---------------------------------------------------------
# POOL MODEL
# ---------------------------------------------------------
class Pool(Base):
    __tablename__ = "pools"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, nullable=False)

    name = Column(String, nullable=False)
    pool_type = Column(String, nullable=False)

    # ⚠️ Deprecated as source of truth — keep for legacy, but don't use in UI
    starting_lives = Column(Integer, default=5)
    picks_per_week = Column(Integer, default=1)
    total_games_per_week = Column(Integer, default=0)

    # Relationships
    members = relationship("PoolMember", backref="pool")
    settings = relationship("PoolSettings", backref="pool", uselist=True)
    buyins = relationship("BuyIn", backref="pool")
    news = relationship("NewsEvent", backref="pool")
    games = relationship("Game", backref="pool")


# ---------------------------------------------------------
# GAME MODEL
# ---------------------------------------------------------
class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    pool_id = Column(Integer, ForeignKey("pools.id"), nullable=False)

    game_date = Column(DateTime, nullable=False)
    game_time = Column(Time, nullable=True)

    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)

    home_team_name = Column(String, nullable=True)
    away_team_name = Column(String, nullable=True)
    home_abbrev = Column(String, nullable=True)
    away_abbrev = Column(String, nullable=True)

    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)

    is_completed = Column(Boolean, default=False)
    winner = Column(String, nullable=True)

    picks = relationship("Pick", backref="game")


# ---------------------------------------------------------
# POOL SETTINGS (SOURCE OF TRUTH)
# ---------------------------------------------------------
class PoolSettings(Base):
    __tablename__ = "pool_settings"

    id = Column(Integer, primary_key=True, index=True)
    pool_id = Column(Integer, ForeignKey("pools.id"), nullable=False)

    starting_lives = Column(Integer, default=5)
    picks_per_week = Column(Integer, default=1)
    total_games_per_week = Column(Integer, default=5)

    updated_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------
# BUY-INS
# ---------------------------------------------------------
class BuyIn(Base):
    __tablename__ = "buyins"

    id = Column(Integer, primary_key=True, index=True)
    pool_id = Column(Integer, ForeignKey("pools.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    amount = Column(Integer, nullable=False)
    paid = Column(Boolean, default=False)
    date_paid = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------
# POOL MEMBERS (LIVES PER USER)
# ---------------------------------------------------------
class PoolMember(Base):
    __tablename__ = "pool_members"

    id = Column(Integer, primary_key=True, index=True)
    pool_id = Column(Integer, ForeignKey("pools.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    remaining_lives = Column(Integer, default=5)
    buyin_adjustment = Column(Integer, default=0)
    buyin_date = Column(String, default="")

    is_eliminated = Column(Boolean, default=False)


# ---------------------------------------------------------
# PICKS
# ---------------------------------------------------------
class Pick(Base):
    __tablename__ = "picks"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    selection = Column(String, nullable=True)
    is_correct = Column(Boolean, nullable=True)


# ---------------------------------------------------------
# NEWS EVENTS
# ---------------------------------------------------------
class NewsEvent(Base):
    __tablename__ = "news_events"

    id = Column(Integer, primary_key=True, index=True)
    pool_id = Column(Integer, ForeignKey("pools.id"), nullable=False)

    date = Column(String, nullable=False)
    message = Column(String, nullable=False)
