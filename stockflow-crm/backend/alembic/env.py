import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

# Make sure the backend/app package is importable when running alembic from
# the backend/ directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.base import Base  # noqa: E402
import app.models  # noqa: F401, E402 — registers all models with Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Read DATABASE_URL from environment (loaded by pydantic-settings / python-dotenv).
from dotenv import load_dotenv, find_dotenv

# Search upward from the current working directory so the command works
# whether run from backend/ or from the repo root.
load_dotenv(find_dotenv(usecwd=True) or os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
DATABASE_URL = os.environ["DATABASE_URL"]
# NOTE: We do NOT pass the URL through set_main_option because configparser
# performs %-interpolation which breaks percent-encoded characters (e.g. %27).


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
