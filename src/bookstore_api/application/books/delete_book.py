from bookstore_api.application.books.commands import DeleteBookCommand
from bookstore_api.application.books.errors import BookNotFoundError, BookVersionConflictError
from bookstore_api.application.unit_of_work import UnitOfWorkFactory


class DeleteBookService:
    _uow_factory: UnitOfWorkFactory

    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def execute(self, command: DeleteBookCommand) -> int:
        with self._uow_factory() as uow:
            book = uow.books.get_by_id(command.book_id)
            if book is None:
                raise BookNotFoundError(f"Book with id {command.book_id} not found")
            if (
                command.expected_versions is not None
                and book.version not in command.expected_versions
            ):
                raise BookVersionConflictError("The book has changed; retrieve it before deleting")

            version = book.version
            uow.books.delete(book)
            uow.commit()
            return version
