from dataclasses import dataclass
from uuid import UUID

from bookstore_api.application.books.errors import BookNotFoundError
from bookstore_api.application.unit_of_work import UnitOfWorkFactory
from bookstore_api.domain.books.isbn import ISBN

__all__ = ["BookNotFoundError", "GetBookDetailsResult", "GetBookDetailsService"]


@dataclass(frozen=True, slots=True)
class GetBookDetailsResult:
    book_id: UUID
    isbn: ISBN
    title: str
    author: str
    version: int = 1


class GetBookDetailsService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def execute(self, book_id: UUID) -> GetBookDetailsResult:
        with self._uow_factory() as uow:
            book = uow.books.get_by_id(book_id)
            if book is None:
                raise BookNotFoundError(f"Book with id {book_id} not found")
            return GetBookDetailsResult(
                book_id=book.id,
                isbn=book.isbn,
                title=book.title,
                author=book.author,
                version=book.version,
            )
