from contextlib import nullcontext
from unittest.mock import create_autospec
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from bookstore_api.application.books.create_book import BookAlreadyExistsError
from bookstore_api.domain.books.book import Book
from bookstore_api.domain.books.isbn import ISBN
from bookstore_api.infrastructure.persistence.models.book import BookModel
from bookstore_api.infrastructure.persistence.sqlalchemy_unit_of_work import (
    SqlAlchemyUnitOfWork,
)


def unique_isbn() -> ISBN:
    prefix = f"978{uuid4().int % 1_000_000_000:09d}"

    total = sum(int(digit) * (1 if index % 2 == 0 else 3) for index, digit in enumerate(prefix))

    check_digit = (-total) % 10

    return ISBN(f"{prefix}{check_digit}")


def test_repository_persists_and_reconstructs_book(
    session_factory: sessionmaker[Session],
) -> None:
    book = Book.create(
        isbn=unique_isbn(),
        title="Clean Architecture",
        author="Robert C. Martin",
    )

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.books.add(book)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        retrieved = uow.books.get_by_id(book.id)

    assert retrieved is not None
    assert retrieved.id == book.id
    assert retrieved.isbn == book.isbn
    assert retrieved.title == book.title
    assert retrieved.author == book.author
    assert retrieved is not book


def test_unit_of_work_discards_uncommitted_book(
    session_factory: sessionmaker[Session],
) -> None:
    book = Book.create(
        isbn=unique_isbn(),
        title="Uncommitted Book",
        author="Test Author",
    )

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.books.add(book)
        # No commit.

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        retrieved = uow.books.get_by_id(book.id)

    assert retrieved is None


def test_mysql_rejects_duplicate_isbn(
    session_factory: sessionmaker[Session],
) -> None:
    isbn = unique_isbn()

    first = Book.create(
        isbn=isbn,
        title="First Book",
        author="Author One",
    )

    second = Book.create(
        isbn=isbn,
        title="Second Book",
        author="Author Two",
    )

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.books.add(first)
        uow.commit()

    with pytest.raises(BookAlreadyExistsError), SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.books.add(second)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        persisted = uow.books.get_by_isbn(isbn)
        rejected = uow.books.get_by_id(second.id)

    assert persisted is not None
    assert persisted.id == first.id
    assert rejected is None


@pytest.mark.parametrize("raise_error", [False, True], ids=["normal-exit", "exception"])
def test_unit_of_work_rolls_back_flushed_book(
    session_factory: sessionmaker[Session],
    raise_error: bool,
) -> None:
    book = Book.create(
        isbn=unique_isbn(),
        title="Flushed Book",
        author="Test Author",
    )

    with session_factory() as session:
        # Control session creation so the test can flush real SQL without exposing UoW internals.
        factory = create_autospec(session_factory, return_value=session)
        expected_error = (
            pytest.raises(RuntimeError, match="^Failure after flush$")
            if raise_error
            else nullcontext()
        )

        with expected_error, SqlAlchemyUnitOfWork(factory) as uow:
            uow.books.add(book)
            session.flush()

            assert session.get(BookModel, str(book.id)) is not None

            if raise_error:
                raise RuntimeError("Failure after flush")

        with SqlAlchemyUnitOfWork(session_factory) as uow:
            retrieved = uow.books.get_by_id(book.id)

        assert retrieved is None


def test_commit_is_visible_to_independent_connection(
    mysql_engine: Engine,
) -> None:
    book = Book.create(
        isbn=unique_isbn(),
        title="Durable Book",
        author="Test Author",
    )

    factory = sessionmaker(
        bind=mysql_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    try:
        with SqlAlchemyUnitOfWork(factory) as uow:
            uow.books.add(book)
            uow.commit()

        with mysql_engine.connect() as connection:
            persisted = connection.execute(
                BookModel.__table__.select().where(BookModel.id == str(book.id))
            ).one_or_none()

        assert persisted is not None
        assert persisted.isbn == book.isbn.value

    finally:
        with mysql_engine.begin() as connection:
            connection.execute(delete(BookModel).where(BookModel.id == str(book.id)))
