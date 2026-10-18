import pytest

from bookstore_api.application.books.commands import CreateBookCommand
from bookstore_api.application.books.create_book import (
    BookAlreadyExistsError,
    CreateBookService,
)
from bookstore_api.domain.books.isbn import ISBN
from tests.fakes.book_repository import FakeBookRepository
from tests.fakes.unit_of_work import FakeUnitOfWork


def test_create_book() -> None:
    repository = FakeBookRepository()
    uow = FakeUnitOfWork(repository)
    service = CreateBookService(lambda: uow)

    command = CreateBookCommand(
        isbn="9780132350884",
        title="Clean Code",
        author="Robert C. Martin",
    )

    result = service.execute(command)
    book = repository.get_by_id(result.book_id)

    assert book is not None
    assert book.isbn == ISBN(command.isbn)
    assert book.title == command.title
    assert book.author == command.author
    assert uow.committed is True


def test_rejects_duplicate_isbn() -> None:
    repository = FakeBookRepository()
    service = CreateBookService(
        lambda: FakeUnitOfWork(repository)
    )

    command = CreateBookCommand(
        isbn="9780132350884",
        title="Clean Code",
        author="Robert C. Martin",
    )

    service.execute(command)

    second_uow = FakeUnitOfWork(repository)
    duplicate_service = CreateBookService(lambda: second_uow)

    with pytest.raises(BookAlreadyExistsError):
        duplicate_service.execute(command)

    assert len(repository.books) == 1
    assert second_uow.committed is False
