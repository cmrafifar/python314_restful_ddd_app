from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from bookstore_api.application.books.errors import BookVersionConflictError
from bookstore_api.domain.books.book import Book
from bookstore_api.domain.books.isbn import ISBN
from bookstore_api.infrastructure.persistence.models.book import BookModel
from bookstore_api.infrastructure.persistence.repositories.sqlalchemy_book_repository import (
    SqlAlchemyBookRepository,
)
from bookstore_api.infrastructure.persistence.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def make_book() -> Book:
    prefix = f"978{uuid4().int % 1_000_000_000:09d}"
    checksum = (-sum(int(digit) * (1 if i % 2 == 0 else 3) for i, digit in enumerate(prefix))) % 10
    return Book.create(ISBN(f"{prefix}{checksum}"), "Original", "Author")


@pytest.mark.parametrize("winner_title", ["Accepted", "Original"])
def test_mysql_version_predicate_rejects_a_stale_writer(
    mysql_engine: Engine, winner_title: str
) -> None:
    factory = sessionmaker(bind=mysql_engine, autoflush=False, expire_on_commit=False)
    book = make_book()
    try:
        with SqlAlchemyUnitOfWork(factory) as uow:
            uow.books.add(book)
            uow.commit()

        with factory() as stale_session:
            # Keep the stale ORM instance alive so the test reaches SQL's version predicate.
            stale_model = stale_session.get(BookModel, str(book.id))
            assert stale_model is not None
            repository = SqlAlchemyBookRepository(stale_session)
            stale_book = repository.get_by_id(book.id)
            assert stale_book is not None
            assert stale_book.version == 1

            with SqlAlchemyUnitOfWork(factory) as winner:
                current = winner.books.get_by_id(book.id)
                assert current is not None
                current.revise_details(title=winner_title)
                assert winner.books.update(current) == 2
                winner.commit()

            stale_book.revise_details(title="Rejected")
            with pytest.raises(BookVersionConflictError) as conflict:
                repository.update(stale_book)
            # The conflict must come from the atomic UPDATE, not only a Python comparison.
            assert conflict.value.__cause__ is not None
            stale_session.rollback()

        with SqlAlchemyUnitOfWork(factory) as reader:
            persisted = reader.books.get_by_id(book.id)
            assert persisted is not None
            assert (persisted.title, persisted.author, persisted.version) == (
                winner_title,
                "Author",
                2,
            )
    finally:
        with mysql_engine.begin() as connection:
            connection.execute(delete(BookModel).where(BookModel.id == str(book.id)))


def test_uncommitted_update_rolls_back_details_and_version(
    session_factory: sessionmaker[Session],
) -> None:
    book = make_book()
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.books.add(book)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        current = uow.books.get_by_id(book.id)
        assert current is not None
        current.revise_details(title="Uncommitted")
        assert uow.books.update(current) == 2
        # Flush succeeded, but leaving without commit must discard both changes.

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        persisted = uow.books.get_by_id(book.id)
        assert persisted is not None
        assert (persisted.title, persisted.version) == ("Original", 1)
