from bookstore_api.application.books.commands import UpdateBookCommand
from bookstore_api.application.books.errors import BookNotFoundError, BookVersionConflictError
from bookstore_api.application.books.get_book_details import GetBookDetailsResult
from bookstore_api.application.unit_of_work import UnitOfWorkFactory


class UpdateBookService:
    _uow_factory: UnitOfWorkFactory

    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def execute(self, command: UpdateBookCommand) -> GetBookDetailsResult:
        if command.title is None and command.author is None:
            raise ValueError("At least one book detail must be supplied")

        with self._uow_factory() as uow:
            book = uow.books.get_by_id(command.book_id)
            if book is None:
                raise BookNotFoundError(f"Book with id {command.book_id} not found")
            if (
                command.expected_versions is not None
                and book.version not in command.expected_versions
            ):
                raise BookVersionConflictError("The book has changed; retrieve it before updating")

            book.revise_details(title=command.title, author=command.author)
            version = uow.books.update(book)
            uow.commit()
            return GetBookDetailsResult(
                book_id=book.id,
                isbn=book.isbn,
                title=book.title,
                author=book.author,
                version=version,
            )
