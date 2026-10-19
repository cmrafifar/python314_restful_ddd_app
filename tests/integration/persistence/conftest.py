import os
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture(scope="session")
def mysql_engine() -> Iterator[Engine]:
    database_url = os.environ.get("BOOKSTORE_TEST_DATABASE_URL")

    if database_url is None:
        pytest.fail(
            "BOOKSTORE_TEST_DATABASE_URL must be configured"
        )

    url = make_url(database_url)

    if url.get_backend_name() != "mysql":
        pytest.fail("Integration tests require MySQL")

    if url.database != "bookstore_test":
        pytest.fail(
            "Refusing to run against a non-test database"
        )

    engine = create_engine(
        url,
        pool_pre_ping=True,
    )

    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def session_factory(
    mysql_engine: Engine,
) -> Iterator[sessionmaker[Session]]:
    with mysql_engine.connect() as connection:
        transaction = connection.begin()

        factory = sessionmaker(
            bind=connection,
            autoflush=False,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        try:
            yield factory
        finally:
            transaction.rollback()
