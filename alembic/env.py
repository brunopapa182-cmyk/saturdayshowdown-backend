import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# ---------------------------------------------------------
# Add project directory to PYTHONPATH
# ---------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
sys.path.append(PROJECT_DIR)

# ---------------------------------------------------------
# Import your database Base + models
# ---------------------------------------------------------
from database import Base

from auth.user_model import User
from teams.models import FantasyTeam

# IMPORTANT: Pool is in pool_model.py, other models are in models.py
from pools.pool_model import Pool
from pools.models import PoolMember, BuyIn, PoolSettings, NewsEvent, Game

# ---------------------------------------------------------
# Alembic Config
# ---------------------------------------------------------
config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata

# ---------------------------------------------------------
# Run migrations offline
# ---------------------------------------------------------
def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

# ---------------------------------------------------------
# Run migrations online
# ---------------------------------------------------------
def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()

# ---------------------------------------------------------
# Choose mode
# ---------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
