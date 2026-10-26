from bookstore_api.application.books.commands import DeleteBookCommand
from bookstore_api.application.books.errors import BookNotFoundError, BookVersionConflictError
from bookstore_api.application.books.ports import BookRepository
from bookstore_api.application.books.transactions import BookTransactions


class DeleteBookService:
    _transactions: BookTransactions

    def __init__(self, transactions: BookTransactions) -> None:
        self._transactions = transactions

    def execute(self, command: DeleteBookCommand) -> int:
        def work(repository: BookRepository) -> int:
            book = repository.get_by_id(command.book_id)
            if book is None:
                raise BookNotFoundError(f"Book with id {command.book_id} not found")
            if (
                command.expected_versions is not None
                and book.version not in command.expected_versions
            ):
                raise BookVersionConflictError("The book has changed; retrieve it before deleting")

            version = book.version
            repository.delete(book)
            return version

        return self._transactions.run(work)
