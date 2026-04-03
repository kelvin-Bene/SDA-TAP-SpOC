"""Alembic environment configuration.

Reads DATABASE_URL from environment for migration target.
Only runs against PostgreSQL (not DuckDB).
"""
import os
from logging.config import fileConfig

from alembic import context

# Read alembic.ini for logging config
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get database URL from environment
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError(
        "DATABASE_URL must be set for Alembic migrations. "
        "Alembic only targets PostgreSQL, not DuckDB."
    )

config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode -- generates SQL script."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode -- connects to database."""
    from sqlalchemy import create_engine, text

    connectable = create_engine(config.get_main_option("sqlalchemy.url"))

    with connectable.connect() as connection:
        # Acquire advisory lock to prevent concurrent migrations
        connection.execute(text("SELECT pg_advisory_lock(123456789)"))
        try:
            context.configure(connection=connection, target_metadata=None)
            with context.begin_transaction():
                context.run_migrations()
        finally:
            # Always release the advisory lock
            connection.execute(text("SELECT pg_advisory_unlock(123456789)"))
            connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
