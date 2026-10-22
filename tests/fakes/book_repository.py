from copy import deepcopy
from uuid import UUID

from bookstore_api.application.books.errors import BookVersionConflictError
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

    def add(self, book: Book) -> None:
        self.books[book.id] = deepcopy(book)

    def update(self, book: Book) -> int:
        stored = self.books.get(book.id)
        if stored is None or stored.version != book.version:
            raise BookVersionConflictError("The book changed or was deleted")
        book.version += 1
        self.books[book.id] = deepcopy(book)
        return book.version
