from types import TracebackType
from typing import Protocol, Self

from bookstore_api.application.books.ports import BookRepository


class UnitOfWork(Protocol):
    books: BookRepository

    # Enter context manager
    def __enter__(self) -> Self:
        ...

    # Exit context manager
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        ...

    def commit(self) -> None:
        ...

