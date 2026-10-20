from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from bookstore_api.application.books.ports import BookRepository
from bookstore_api.domain.books.book import Book
from bookstore_api.domain.books.isbn import ISBN
from bookstore_api.infrastructure.persistence.mappers.book_mapper import BookMapper
from bookstore_api.infrastructure.persistence.models.book import BookModel


class SqlAlchemyBookRepository(BookRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, book_id: UUID) -> Book | None:
        model = self._session.get(BookModel, str(book_id))

        if model is None:
            return None

        return BookMapper.to_domain(model)

    def get_by_isbn(self, isbn: ISBN) -> Book | None:
        statement = select(BookModel).where(BookModel.isbn == isbn.value)

        model = self._session.scalar(statement)

        if model is None:
            return None

        return BookMapper.to_domain(model)

    def add(self, book: Book) -> None:
        model = BookMapper.to_model(book)

        self._session.add(model)
