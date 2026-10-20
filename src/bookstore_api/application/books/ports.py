from typing import Protocol
from uuid import UUID

from bookstore_api.domain.books.book import Book
from bookstore_api.domain.books.isbn import ISBN


class BookRepository(Protocol):
    def get_by_id(self, book_id: UUID) -> Book | None: ...

    def get_by_isbn(self, isbn: ISBN) -> Book | None: ...

    def add(self, book: Book) -> None: ...
