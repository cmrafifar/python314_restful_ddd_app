import base64
import json
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
    assert response.json() == {
        "items": [],
        "has_more": False,
        "next_cursor": None,
        "previous_cursor": None,
    }
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
        "next_cursor": None,
        "previous_cursor": None,
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
    assert parameters.keys() == {"title", "author", "limit", "cursor"}
    assert all(p["in"] == "query" and not p["required"] for p in parameters.values())
    limit = parameters["limit"]["schema"]
    assert (limit["default"], limit["minimum"], limit["maximum"]) == (20, 1, 100)
    response = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert response["$ref"] == "#/components/schemas/BookListResponse"
    collection = schema["components"]["schemas"]["BookListResponse"]
    assert set(collection["required"]) == {"items", "has_more", "next_cursor", "previous_cursor"}
    assert collection["properties"]["items"]["items"]["$ref"] == (
        "#/components/schemas/BookDetailsResponse"
    )
    assert collection["properties"]["has_more"]["type"] == "boolean"


def encoded_cursor(payload: object) -> str:
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")


def test_http_navigation_round_trip(client: TestClient, books: list[Book]) -> None:
    first = client.get("/api/v1/books", params={"limit": 1}).json()
    assert first["previous_cursor"] is None
    assert first["next_cursor"] is not None
    middle_response = client.get(
        "/api/v1/books", params={"limit": 1, "cursor": first["next_cursor"]}
    )
    assert middle_response.status_code == 200
    middle = middle_response.json()
    assert [item["id"] for item in middle["items"]] == [str(books[1].id)]
    assert middle["has_more"] is True
    assert middle["next_cursor"] is not None
    assert middle["previous_cursor"] is not None
    for field, isbn, direction in [
        ("previous_cursor", books[1].isbn.value, "previous"),
        ("next_cursor", books[1].isbn.value, "next"),
    ]:
        token = middle[field]
        decoded = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
        assert json.loads(decoded) == {"v": 1, "isbn": isbn, "direction": direction}

    last = client.get("/api/v1/books", params={"limit": 1, "cursor": middle["next_cursor"]}).json()
    assert [item["id"] for item in last["items"]] == [str(books[2].id)]
    assert last["has_more"] is False
    assert last["next_cursor"] is None
    back = client.get(
        "/api/v1/books", params={"limit": 1, "cursor": middle["previous_cursor"]}
    ).json()
    assert back == first


def test_http_previous_page_preserves_filters_and_accepts_new_limit(
    client: TestClient, books: list[Book]
) -> None:
    first = client.get("/api/v1/books", params={"limit": 1, "title": "Clean"}).json()
    second = client.get(
        "/api/v1/books", params={"limit": 1, "title": "Clean", "cursor": first["next_cursor"]}
    ).json()

    response = client.get(
        "/api/v1/books", params={"limit": 2, "title": "Clean", "cursor": second["previous_cursor"]}
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [str(books[0].id)]
    assert response.json()["previous_cursor"] is None
    assert response.json()["has_more"] is True


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {},
        {"v": 1, "isbn": "9780132350884"},
        {"v": 2, "isbn": "9780132350884", "direction": "next"},
        {"v": True, "isbn": "9780132350884", "direction": "next"},
        {"v": 1.0, "isbn": "9780132350884", "direction": "next"},
        {"v": "1", "isbn": "9780132350884", "direction": "next"},
        {"v": 1, "isbn": "9780132350884", "direction": "back"},
        {"v": 1, "isbn": "9780132350884", "direction": None},
        {"v": 1, "isbn": 9780132350884, "direction": "next"},
        {"v": 1, "isbn": "9780132350885", "direction": "next"},
        {"v": 1, "isbn": "invalid", "direction": "next"},
        {"v": 1, "isbn": "9780132350884", "direction": "next", "page": 2},
    ],
)
def test_invalid_cursor_payload_returns_422(client: TestClient, payload: object) -> None:
    response = client.get("/api/v1/books", params={"cursor": encoded_cursor(payload)})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "cursor"]


@pytest.mark.parametrize("token", ["", "!", "a", "+/8=", "_w", "ew", "A" * 513])
def test_invalid_cursor_encoding_returns_422(client: TestClient, token: str) -> None:
    response = client.get("/api/v1/books", params={"cursor": token})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "cursor"]


@pytest.mark.parametrize("direction,index", [("next", 2), ("previous", 0)])
def test_empty_continuation_returns_null_cursors(
    client: TestClient, books: list[Book], direction: str, index: int
) -> None:
    token = encoded_cursor({"v": 1, "isbn": books[index].isbn.value, "direction": direction})

    response = client.get("/api/v1/books", params={"cursor": token})

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "has_more": False,
        "next_cursor": None,
        "previous_cursor": None,
    }
