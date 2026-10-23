from dataclasses import dataclass

from bookstore_api.application.books.get_book_details import GetBookDetailsResult
from bookstore_api.application.unit_of_work import UnitOfWorkFactory
from bookstore_api.domain.books.book import MAX_AUTHOR_LENGTH, MAX_TITLE_LENGTH

MAX_LIST_LIMIT = 100


@dataclass(frozen=True, slots=True)
class ListBooksQuery:
    title: str | None = None
    author: str | None = None
    limit: int = 20


@dataclass(frozen=True, slots=True)
class ListBooksResult:
    items: tuple[GetBookDetailsResult, ...]
    has_more: bool


class ListBooksService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def execute(self, query: ListBooksQuery) -> ListBooksResult:
        if not 1 <= query.limit <= MAX_LIST_LIMIT:
            raise ValueError(f"Limit must be between 1 and {MAX_LIST_LIMIT}")

        title = _normalize_filter(query.title, "Title", MAX_TITLE_LENGTH)
        author = _normalize_filter(query.author, "Author", MAX_AUTHOR_LENGTH)

        with self._uow_factory() as uow:
            books = uow.books.list_books(title=title, author=author, limit=query.limit + 1)
            return ListBooksResult(
                items=tuple(
                    GetBookDetailsResult(
                        book_id=book.id,
                        isbn=book.isbn,
                        title=book.title,
                        author=book.author,
                        version=book.version,
                    )
                    for book in books[: query.limit]
                ),
                has_more=len(books) > query.limit,
            )


def _normalize_filter(value: str | None, field: str, max_length: int) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field} filter cannot be empty")
    if len(normalized) > max_length:
        raise ValueError(f"{field} filter cannot exceed {max_length} characters")
    return normalized
