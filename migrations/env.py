"""Alembic environment for MedIntelOS.

The application (postgres_repository.py) talks to Postgres via psycopg
directly and has no SQLAlchemy dependency. SQLAlchemy is used here only
because Alembic needs an Engine to run migrations against — this is
Alembic's normal mode of operation and does not imply the app uses an ORM.

The connection string always comes from MEDINTELOS_DATABASE_URL (the same
variable the app reads via config.py), never from a value committed here, so
the same migrations run unmodified in development, CI, and production.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None  # migrations are written by hand with raw SQL/op.*


def _database_url() -> str:
    url = os.getenv("MEDINTELOS_DATABASE_URL")
    if not url:
        raise RuntimeError(
            "MEDINTELOS_DATABASE_URL must be set before running Alembic. "
            "See docs/DEPLOYMENT.md."
        )
    # Alembic/SQLAlchemy need the psycopg3 dialect prefix; accept a plain
    # postgresql:// URL (what most operators and .env.example files use) and
    # rewrite it, so the same MEDINTELOS_DATABASE_URL works for both the app
    # (psycopg.connect, which wants a plain DSN) and Alembic.
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
