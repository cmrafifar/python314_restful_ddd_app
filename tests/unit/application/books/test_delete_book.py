from uuid import uuid4

import pytest

from bookstore_api.application.books.commands import DeleteBookCommand
from bookstore_api.application.books.delete_book import DeleteBookService
from bookstore_api.application.books.errors import BookNotFoundError, BookVersionConflictError
from bookstore_api.domain.books.book import Book
from bookstore_api.domain.books.isbn import ISBN
from tests.fakes.book_repository import FakeBookRepository
from tests.fakes.unit_of_work import FakeUnitOfWork


@pytest.fixture
def repository() -> FakeBookRepository:
    return FakeBookRepository()


@pytest.fixture
def book(repository: FakeBookRepository) -> Book:
    book = Book.create(ISBN("9780132350884"), "Original", "Author")
    repository.add(book)
    return book


@pytest.mark.parametrize("versions", [frozenset({1}), frozenset({1, 2}), None])
def test_delete_commits_when_version_matches(
    repository: FakeBookRepository, book: Book, versions: frozenset[int] | None
) -> None:
    uow = FakeUnitOfWork(repository)

    DeleteBookService(lambda: uow).execute(DeleteBookCommand(book.id, versions))

    assert repository.get_by_id(book.id) is None
    assert uow.committed is True


@pytest.mark.parametrize("versions", [frozenset({2}), frozenset()])
def test_nonmatching_version_preserves_book_without_commit(
    repository: FakeBookRepository, book: Book, versions: frozenset[int]
) -> None:
    uow = FakeUnitOfWork(repository)

    with pytest.raises(BookVersionConflictError):
        DeleteBookService(lambda: uow).execute(DeleteBookCommand(book.id, versions))

    stored = repository.get_by_id(book.id)
    assert stored is not None
    assert (stored.title, stored.version) == ("Original", 1)
    assert uow.committed is False


def test_missing_book_is_rejected_without_commit(repository: FakeBookRepository) -> None:
    uow = FakeUnitOfWork(repository)

    with pytest.raises(BookNotFoundError):
        DeleteBookService(lambda: uow).execute(DeleteBookCommand(uuid4(), None))

    assert uow.committed is False


def test_repository_conflict_does_not_commit() -> None:
    class RacingRepository(FakeBookRepository):
        def delete(self, book: Book) -> None:
            raise BookVersionConflictError("Another writer won")

    repository = RacingRepository()
    book = Book.create(ISBN("9780132350884"), "Original", "Author")
    repository.add(book)
    uow = FakeUnitOfWork(repository)

    with pytest.raises(BookVersionConflictError):
        DeleteBookService(lambda: uow).execute(DeleteBookCommand(book.id, frozenset({1})))

    assert uow.committed is False
