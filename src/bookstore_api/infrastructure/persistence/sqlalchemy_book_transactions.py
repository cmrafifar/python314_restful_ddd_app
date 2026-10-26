from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from bookstore_api.application.books.create_book import BookAlreadyExistsError
from bookstore_api.application.books.transactions import BookTransactionWork
from bookstore_api.infrastructure.persistence.repositories.sqlalchemy_book_repository import (
    SqlAlchemyBookRepository,
)


class SqlAlchemyBookTransactions:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def run[T](self, work: BookTransactionWork[T]) -> T:
        try:
            with self._session_factory.begin() as session:
                result = work(SqlAlchemyBookRepository(session))
            return result
        except IntegrityError as exc:
            original = exc.orig
            args = getattr(original, "args", ())

            error_code = args[0] if args else None
            error_message = str(original)

            if error_code == 1062 and "uq_books_isbn" in error_message:
                raise BookAlreadyExistsError("Book with this ISBN already exists") from exc

            raise
