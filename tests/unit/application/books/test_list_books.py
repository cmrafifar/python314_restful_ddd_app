import pytest

from bookstore_api.application.books.list_books import ListBooksQuery, ListBooksService
from bookstore_api.application.unit_of_work import UnitOfWork
from bookstore_api.domain.books.book import Book
from bookstore_api.domain.books.isbn import ISBN
from tests.fakes.book_repository import FakeBookRepository
from tests.fakes.unit_of_work import FakeUnitOfWork


@pytest.fixture
def catalog() -> tuple[ListBooksService, FakeUnitOfWork, list[Book]]:
    books = [
        Book.create(ISBN("9780132350884"), "Clean Code", "Robert C. Martin"),
        Book.create(ISBN("9780134494166"), "Clean Architecture", "Robert C. Martin"),
        Book.create(ISBN("9780201616224"), "Café 100%_ Python", "Ada"),
    ]
    books[0].version = 3
    repository = FakeBookRepository()
    for book in reversed(books):
        repository.add(book)
    uow = FakeUnitOfWork(repository)
    return ListBooksService(lambda: uow), uow, books


def test_list_books_returns_empty_collection_without_committing() -> None:
    uow = FakeUnitOfWork(FakeBookRepository())
    service = ListBooksService(lambda: uow)

    result = service.execute(ListBooksQuery())

    assert result.items == ()
    assert result.has_more is False
    assert uow.committed is False


def test_list_books_returns_details_ordered_by_isbn_without_committing(
    catalog: tuple[ListBooksService, FakeUnitOfWork, list[Book]],
) -> None:
    service, uow, books = catalog

    result = service.execute(ListBooksQuery())

    assert [item.book_id for item in result.items] == [book.id for book in books]
    for item, book in zip(result.items, books, strict=True):
        assert item.isbn == book.isbn
        assert item.title == book.title
        assert item.author == book.author
        assert item.version == book.version
    assert result.has_more is False
    assert uow.committed is False


@pytest.mark.parametrize(
    ("query", "expected_indexes"),
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
        (ListBooksQuery(title="%"), [2]),
        (ListBooksQuery(title="_"), [2]),
    ],
    # ids is a pytest attribute used to name the test.
    ids=[
        "title-substring",
        "author-substring",
        "combined-filters",
        "filters-use-and",
        "trim-filters",
        "no-matches",
        "title-case-sensitive",
        "author-case-sensitive",
        "accent-match",
        "accent-sensitive",
        "literal-percent",
        "literal-underscore",
    ],
)
def test_list_books_filters_results(
    catalog: tuple[ListBooksService, FakeUnitOfWork, list[Book]],
    query: ListBooksQuery,
    expected_indexes: list[int],
) -> None:
    service, uow, books = catalog

    result = service.execute(query)

    assert [item.book_id for item in result.items] == [books[i].id for i in expected_indexes]
    assert result.has_more is False
    assert uow.committed is False


@pytest.mark.parametrize(
    ("limit", "expected_count", "has_more"),
    [(1, 1, True), (2, 2, True), (3, 3, False), (100, 3, False)],
)
def test_list_books_caps_results_and_reports_more_matches(
    catalog: tuple[ListBooksService, FakeUnitOfWork, list[Book]],
    limit: int,
    expected_count: int,
    has_more: bool,
) -> None:
    service, uow, books = catalog

    result = service.execute(ListBooksQuery(limit=limit))

    assert [item.book_id for item in result.items] == [book.id for book in books[:expected_count]]
    assert result.has_more is has_more
    assert uow.committed is False


def test_list_books_calculates_has_more_from_filtered_matches(
    catalog: tuple[ListBooksService, FakeUnitOfWork, list[Book]],
) -> None:
    service, uow, books = catalog

    result = service.execute(ListBooksQuery(title="Code", limit=1))

    assert [item.book_id for item in result.items] == [books[0].id]
    assert result.has_more is False
    assert uow.committed is False


@pytest.mark.parametrize(
    ("query", "message"),
    [
        (ListBooksQuery(limit=0), "Limit"),
        (ListBooksQuery(limit=-1), "Limit"),
        (ListBooksQuery(limit=101), "Limit"),
        (ListBooksQuery(title=""), "Title filter cannot be empty"),
        (ListBooksQuery(title=" \t "), "Title filter cannot be empty"),
        (ListBooksQuery(author=""), "Author filter cannot be empty"),
        (ListBooksQuery(author=" \t "), "Author filter cannot be empty"),
        (ListBooksQuery(title="T" * 101), "Title filter cannot exceed 100"),
        (ListBooksQuery(author="A" * 81), "Author filter cannot exceed 80"),
    ],
)
def test_list_books_rejects_invalid_query_before_opening_unit_of_work(
    query: ListBooksQuery, message: str
) -> None:
    def unexpected_unit_of_work() -> UnitOfWork:
        raise AssertionError("Invalid queries must not open a unit of work")

    service = ListBooksService(unexpected_unit_of_work)

    with pytest.raises(ValueError, match=message):
        service.execute(query)


def test_list_books_accepts_filter_length_boundaries_after_trimming() -> None:
    repository = FakeBookRepository()
    book = Book.create(ISBN("9780132350884"), "T" * 100, "A" * 80)
    repository.add(book)
    uow = FakeUnitOfWork(repository)
    service = ListBooksService(lambda: uow)

    result = service.execute(ListBooksQuery(title=f"  {book.title}  ", author=f"  {book.author}  "))

    assert [item.book_id for item in result.items] == [book.id]
    assert result.has_more is False
    assert uow.committed is False
