from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ---------------------------------------------------------
# NEON POSTGRESQL URL (Persistent, IPv4, FastAPI Compatible)
# ---------------------------------------------------------

DATABASE_URL = (
    "postgresql://neondb_owner:npg_8IvM0ajolSUG"
    "@ep-little-sound-b5xd7dx6-pooler.c-7.us-east-2.aws.neon.tech/"
    "neondb?sslmode=require&channel_binding=require"
)

# Debug print so you can confirm in local logs or Render logs
print("Using database:", DATABASE_URL)

# Create engine (PostgreSQL)
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
