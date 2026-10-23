import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session, sessionmaker

from bookstore_api.application.books.list_books import ListBooksQuery, ListBooksService
from bookstore_api.domain.books.book import Book
from bookstore_api.domain.books.isbn import ISBN
from bookstore_api.infrastructure.persistence.models.book import BookModel
from bookstore_api.infrastructure.persistence.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
def empty_catalog(session_factory: sessionmaker[Session]) -> ListBooksService:
    # The shared fixture's outer transaction restores existing rows after every test.
    with session_factory() as session:
        session.execute(delete(BookModel))
        session.commit()
    return ListBooksService(lambda: SqlAlchemyUnitOfWork(session_factory))


@pytest.fixture
def books(empty_catalog: ListBooksService, session_factory: sessionmaker[Session]) -> list[Book]:
    books = [
        Book.create(ISBN("9780132350884"), "Clean Code", "Robert C. Martin"),
        Book.create(ISBN("9780134494166"), "Clean Architecture", "Robert C. Martin"),
        Book.create(ISBN("9780201616224"), "Café 100%_ Python / Paths\\Guide", "Áda %_ / \\"),
    ]
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        for book in reversed(books):
            uow.books.add(book)
        uow.commit()
    return books


def test_empty_collection(empty_catalog: ListBooksService) -> None:
    result = empty_catalog.execute(ListBooksQuery())

    assert result.items == ()
    assert result.has_more is False


def test_listing_maps_persisted_details_in_isbn_order(
    empty_catalog: ListBooksService, books: list[Book]
) -> None:
    result = empty_catalog.execute(ListBooksQuery())

    assert [item.book_id for item in result.items] == [book.id for book in books]
    for item, book in zip(result.items, books, strict=True):
        assert (item.isbn, item.title, item.author, item.version) == (
            book.isbn,
            book.title,
            book.author,
            book.version,
        )
    assert result.has_more is False


@pytest.mark.parametrize(
    ("query", "indexes"),
    [
        (ListBooksQuery(title="Code"), [0]),
        (ListBooksQuery(author="Martin"), [0, 1]),
        (ListBooksQuery(title="Architecture", author="Robert"), [1]),
        (ListBooksQuery(title="Clean", author="Ada"), []),
        (ListBooksQuery(title="  Clean  ", author="  Robert  "), [0, 1]),
        (ListBooksQuery(title="Unknown"), []),
        (ListBooksQuery(title="clean"), []),
        (ListBooksQuery(author="robert"), []),
        (ListBooksQuery(title="Café"), [2]),
        (ListBooksQuery(title="Cafe"), []),
        (ListBooksQuery(author="Áda"), [2]),
        (ListBooksQuery(author="Ada"), []),
        (ListBooksQuery(title="%"), [2]),
        (ListBooksQuery(title="_"), [2]),
        (ListBooksQuery(title="/"), [2]),
        (ListBooksQuery(title="\\"), [2]),
        (ListBooksQuery(author="%"), [2]),
        (ListBooksQuery(author="_"), [2]),
        (ListBooksQuery(author="/"), [2]),
        (ListBooksQuery(author="\\"), [2]),
        (ListBooksQuery(title="Code", limit=1), [0]),
        (ListBooksQuery(title="Architecture", limit=1), [1]),
    ],
)
def test_mysql_literal_filter_semantics(
    empty_catalog: ListBooksService, books: list[Book], query: ListBooksQuery, indexes: list[int]
) -> None:
    result = empty_catalog.execute(query)

    assert [item.book_id for item in result.items] == [books[i].id for i in indexes]
    assert result.has_more is False


@pytest.mark.parametrize(
    ("limit", "count", "has_more"), [(1, 1, True), (2, 2, True), (3, 3, False), (100, 3, False)]
)
def test_mysql_listing_bounds(
    empty_catalog: ListBooksService, books: list[Book], limit: int, count: int, has_more: bool
) -> None:
    result = empty_catalog.execute(ListBooksQuery(limit=limit))

    assert [item.book_id for item in result.items] == [book.id for book in books[:count]]
    assert result.has_more is has_more


def test_repository_bounds_results_before_service_slicing(
    session_factory: sessionmaker[Session], books: list[Book]
) -> None:
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        result = uow.books.list_books(title=None, author=None, limit=2)

    assert [book.id for book in result] == [book.id for book in books[:2]]


def test_mysql_maximum_limit_and_lookahead(
    empty_catalog: ListBooksService, session_factory: sessionmaker[Session]
) -> None:
    books: list[Book] = []
    for number in range(101):
        prefix = f"978{number:09d}"
        checksum = (-sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(prefix))) % 10
        books.append(Book.create(ISBN(f"{prefix}{checksum}"), "Title", "Author"))
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        for book in reversed(books):
            uow.books.add(book)
        uow.commit()

    result = empty_catalog.execute(ListBooksQuery(limit=100))

    assert [item.book_id for item in result.items] == [book.id for book in books[:100]]
    assert result.has_more is True
