from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from bookstore_api.application.books.errors import BookVersionConflictError
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

    def update(self, book: Book) -> int:
        model = self._session.get(BookModel, str(book.id))
        if model is None or model.version != book.version:
            raise BookVersionConflictError("The book changed or was deleted")

        model.title = book.title
        model.author = book.author
        model.version += 1
        try:
            # Flush obtains the new version and checks concurrent writes, without committing.
            self._session.flush()
        except StaleDataError as exc:
            raise BookVersionConflictError("The book changed or was deleted") from exc
        return model.version

    def delete(self, book: Book) -> None:
        statement = delete(BookModel).where(
            BookModel.id == str(book.id), BookModel.version == book.version
        )
        # Execute on the unit of work's connection without another ORM lookup or a commit.
        result = self._session.connection().execute(statement)
        if result.rowcount != 1:
            raise BookVersionConflictError("The book changed or was deleted")
