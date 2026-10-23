from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from bookstore_api.application.books.errors import BookVersionConflictError
from bookstore_api.domain.books.book import Book
from bookstore_api.domain.books.isbn import ISBN
from bookstore_api.infrastructure.persistence.models.book import BookModel
from bookstore_api.infrastructure.persistence.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def make_book() -> Book:
    prefix = f"978{uuid4().int % 1_000_000_000:09d}"
    checksum = (-sum(int(digit) * (1 if i % 2 == 0 else 3) for i, digit in enumerate(prefix))) % 10
    return Book.create(ISBN(f"{prefix}{checksum}"), "Original", "Author")


def test_delete_frees_isbn(
    session_factory: sessionmaker[Session],
) -> None:
    book = make_book()
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.books.add(book)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.books.delete(book)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.books.get_by_id(book.id) is None
        replacement = Book.create(book.isbn, "Replacement", "Author")
        uow.books.add(replacement)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.books.get_by_id(replacement.id) is not None


def test_delete_missing_book_raises_conflict(session_factory: sessionmaker[Session]) -> None:
    with SqlAlchemyUnitOfWork(session_factory) as uow, pytest.raises(BookVersionConflictError):
        uow.books.delete(make_book())


def test_uncommitted_delete_rolls_back(session_factory: sessionmaker[Session]) -> None:
    book = make_book()
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.books.add(book)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.books.delete(book)
        assert uow.books.get_by_id(book.id) is None

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.books.get_by_id(book.id) is not None


@pytest.fixture
def committed_book(mysql_engine: Engine) -> Iterator[Book]:
    """Seed a durable row so tests can use independent database connections."""
    factory = sessionmaker(bind=mysql_engine, autoflush=False, expire_on_commit=False)
    book = make_book()
    try:
        with SqlAlchemyUnitOfWork(factory) as uow:
            uow.books.add(book)
            uow.commit()
        yield book
    finally:
        with mysql_engine.begin() as connection:
            connection.execute(delete(BookModel).where(BookModel.id == str(book.id)))


def test_concurrent_update_prevents_stale_delete(
    mysql_engine: Engine, committed_book: Book
) -> None:
    factory = sessionmaker(bind=mysql_engine, autoflush=False, expire_on_commit=False)
    with SqlAlchemyUnitOfWork(factory) as stale:
        loaded = stale.books.get_by_id(committed_book.id)
        assert loaded is not None

        with SqlAlchemyUnitOfWork(factory) as winner:
            committed_book.revise_details(title="Accepted")
            winner.books.update(committed_book)
            winner.commit()

        with pytest.raises(BookVersionConflictError):
            stale.books.delete(loaded)

    with SqlAlchemyUnitOfWork(factory) as reader:
        persisted = reader.books.get_by_id(committed_book.id)
        assert persisted is not None
        assert (persisted.title, persisted.version) == ("Accepted", 2)


def test_concurrent_delete_prevents_stale_delete(
    mysql_engine: Engine, committed_book: Book
) -> None:
    factory = sessionmaker(bind=mysql_engine, autoflush=False, expire_on_commit=False)
    with SqlAlchemyUnitOfWork(factory) as stale:
        loaded = stale.books.get_by_id(committed_book.id)
        assert loaded is not None

        with SqlAlchemyUnitOfWork(factory) as winner:
            winner.books.delete(committed_book)
            winner.commit()

        with pytest.raises(BookVersionConflictError):
            stale.books.delete(loaded)

    with SqlAlchemyUnitOfWork(factory) as reader:
        assert reader.books.get_by_id(committed_book.id) is None
