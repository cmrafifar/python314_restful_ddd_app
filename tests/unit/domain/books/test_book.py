from uuid import UUID

import pytest

from bookstore_api.domain.books.book import Book
from bookstore_api.domain.books.isbn import ISBN


def test_create_book() -> None:
    book = Book.create(
        isbn=ISBN("9780132350884"),
        title="Clean Code",
        author="Robert C. Martin",
    )

    assert isinstance(book.id, UUID)
    assert book.title == "Clean Code"
    assert book.author == "Robert C. Martin"


def test_book_title_cannot_be_empty() -> None:
    with pytest.raises(ValueError, match="Title cannot be empty"):
        Book.create(
            isbn=ISBN("9780132350884"),
            title="   ",
            author="Robert C. Martin",
        )


def test_book_can_be_renamed() -> None:
    book = Book.create(
        isbn=ISBN("9780132350884"),
        title="Original",
        author="Robert C. Martin",
    )

    book.rename("Updated")

    assert book.title == "Updated"


def test_book_cannot_be_renamed_to_empty_title() -> None:
    book = Book.create(
        isbn=ISBN("9780132350884"),
        title="Original",
        author="Robert C. Martin",
    )

    with pytest.raises(ValueError):
        book.rename("")

    assert book.title == "Original"
