from uuid import UUID

from bookstore_api.application.books.ports import BookRepository
from bookstore_api.domain.books.book import Book
from bookstore_api.domain.books.isbn import ISBN


class FakeBookRepository(BookRepository):
    def __init__(self) -> None:
        self.books: dict[UUID, Book] = {}

    def get_by_id(self, book_id: UUID) -> Book | None:
        return self.books.get(book_id)

    def get_by_isbn(self, isbn: ISBN) -> Book | None:
        return next(
            (book for book in self.books.values() if book.isbn == isbn),
            None,
        )

    def add(self, book: Book) -> None:
        self.books[book.id] = book
