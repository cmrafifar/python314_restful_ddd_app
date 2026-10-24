from typing import Protocol
from uuid import UUID

from bookstore_api.application.books.pagination import BookPageCursor
from bookstore_api.domain.books.book import Book
from bookstore_api.domain.books.isbn import ISBN


class BookRepository(Protocol):
    def get_by_id(self, book_id: UUID) -> Book | None: ...

    def get_by_isbn(self, isbn: ISBN) -> Book | None: ...

    def list_books(
        self,
        *,
        title: str | None,
        author: str | None,
        limit: int,
        cursor: BookPageCursor | None = None,
    ) -> list[Book]:
        """Return matching books in ISBN seek order, up to limit.

        Combine case-sensitive literal substring filters with AND.
        None disables a filter. Do not commit.
        A cursor excludes its boundary. Default and next navigation use ascending order;
        previous navigation uses descending order so the nearest preceding rows come first.
        """
        ...

    def has_books(self, *, title: str | None, author: str | None, cursor: BookPageCursor) -> bool:
        """Check for a matching book strictly beyond the boundary in the given direction.

        Use the same filters as list_books, without loading the collection or committing.
        """
        ...

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
