from unittest.mock import create_autospec

import pytest

from bookstore_api.application.books.commands import CreateBookCommand
from bookstore_api.application.books.create_book import (
    BookAlreadyExistsError,
    CreateBookService,
)
from bookstore_api.application.books.ports import BookRepository
from bookstore_api.application.unit_of_work import UnitOfWork
from bookstore_api.domain.books.book import Book
from bookstore_api.domain.books.isbn import ISBN


def test_it_creates_and_commits_a_book() -> None:
    # Arrange
    repository = create_autospec(BookRepository, instance=True)
    repository.get_by_isbn.return_value = None

    uow = create_autospec(UnitOfWork, instance=True)
    uow.books = repository
    uow.__enter__.return_value = uow

    service = CreateBookService(lambda: uow)

    command = CreateBookCommand(
        isbn="9780132350884",
        title="Clean Code",
        author="Robert C. Martin",
    )

    # Act
    result = service.execute(command)

    # Assert
    repository.get_by_isbn.assert_called_once_with(ISBN(command.isbn))
    repository.add.assert_called_once()

    book = repository.add.call_args.args[0]

    assert isinstance(book, Book)
    assert book.id == result.book_id
    assert book.title == command.title
    assert book.author == command.author

    uow.commit.assert_called_once_with()
    uow.__exit__.assert_called_once()


def test_it_does_not_commit_when_isbn_already_exists() -> None:
    # Arrange
    repository = create_autospec(BookRepository, instance=True)

    repository.get_by_isbn.return_value = Book.create(
        isbn=ISBN("9780132350884"),
        title="Existing Book",
        author="Existing Author",
    )

    uow = create_autospec(UnitOfWork, instance=True)
    uow.books = repository
    uow.__enter__.return_value = uow

    service = CreateBookService(lambda: uow)

    command = CreateBookCommand(
        isbn="9780132350884",
        title="Clean Code",
        author="Robert C. Martin",
    )

    # Act / Assert
    with pytest.raises(BookAlreadyExistsError):
        service.execute(command)

    repository.add.assert_not_called()
    uow.commit.assert_not_called()
    uow.__exit__.assert_called_once()
