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


@pytest.mark.parametrize("title,author", [("t" * 100, "a" * 80), ("  Title  ", " Author ")])
def test_book_accepts_limits_and_trims_text(title: str, author: str) -> None:
    book = Book.create(ISBN("9780132350884"), title, author)

    assert book.title == title.strip()
    assert book.author == author.strip()


@pytest.mark.parametrize(
    "title,author,message",
    [
        ("t" * 101, "Author", "Title cannot exceed 100"),
        ("Title", "a" * 81, "Author cannot exceed 80"),
    ],
)
def test_book_rejects_text_beyond_limits(title: str, author: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        Book.create(ISBN("9780132350884"), title, author)


def test_revising_details_is_atomic_when_author_is_invalid() -> None:
    book = Book.create(ISBN("9780132350884"), "Original", "Author")

    with pytest.raises(ValueError, match="Author cannot exceed 80"):
        book.revise_details(title="New title", author="a" * 81)

    assert (book.title, book.author) == ("Original", "Author")


def test_rename_enforces_title_limit() -> None:
    book = Book.create(ISBN("9780132350884"), "Original", "Author")

    with pytest.raises(ValueError, match="Title cannot exceed 100"):
        book.rename("t" * 101)

    assert book.title == "Original"
