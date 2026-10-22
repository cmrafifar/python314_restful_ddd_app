from uuid import uuid4

import pytest

from bookstore_api.application.books.commands import UpdateBookCommand
from bookstore_api.application.books.errors import BookNotFoundError, BookVersionConflictError
from bookstore_api.application.books.update_book import UpdateBookService
from bookstore_api.domain.books.book import Book
from bookstore_api.domain.books.isbn import ISBN
from tests.fakes.book_repository import FakeBookRepository
from tests.fakes.unit_of_work import FakeUnitOfWork


def test_updates_selected_details_and_commits_new_version() -> None:
    repository = FakeBookRepository()
    book = Book.create(ISBN("9780132350884"), "Original", "Author")
    repository.add(book)
    uow = FakeUnitOfWork(repository)

    result = UpdateBookService(lambda: uow).execute(
        UpdateBookCommand(
            book_id=book.id,
            expected_versions=frozenset({1}),
            title="Updated",
        )
    )

    assert (result.title, result.author, result.version) == ("Updated", "Author", 2)
    assert result.book_id == book.id
    assert result.isbn == book.isbn
    assert uow.committed is True


def test_stale_version_is_rejected_without_commit_or_mutation() -> None:
    repository = FakeBookRepository()
    book = Book.create(ISBN("9780132350884"), "Original", "Author")
    repository.add(book)
    uow = FakeUnitOfWork(repository)

    with pytest.raises(BookVersionConflictError):
        UpdateBookService(lambda: uow).execute(
            UpdateBookCommand(
                book_id=book.id,
                expected_versions=frozenset({2}),
                title="Updated",
            )
        )

    assert repository.books[book.id].title == "Original"
    assert uow.committed is False


def test_missing_book_is_rejected_without_commit() -> None:
    uow = FakeUnitOfWork(FakeBookRepository())

    with pytest.raises(BookNotFoundError):
        UpdateBookService(lambda: uow).execute(
            UpdateBookCommand(
                book_id=uuid4(),
                expected_versions=frozenset({1}),
                title="Updated",
            )
        )

    assert uow.committed is False


def test_invalid_details_leave_persisted_book_intact() -> None:
    repository = FakeBookRepository()
    book = Book.create(ISBN("9780132350884"), "Original", "Author")
    repository.add(book)
    uow = FakeUnitOfWork(repository)

    with pytest.raises(ValueError):
        UpdateBookService(lambda: uow).execute(
            UpdateBookCommand(
                book_id=book.id,
                expected_versions=frozenset({1}),
                title="Updated",
                author="a" * 81,
            )
        )

    assert (repository.books[book.id].title, repository.books[book.id].version) == ("Original", 1)
    assert uow.committed is False


def test_flush_conflict_does_not_commit() -> None:
    class RacingRepository(FakeBookRepository):
        def update(self, book: Book) -> int:
            raise BookVersionConflictError("Another writer won")

    repository = RacingRepository()
    book = Book.create(ISBN("9780132350884"), "Original", "Author")
    repository.add(book)
    uow = FakeUnitOfWork(repository)

    with pytest.raises(BookVersionConflictError):
        UpdateBookService(lambda: uow).execute(
            UpdateBookCommand(
                book_id=book.id,
                expected_versions=frozenset({1}),
                title="Updated",
            )
        )

    assert uow.committed is False


def test_empty_update_is_rejected() -> None:
    uow = FakeUnitOfWork(FakeBookRepository())
    with pytest.raises(ValueError, match="At least one"):
        UpdateBookService(lambda: uow).execute(
            UpdateBookCommand(
                book_id=uuid4(),
                expected_versions=frozenset({1}),
            )
        )
    assert uow.committed is False
