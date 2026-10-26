from dataclasses import dataclass
from uuid import UUID

from bookstore_api.application.books.commands import CreateBookCommand
from bookstore_api.application.books.ports import BookRepository
from bookstore_api.application.books.transactions import BookTransactions
from bookstore_api.domain.books.book import Book
from bookstore_api.domain.books.isbn import ISBN


class BookAlreadyExistsError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class CreateBookResult:
    book_id: UUID


class CreateBookService:
    def __init__(
        self,
        transactions: BookTransactions,
    ) -> None:
        self._transactions = transactions

    def execute(self, command: CreateBookCommand) -> CreateBookResult:
        isbn = ISBN(command.isbn)

        def work(repository: BookRepository) -> CreateBookResult:
            existing = repository.get_by_isbn(isbn)

            if existing is not None:
                raise BookAlreadyExistsError(f"Book with ISBN {isbn.value} already exists")

            book = Book.create(
                isbn=isbn,
                title=command.title,
                author=command.author,
            )

            repository.add(book)

            return CreateBookResult(book_id=book.id)

        return self._transactions.run(work)
