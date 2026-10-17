import pytest

from bookstore_api.application.books.commands import CreateBookCommand
from bookstore_api.application.books.create_book import (
    BookAlreadyExistsError,
    CreateBookService,
)
from bookstore_api.domain.books.isbn import ISBN
from tests.fakes.book_repository import FakeBookRepository


def test_create_book() -> None:
    repository = FakeBookRepository()
    service = CreateBookService(repository)

    command = CreateBookCommand(
        isbn="9780132350884",
        title="Clean Code",
        author="Robert C. Martin",
    )

    result = service.execute(command)

    book = repository.get_by_id(result.book_id)

    assert book is not None
    assert book.id == result.book_id
    assert book.isbn == ISBN(command.isbn)
    assert book.title == command.title
    assert book.author == command.author


def test_cannot_create_duplicate_book() -> None:
    repository = FakeBookRepository()
    service = CreateBookService(repository)

    command = CreateBookCommand(
        isbn="9780132350884",
        title="Clean Code",
        author="Robert C. Martin",
    )

    service.execute(command)

    with pytest.raises(BookAlreadyExistsError):
        service.execute(command)

    assert len(repository.books) == 1
