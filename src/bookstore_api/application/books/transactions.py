from collections.abc import Callable
from typing import Protocol

from bookstore_api.application.books.ports import BookRepository

type BookTransactionWork[T] = Callable[[BookRepository], T]


class BookTransactions(Protocol):
    def run[T](self, work: BookTransactionWork[T]) -> T:
        """Run work with one repository; commit on success, roll back on failure.

        Return the callback result only after commit succeeds. Supply a fresh
        transaction for every call; the repository must not escape the callback.
        """
        ...
