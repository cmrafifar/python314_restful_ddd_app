from bookstore_api.application.books.commands import UpdateBookCommand
from bookstore_api.application.books.errors import BookNotFoundError, BookVersionConflictError
from bookstore_api.application.books.get_book_details import GetBookDetailsResult
from bookstore_api.application.books.ports import BookRepository
from bookstore_api.application.books.transactions import BookTransactions


class UpdateBookService:
    _transactions: BookTransactions

    def __init__(self, transactions: BookTransactions) -> None:
        self._transactions = transactions

    def execute(self, command: UpdateBookCommand) -> GetBookDetailsResult:
        if command.title is None and command.author is None:
            raise ValueError("At least one book detail must be supplied")

        def work(repository: BookRepository) -> GetBookDetailsResult:
            book = repository.get_by_id(command.book_id)
            if book is None:
                raise BookNotFoundError(f"Book with id {command.book_id} not found")
            if (
                command.expected_versions is not None
                and book.version not in command.expected_versions
            ):
                raise BookVersionConflictError("The book has changed; retrieve it before updating")

            book.revise_details(title=command.title, author=command.author)
            version = repository.update(book)
            return GetBookDetailsResult(
                book_id=book.id,
                isbn=book.isbn,
                title=book.title,
                author=book.author,
                version=version,
            )

        return self._transactions.run(work)
