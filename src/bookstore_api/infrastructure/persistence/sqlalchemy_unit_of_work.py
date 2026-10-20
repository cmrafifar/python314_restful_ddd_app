from types import TracebackType
from typing import Self

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from bookstore_api.application.books.create_book import (
    BookAlreadyExistsError,
)
from bookstore_api.application.books.ports import BookRepository
from bookstore_api.application.unit_of_work import UnitOfWork
from bookstore_api.infrastructure.persistence.repositories.sqlalchemy_book_repository import (
    SqlAlchemyBookRepository,
)


class SqlAlchemyUnitOfWork(UnitOfWork):
    books: BookRepository

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None

    def __enter__(self) -> Self:
        if self._session is not None:
            raise RuntimeError("Unit of Work is already active")

        session = self._session_factory()
        self._session = session
        self.books = SqlAlchemyBookRepository(session)

        return self

    def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of Work is not active")

        try:
            self._session.commit()
        except IntegrityError as exc:
            original = exc.orig
            args = getattr(original, "args", ())

            error_code = args[0] if args else None
            error_message = str(original)

            if error_code == 1062 and "uq_books_isbn" in error_message:
                raise BookAlreadyExistsError("Book with this ISBN already exists") from exc

            raise

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        session = self._session

        if session is None:
            return

        try:
            # Any uncommitted transaction is rolled back.
            if session.in_transaction():
                session.rollback()
        finally:
            session.close()
            self._session = None
