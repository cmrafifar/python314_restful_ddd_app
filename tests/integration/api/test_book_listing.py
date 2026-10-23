from collections.abc import Iterator

import pytest
from dishka import Provider, Scope
from fastapi.testclient import TestClient

from bookstore_api.application.unit_of_work import UnitOfWorkFactory
from bookstore_api.domain.books.book import Book
from bookstore_api.domain.books.isbn import ISBN
from bookstore_api.main import create_app
from tests.fakes.book_repository import FakeBookRepository
from tests.fakes.unit_of_work import FakeUnitOfWork


@pytest.fixture
def repository() -> FakeBookRepository:
    return FakeBookRepository()


@pytest.fixture
def client(repository: FakeBookRepository) -> Iterator[TestClient]:
    def provide_unit_of_work_factory() -> UnitOfWorkFactory:
        return lambda: FakeUnitOfWork(repository)

    overrides = Provider(scope=Scope.APP)
    overrides.provide(provide_unit_of_work_factory, override=True)
    with TestClient(create_app(provider_overrides=[overrides])) as test_client:
        yield test_client


@pytest.fixture
def books(repository: FakeBookRepository) -> list[Book]:
    books = [
        Book.create(ISBN("9780132350884"), "Clean Code", "Robert C. Martin"),
        Book.create(ISBN("9780134494166"), "Clean Architecture", "Robert C. Martin"),
        Book.create(ISBN("9780201616224"), "Café 100%_ Python", "Ada"),
    ]
    books[0].version = 3
    for book in reversed(books):
        repository.add(book)
    return books


def test_empty_collection_returns_200_without_etag(client: TestClient) -> None:
    response = client.get("/api/v1/books")

    assert response.status_code == 200
    assert response.json() == {"items": [], "has_more": False}
    assert "etag" not in response.headers


def test_listing_returns_details_in_isbn_order(client: TestClient, books: list[Book]) -> None:
    response = client.get("/api/v1/books")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": str(book.id),
                "isbn": book.isbn.value,
                "title": book.title,
                "author": book.author,
            }
            for book in books
        ],
        "has_more": False,
    }
    assert "etag" not in response.headers


@pytest.mark.parametrize(
    ("params", "indexes"),
    [
        ({"title": "Code"}, [0]),
        ({"author": "Martin"}, [0, 1]),
        ({"title": "Architecture", "author": "Robert"}, [1]),
        ({"title": "Clean", "author": "Ada"}, []),
        ({"title": "  Clean  ", "author": "  Robert  "}, [0, 1]),
        ({"title": "Unknown"}, []),
        ({"title": "clean"}, []),
        ({"author": "robert"}, []),
        ({"title": "Café"}, [2]),
        ({"title": "Cafe"}, []),
        ({"title": "%"}, [2]),
        ({"title": "_"}, [2]),
        ({"title": "Code", "limit": "1"}, [0]),
    ],
)
def test_listing_filters(
    client: TestClient, books: list[Book], params: dict[str, str], indexes: list[int]
) -> None:
    response = client.get("/api/v1/books", params=params)

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [str(books[i].id) for i in indexes]
    assert response.json()["has_more"] is False


@pytest.mark.parametrize(
    ("limit", "count", "has_more"), [(1, 1, True), (2, 2, True), (3, 3, False), (100, 3, False)]
)
def test_listing_limits_results(
    client: TestClient, books: list[Book], limit: int, count: int, has_more: bool
) -> None:
    response = client.get("/api/v1/books", params={"limit": limit})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [str(b.id) for b in books[:count]]
    assert response.json()["has_more"] is has_more


def test_listing_defaults_to_twenty_results(
    client: TestClient, repository: FakeBookRepository
) -> None:
    for number in range(21):
        prefix = f"978{number:09d}"
        checksum = (-sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(prefix))) % 10
        repository.add(Book.create(ISBN(f"{prefix}{checksum}"), "Title", "Author"))

    response = client.get("/api/v1/books")

    assert response.status_code == 200
    assert len(response.json()["items"]) == 20
    assert response.json()["has_more"] is True


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"limit": "0"}, "limit"),
        ({"limit": "-1"}, "limit"),
        ({"limit": "101"}, "limit"),
        ({"limit": "1.5"}, "limit"),
        ({"limit": "abc"}, "limit"),
        ({"limit": ""}, "limit"),
        ({"title": ""}, "title"),
        ({"title": " \t "}, "title"),
        ({"title": "T" * 101}, "title"),
        ({"author": ""}, "author"),
        ({"author": " \t "}, "author"),
        ({"author": "A" * 81}, "author"),
        ({"unknown": "value"}, "unknown"),
    ],
)
def test_invalid_query_returns_standard_422(
    client: TestClient, params: dict[str, str], field: str
) -> None:
    response = client.get("/api/v1/books", params=params)

    assert response.status_code == 422
    assert any(error["loc"] == ["query", field] for error in response.json()["detail"])


def test_filter_length_boundaries_are_accepted_after_trimming(
    client: TestClient, repository: FakeBookRepository
) -> None:
    book = Book.create(ISBN("9780132350884"), "T" * 100, "A" * 80)
    repository.add(book)

    response = client.get(
        "/api/v1/books", params={"title": f"  {book.title}  ", "author": f"  {book.author}  "}
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [str(book.id)]


def test_openapi_documents_collection_contract(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/api/v1/books"]["get"]
    assert {"200", "422"} <= operation["responses"].keys()
    assert "requestBody" not in operation
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}
    assert parameters.keys() == {"title", "author", "limit"}
    assert all(p["in"] == "query" and not p["required"] for p in parameters.values())
    limit = parameters["limit"]["schema"]
    assert (limit["default"], limit["minimum"], limit["maximum"]) == (20, 1, 100)
    for field, maximum in [("title", 100), ("author", 80)]:
        text_ref = next(s["$ref"] for s in parameters[field]["schema"]["anyOf"] if "$ref" in s)
        text_schema = schema["components"]["schemas"][text_ref.rsplit("/", 1)[-1]]
        assert (text_schema["minLength"], text_schema["maxLength"]) == (1, maximum)
    response = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert response["$ref"] == "#/components/schemas/BookListResponse"
    collection = schema["components"]["schemas"]["BookListResponse"]
    assert set(collection["required"]) == {"items", "has_more"}
    assert collection["properties"]["items"]["items"]["$ref"] == (
        "#/components/schemas/BookDetailsResponse"
    )
    assert collection["properties"]["has_more"]["type"] == "boolean"
