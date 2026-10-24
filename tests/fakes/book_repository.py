from collections.abc import Iterator
from copy import deepcopy
from uuid import UUID

from bookstore_api.application.books.errors import BookVersionConflictError
from bookstore_api.application.books.pagination import BookPageCursor
from bookstore_api.application.books.ports import BookRepository
from bookstore_api.domain.books.book import Book
from bookstore_api.domain.books.isbn import ISBN


class FakeBookRepository(BookRepository):
    def __init__(self) -> None:
        self.books: dict[UUID, Book] = {}

    def get_by_id(self, book_id: UUID) -> Book | None:
        return deepcopy(self.books.get(book_id))

    def get_by_isbn(self, isbn: ISBN) -> Book | None:
        return next(
            (book for book in self.books.values() if book.isbn == isbn),
            None,
        )

    def list_books(
        self,
        *,
        title: str | None,
        author: str | None,
        limit: int,
        cursor: BookPageCursor | None = None,
    ) -> list[Book]:
        ordered = sorted(
            self._matching_books(title=title, author=author, cursor=cursor),
            key=lambda book: book.isbn.value,
            reverse=cursor is not None and cursor.direction == "previous",
        )
        return deepcopy(ordered[:limit])

    def has_books(self, *, title: str | None, author: str | None, cursor: BookPageCursor) -> bool:
        return any(self._matching_books(title=title, author=author, cursor=cursor))

    def _matching_books(
        self, *, title: str | None, author: str | None, cursor: BookPageCursor | None
    ) -> Iterator[Book]:
        for book in self.books.values():
            if title is not None and title not in book.title:
                continue
            if author is not None and author not in book.author:
                continue
            if cursor is not None:
                if cursor.direction == "next" and book.isbn.value <= cursor.isbn.value:
                    continue
                if cursor.direction == "previous" and book.isbn.value >= cursor.isbn.value:
                    continue
            yield book

    def add(self, book: Book) -> None:
        self.books[book.id] = deepcopy(book)

    def update(self, book: Book) -> int:
        stored = self.books.get(book.id)
        if stored is None or stored.version != book.version:
            raise BookVersionConflictError("The book changed or was deleted")
        book.version += 1
        self.books[book.id] = deepcopy(book)
        return book.version

    def delete(self, book: Book) -> None:
        stored = self.books.get(book.id)
        if stored is None or stored.version != book.version:
            raise BookVersionConflictError("The book changed or was deleted")
        del self.books[book.id]
