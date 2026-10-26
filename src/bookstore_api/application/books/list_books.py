from dataclasses import dataclass

from bookstore_api.application.books.get_book_details import GetBookDetailsResult
from bookstore_api.application.books.pagination import BookPageCursor
from bookstore_api.application.books.ports import BookRepository
from bookstore_api.application.books.transactions import BookTransactions
from bookstore_api.domain.books.book import MAX_AUTHOR_LENGTH, MAX_TITLE_LENGTH

MAX_LIST_LIMIT = 100


@dataclass(frozen=True, slots=True)
class ListBooksQuery:
    title: str | None = None
    author: str | None = None
    limit: int = 20
    cursor: BookPageCursor | None = None


@dataclass(frozen=True, slots=True)
class ListBooksResult:
    items: tuple[GetBookDetailsResult, ...]
    has_more: bool
    next_cursor: BookPageCursor | None = None
    previous_cursor: BookPageCursor | None = None


class ListBooksService:
    def __init__(self, transactions: BookTransactions) -> None:
        self._transactions = transactions

    def execute(self, query: ListBooksQuery) -> ListBooksResult:
        if not 1 <= query.limit <= MAX_LIST_LIMIT:
            raise ValueError(f"Limit must be between 1 and {MAX_LIST_LIMIT}")

        title = _normalize_filter(query.title, "Title", MAX_TITLE_LENGTH)
        author = _normalize_filter(query.author, "Author", MAX_AUTHOR_LENGTH)

        def work(repository: BookRepository) -> ListBooksResult:
            books = repository.list_books(
                title=title, author=author, limit=query.limit + 1, cursor=query.cursor
            )
            has_extra = len(books) > query.limit
            page = books[: query.limit]
            if not page:
                return ListBooksResult(items=(), has_more=False)

            backward = query.cursor is not None and query.cursor.direction == "previous"
            if backward:
                page.reverse()

            next_cursor = BookPageCursor(page[-1].isbn, "next")
            previous_cursor = BookPageCursor(page[0].isbn, "previous")
            if backward:
                has_previous = has_extra
                has_next = repository.has_books(title=title, author=author, cursor=next_cursor)
            else:
                has_next = has_extra
                has_previous = query.cursor is not None and repository.has_books(
                    title=title, author=author, cursor=previous_cursor
                )

            return ListBooksResult(
                items=tuple(
                    GetBookDetailsResult(
                        book_id=book.id,
                        isbn=book.isbn,
                        title=book.title,
                        author=book.author,
                        version=book.version,
                    )
                    for book in page
                ),
                has_more=has_next,
                next_cursor=next_cursor if has_next else None,
                previous_cursor=previous_cursor if has_previous else None,
            )

        return self._transactions.run(work)


def _normalize_filter(value: str | None, field: str, max_length: int) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field} filter cannot be empty")
    if len(normalized) > max_length:
        raise ValueError(f"{field} filter cannot exceed {max_length} characters")
    return normalized
