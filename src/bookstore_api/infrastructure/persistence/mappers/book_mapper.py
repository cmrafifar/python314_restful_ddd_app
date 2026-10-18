from uuid import UUID

from bookstore_api.domain.books.book import Book
from bookstore_api.domain.books.isbn import ISBN
from bookstore_api.infrastructure.persistence.models.book import BookModel


class BookMapper:
    @staticmethod
    def to_model(book: Book) -> BookModel:
        return BookModel(
            id=str(book.id),
            isbn=book.isbn.value,
            title=book.title,
            author=book.author,
        )

    @staticmethod
    def to_domain(model: BookModel) -> Book:
        return Book(
            id=UUID(model.id),
            isbn=ISBN(model.isbn),
            title=model.title,
            author=model.author,
        )
