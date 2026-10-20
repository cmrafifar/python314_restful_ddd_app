from types import TracebackType
from typing import Self

from bookstore_api.application.books.ports import BookRepository
from bookstore_api.application.unit_of_work import UnitOfWork


class FakeUnitOfWork(UnitOfWork):
    books: BookRepository

    def __init__(self, repository: BookRepository) -> None:
        self.books = repository
        self.committed = False

    def __enter__(self) -> Self:
        return self

    def commit(self) -> None:
        self.committed = True

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        pass
