from typing import Protocol
from uuid import UUID

from bookstore_api.domain.books.book import Book
from bookstore_api.domain.books.isbn import ISBN


class BookRepository(Protocol):
    def get_by_id(self, book_id: UUID) -> Book | None: ...

    def get_by_isbn(self, isbn: ISBN) -> Book | None: ...

    def add(self, book: Book) -> None: ...

    def update(self, book: Book) -> int:
        """Save details only if the stored version equals book.version; return the new version.

        Raise BookVersionConflictError on a stale version or a concurrent deletion.
        The caller must still commit the unit of work.
        """
        ...

    def delete(self, book: Book) -> None:
        """Delete only if the stored version equals book.version.

        Raise BookVersionConflictError on a stale version or a concurrent deletion.
        The caller must still commit the unit of work.
        """
        ...
