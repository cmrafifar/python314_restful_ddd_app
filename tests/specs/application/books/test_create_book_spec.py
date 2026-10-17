
from unittest.mock import create_autospec

import pytest

from bookstore_api.application.books.commands import CreateBookCommand
from bookstore_api.application.books.create_book import (
    BookAlreadyExistsError,
    CreateBookService,
)
from bookstore_api.application.books.ports import BookRepository
from bookstore_api.domain.books.book import Book
from bookstore_api.domain.books.isbn import ISBN


def test_it_creates_a_book() -> None:
    # Arrange
    repository = create_autospec(BookRepository, instance=True)
    repository.get_by_isbn.return_value = None

    service = CreateBookService(repository)

    command = CreateBookCommand(
        isbn="9780132350884",
        title="Clean Code",
        author="Robert C. Martin",
    )

    # Act
    result = service.execute(command)

    # Assert
    repository.get_by_isbn.assert_called_once_with(
        ISBN("9780132350884")
    )

    repository.add.assert_called_once()

    book = repository.add.call_args.args[0]

    assert isinstance(book, Book)
    assert book.id == result.book_id
    assert book.isbn == ISBN(command.isbn)
    assert book.title == command.title
    assert book.author == command.author


def test_it_rejects_a_book_with_an_existing_isbn() -> None:
    # Arrange
    repository = create_autospec(BookRepository, instance=True)

    existing_book = Book.create(
        isbn=ISBN("9780132350884"),
        title="Existing Book",
        author="Existing Author",
    )

    repository.get_by_isbn.return_value = existing_book

    service = CreateBookService(repository)

    command = CreateBookCommand(
        isbn="9780132350884",
        title="Clean Code",
        author="Robert C. Martin",
    )

    # Act / Assert
    with pytest.raises(BookAlreadyExistsError):
        service.execute(command)

    repository.get_by_isbn.assert_called_once_with(
        ISBN("9780132350884")
    )

    repository.add.assert_not_called()

