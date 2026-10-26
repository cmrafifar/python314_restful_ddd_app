from dataclasses import dataclass
from uuid import UUID

from bookstore_api.application.books.errors import BookNotFoundError
from bookstore_api.application.books.ports import BookRepository
from bookstore_api.application.books.transactions import BookTransactions
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
    def __init__(self, transactions: BookTransactions) -> None:
        self._transactions = transactions

    def execute(self, book_id: UUID) -> GetBookDetailsResult:
        def work(repository: BookRepository) -> GetBookDetailsResult:
            book = repository.get_by_id(book_id)
            if book is None:
                raise BookNotFoundError(f"Book with id {book_id} not found")
            return GetBookDetailsResult(
                book_id=book.id,
                isbn=book.isbn,
                title=book.title,
                author=book.author,
                version=book.version,
            )

        return self._transactions.run(work)
