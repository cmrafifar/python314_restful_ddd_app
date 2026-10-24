from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from bookstore_api.application.books.list_books import ListBooksQuery, ListBooksService
from bookstore_api.application.books.pagination import BookPageCursor
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


@pytest.mark.parametrize("direction", ["next", "previous"])
def test_repository_seeks_in_both_directions(
    session_factory: sessionmaker[Session], books: list[Book], direction: str
) -> None:
    cursor = BookPageCursor(books[1].isbn, "next" if direction == "next" else "previous")
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        found = uow.books.list_books(title=None, author=None, cursor=cursor, limit=1)
        exists = uow.books.has_books(title=None, author=None, cursor=cursor)

    assert [book.id for book in found] == [books[2 if direction == "next" else 0].id]
    assert exists is True


def test_mysql_previous_page_trims_lookahead_before_reversing(
    empty_catalog: ListBooksService, books: list[Book]
) -> None:
    result = empty_catalog.execute(
        ListBooksQuery(cursor=BookPageCursor(ISBN("9791234567896"), "previous"), limit=2)
    )

    assert [item.book_id for item in result.items] == [book.id for book in books[1:]]
    assert result.previous_cursor == BookPageCursor(books[1].isbn, "previous")
    assert result.next_cursor is None
    assert result.has_more is False


@pytest.mark.parametrize("title", ["Clean", "clean", "%", "Cafe", "Café"])
def test_mysql_navigation_and_existence_share_filter_semantics(
    empty_catalog: ListBooksService,
    session_factory: sessionmaker[Session],
    books: list[Book],
    title: str,
) -> None:
    cursor = BookPageCursor(books[1].isbn, "next")
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        found = uow.books.list_books(title=title, author=None, cursor=cursor, limit=1)
        exists = uow.books.has_books(title=title, author=None, cursor=cursor)

    expected = [books[2]] if title in ("%", "Café") else []
    assert [book.id for book in found] == [book.id for book in expected]
    assert exists is bool(expected)


def make_catalog_book(prefix: int, author: str, title: str = "Original") -> Book:
    digits = str(prefix)
    checksum = (-sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits))) % 10
    return Book.create(ISBN(f"{digits}{checksum}"), title, author)


@pytest.fixture
def committed_catalog(mysql_engine: Engine) -> Iterator[tuple[ListBooksService, list[Book]]]:
    """Use durable rows and a unique filter for independent connections between pages."""
    author = uuid4().hex
    prefix = int(f"978{uuid4().int % 900_000_000:09d}")
    books = [make_catalog_book(prefix + i, author) for i in (10, 30, 50, 70, 90)]
    factory = sessionmaker(bind=mysql_engine, autoflush=False, expire_on_commit=False)
    try:
        with SqlAlchemyUnitOfWork(factory) as uow:
            for book in reversed(books):
                uow.books.add(book)
            uow.commit()
        yield ListBooksService(lambda: SqlAlchemyUnitOfWork(factory)), books
    finally:
        with mysql_engine.begin() as connection:
            connection.execute(
                delete(BookModel).where(BookModel.id.in_([str(b.id) for b in books]))
            )


def test_mysql_pages_round_trip_on_independent_connections(
    committed_catalog: tuple[ListBooksService, list[Book]],
) -> None:
    service, books = committed_catalog
    first = service.execute(ListBooksQuery(author=books[0].author, limit=2))
    assert first.previous_cursor is None
    assert first.next_cursor is not None
    middle = service.execute(
        ListBooksQuery(author=books[0].author, limit=2, cursor=first.next_cursor)
    )
    assert middle.next_cursor is not None
    assert middle.previous_cursor is not None
    last = service.execute(
        ListBooksQuery(author=books[0].author, limit=2, cursor=middle.next_cursor)
    )
    assert [item.book_id for item in last.items] == [books[-1].id]
    assert last.next_cursor is None
    assert last.previous_cursor is not None

    back = service.execute(
        ListBooksQuery(author=books[0].author, limit=2, cursor=last.previous_cursor)
    )

    assert back.items == middle.items
    assert back.has_more is True
    assert back.next_cursor == middle.next_cursor
    assert back.previous_cursor == middle.previous_cursor


@pytest.mark.parametrize("direction", ["next", "previous"])
def test_mysql_deleted_anchor_does_not_invalidate_cursor(
    mysql_engine: Engine, committed_catalog: tuple[ListBooksService, list[Book]], direction: str
) -> None:
    service, books = committed_catalog
    cursor = BookPageCursor(books[2].isbn, "next" if direction == "next" else "previous")
    factory = sessionmaker(bind=mysql_engine, autoflush=False, expire_on_commit=False)
    with SqlAlchemyUnitOfWork(factory) as writer:
        writer.books.delete(books[2])
        writer.commit()

    result = service.execute(ListBooksQuery(author=books[0].author, limit=2, cursor=cursor))

    expected = books[3:] if direction == "next" else books[:2]
    assert [item.book_id for item in result.items] == [book.id for book in expected]
    assert result.has_more is (direction == "previous")


def test_mysql_inserts_on_either_side_do_not_shift_forward_boundary(
    mysql_engine: Engine, committed_catalog: tuple[ListBooksService, list[Book]]
) -> None:
    service, books = committed_catalog
    first = service.execute(ListBooksQuery(author=books[0].author, limit=2))
    assert first.next_cursor is not None
    boundary = int(books[1].isbn.value[:12])
    inserted = [
        make_catalog_book(boundary - 10, books[0].author),
        make_catalog_book(boundary + 10, books[0].author),
    ]
    # Include inserted rows in the fixture's cleanup even if an assertion fails.
    books.extend(inserted)
    factory = sessionmaker(bind=mysql_engine, autoflush=False, expire_on_commit=False)
    with SqlAlchemyUnitOfWork(factory) as writer:
        for book in inserted:
            writer.books.add(book)
        writer.commit()

    result = service.execute(
        ListBooksQuery(author=books[0].author, limit=2, cursor=first.next_cursor)
    )

    assert [item.book_id for item in result.items] == [inserted[1].id, books[2].id]
    assert result.has_more is True
    restarted = service.execute(ListBooksQuery(author=books[0].author, limit=2))
    assert [item.book_id for item in restarted.items] == [books[0].id, inserted[0].id]


def test_mysql_filter_edits_change_membership_without_moving_boundary(
    mysql_engine: Engine, committed_catalog: tuple[ListBooksService, list[Book]]
) -> None:
    service, books = committed_catalog
    first = service.execute(ListBooksQuery(author=books[0].author, title="Original", limit=2))
    assert first.next_cursor is not None
    factory = sessionmaker(bind=mysql_engine, autoflush=False, expire_on_commit=False)
    with SqlAlchemyUnitOfWork(factory) as writer:
        books[2].revise_details(title="Excluded")
        writer.books.update(books[2])
        writer.commit()

    result = service.execute(
        ListBooksQuery(author=books[0].author, title="Original", limit=2, cursor=first.next_cursor)
    )

    assert [item.book_id for item in result.items] == [book.id for book in books[3:]]
    assert result.next_cursor is None
    assert result.previous_cursor is not None


def test_mysql_removed_earlier_rows_remove_previous_cursor(
    mysql_engine: Engine, committed_catalog: tuple[ListBooksService, list[Book]]
) -> None:
    service, books = committed_catalog
    first = service.execute(ListBooksQuery(author=books[0].author, limit=2))
    assert first.next_cursor is not None
    factory = sessionmaker(bind=mysql_engine, autoflush=False, expire_on_commit=False)
    with SqlAlchemyUnitOfWork(factory) as writer:
        for book in books[:2]:
            writer.books.delete(book)
        writer.commit()

    result = service.execute(
        ListBooksQuery(author=books[0].author, limit=2, cursor=first.next_cursor)
    )

    assert [item.book_id for item in result.items] == [book.id for book in books[2:4]]
    assert result.previous_cursor is None
    assert result.next_cursor is not None
