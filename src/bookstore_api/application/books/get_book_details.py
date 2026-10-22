from dataclasses import dataclass
from uuid import UUID

from bookstore_api.application.books.ports import BookRepository
from bookstore_api.domain.books.isbn import ISBN


class BookNotFoundError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class GetBookDetailsResult:
    book_id: UUID
    isbn: ISBN
    title: str
    author: str


class GetBookDetailsService:
    def __init__(self, book_repository: BookRepository) -> None:
        self._book_repository = book_repository

    def execute(self, book_id: UUID) -> GetBookDetailsResult:
        book = self._book_repository.get_by_id(book_id)
        if book is None:
            raise BookNotFoundError(f"Book with id {book_id} not found")
        return GetBookDetailsResult(
            book_id=book.id,
            isbn=book.isbn,
            title=book.title,
            author=book.author,
        )
