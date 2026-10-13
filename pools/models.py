from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Time
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base

# ---------------------------------------------------------
# POOL MODEL (⭐ REQUIRED — FIXED)
# ---------------------------------------------------------
class Pool(Base):
    __tablename__ = "pools"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, nullable=False)

    name = Column(String, nullable=False)
    pool_type = Column(String, nullable=False)

    starting_lives = Column(Integer, default=3)
    picks_per_week = Column(Integer, default=1)
    total_games_per_week = Column(Integer, default=0)


    # Relationships
    members = relationship("PoolMember", backref="pool")
    settings = relationship("PoolSettings", backref="pool")
    buyins = relationship("BuyIn", backref="pool")
    news = relationship("NewsEvent", backref="pool")
    games = relationship("Game", backref="pool")


# ---------------------------------------------------------
# GAME MODEL (⭐ REQUIRED FOR SCORING + INGEST)
# ---------------------------------------------------------
class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)

    # Every game belongs to a pool
    pool_id = Column(Integer, ForeignKey("pools.id"), nullable=False)

    # NHL API fields
    game_date = Column(DateTime, nullable=False)   # real DateTime
    game_time = Column(Time, nullable=True)        # local start time

    # IDs
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)

    # ⭐ NEW FIELDS: REAL NHL TEAM DATA
    home_team_name = Column(String, nullable=True)
    away_team_name = Column(String, nullable=True)
    home_abbrev = Column(String, nullable=True)
    away_abbrev = Column(String, nullable=True)

    # Scores
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)

    # Result fields
    is_completed = Column(Boolean, default=False)
    winner = Column(String, nullable=True)  # "home", "away", or teamId

    # Relationship to picks
    picks = relationship("Pick", backref="game")


# ---------------------------------------------------------
# POOL SETTINGS
# ---------------------------------------------------------
class PoolSettings(Base):
    __tablename__ = "pool_settings"

    id = Column(Integer, primary_key=True, index=True)
    pool_id = Column(Integer, ForeignKey("pools.id"), nullable=False)

    starting_lives = Column(Integer, default=3)
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
# POOL MEMBERS
# ---------------------------------------------------------
class PoolMember(Base):
    __tablename__ = "pool_members"

    id = Column(Integer, primary_key=True, index=True)
    pool_id = Column(Integer, ForeignKey("pools.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    remaining_lives = Column(Integer, default=3)
    buyin_adjustment = Column(Integer, default=0)
    buyin_date = Column(String, default="")

    # ⭐ NEW FIELD FOR SURVIVOR ENGINE (Step 8)
    is_eliminated = Column(Boolean, default=False)


# ---------------------------------------------------------
# PICKS (⭐ UPDATED FOR GAME + SCORING)
# ---------------------------------------------------------
class Pick(Base):
    __tablename__ = "picks"

    # Flutter uses string IDs
    id = Column(String, primary_key=True, index=True)

    # User who made the pick
    user_id = Column(String, nullable=False)

    # Game this pick belongs to
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)

    # "home", "away", or teamId
    selection = Column(String, nullable=True)

    # null until admin grades results
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
