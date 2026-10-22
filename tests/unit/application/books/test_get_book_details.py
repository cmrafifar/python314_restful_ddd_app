from uuid import uuid4

import pytest

from bookstore_api.application.books.get_book_details import (
    BookNotFoundError,
    GetBookDetailsService,
)
from bookstore_api.domain.books.book import Book
from bookstore_api.domain.books.isbn import ISBN
from tests.fakes.book_repository import FakeBookRepository
from tests.fakes.unit_of_work import FakeUnitOfWork


def test_get_book_details_returns_existing_book() -> None:
    repository = FakeBookRepository()
    book = Book.create(
        isbn=ISBN("9780132350884"),
        title="Clean Code",
        author="Robert C. Martin",
    )
    repository.add(book)
    uow = FakeUnitOfWork(repository)
    service = GetBookDetailsService(lambda: uow)

    result = service.execute(book.id)

    assert result.book_id == book.id
    assert result.isbn == book.isbn
    assert result.title == book.title
    assert result.author == book.author
    assert uow.committed is False


def test_get_book_details_rejects_missing_book() -> None:
    repository = FakeBookRepository()
    repository.add(
        Book.create(
            isbn=ISBN("9780132350884"),
            title="Clean Code",
            author="Robert C. Martin",
        )
    )
    uow = FakeUnitOfWork(repository)
    service = GetBookDetailsService(lambda: uow)
    missing_id = uuid4()

    with pytest.raises(BookNotFoundError, match=str(missing_id)):
        service.execute(missing_id)

    assert uow.committed is False
