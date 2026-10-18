
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

from bookstore_api.config import get_settings
from bookstore_api.infrastructure.persistence.base import Base
from bookstore_api.infrastructure.persistence.database import create_db_engine

# Import mapped classes to register their tables with Base.metadata.
from bookstore_api.infrastructure.persistence.models.book import BookModel  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate SQL without opening a database connection."""
    engine = create_db_engine(get_settings())

    try:
        context.configure(
            url=engine.url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )

        with context.begin_transaction():
            context.run_migrations()
    finally:
        engine.dispose()


def run_migrations_online() -> None:
    """Run migrations against the configured database."""
    engine = create_db_engine(get_settings()).execution_options(
        # isolation_level="READ COMMITTED"  # Alembic migration connection management is independent of application-level Unit of Work semantics
    )

    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

