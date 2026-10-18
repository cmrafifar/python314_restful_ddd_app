
from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker

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

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        if self._session is not None:
            raise RuntimeError("Unit of Work is already active")

        session = self._session_factory()
        self._session = session
        self.books = SqlAlchemyBookRepository(session)

        return self

    def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of Work is not active")

        self._session.commit()

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

