from collections.abc import Iterator
from uuid import uuid4

import pytest
from dishka import Provider, Scope
from fastapi.testclient import TestClient

from bookstore_api.api.books.conditional_requests import book_etag
from bookstore_api.application.unit_of_work import UnitOfWorkFactory
from bookstore_api.domain.books.book import Book
from bookstore_api.domain.books.isbn import ISBN
from bookstore_api.main import create_app
from tests.fakes.book_repository import FakeBookRepository
from tests.fakes.unit_of_work import FakeUnitOfWork


@pytest.fixture
def book() -> Book:
    return Book.create(ISBN("9780132350884"), "Original", "Original author")


@pytest.fixture
def client(book: Book) -> Iterator[TestClient]:
    repository = FakeBookRepository()
    repository.add(book)

    def provide_unit_of_work_factory() -> UnitOfWorkFactory:
        return lambda: FakeUnitOfWork(repository)

    overrides = Provider(scope=Scope.APP)
    overrides.provide(provide_unit_of_work_factory, override=True)
    with TestClient(create_app(provider_overrides=[overrides])) as test_client:
        yield test_client


def test_patch_preserves_omitted_fields_and_changes_etag(client: TestClient, book: Book) -> None:
    url = f"/api/v1/books/{book.id}"
    before = client.get(url)
    etag = before.headers["etag"]

    response = client.patch(url, json={"title": " Updated "}, headers={"If-Match": etag})

    assert response.status_code == 200
    assert response.json() == {
        "id": str(book.id),
        "isbn": book.isbn.value,
        "title": "Updated",
        "author": "Original author",
    }
    assert response.headers["etag"] != etag
    retrieved = client.get(url)
    assert retrieved.json() == response.json()
    assert retrieved.headers["etag"] == response.headers["etag"]


def test_put_replaces_both_writable_fields(client: TestClient, book: Book) -> None:
    url = f"/api/v1/books/{book.id}"
    etag = client.get(url).headers["etag"]

    response = client.put(
        url, json={"title": " New ", "author": " New author "}, headers={"If-Match": etag}
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(book.id),
        "isbn": book.isbn.value,
        "title": "New",
        "author": "New author",
    }
    # PUT normalizes input, so its response does not assert a validator for the submitted bytes.
    assert "etag" not in response.headers
    retrieved = client.get(url)
    assert retrieved.json() == response.json()
    assert retrieved.headers["etag"] != etag


@pytest.mark.parametrize("method", ["put", "patch"])
def test_stale_client_cannot_overwrite_a_newer_write(
    client: TestClient, book: Book, method: str
) -> None:
    url = f"/api/v1/books/{book.id}"
    etag = client.get(url).headers["etag"]
    first = client.patch(url, json={"author": "Corrected author"}, headers={"If-Match": etag})
    assert first.status_code == 200

    stale = client.request(
        method,
        url,
        json={"title": "Stale title", "author": "Old author"},
        headers={"If-Match": etag},
    )

    assert stale.status_code == 412
    assert stale.json()["detail"]["code"] == "precondition_failed"
    assert client.get(url).json()["author"] == "Corrected author"
    assert client.get(url).json()["title"] == "Original"


@pytest.mark.parametrize("method", ["put", "patch"])
@pytest.mark.parametrize(
    "value,expected", [(None, 428), ("unquoted", 400), ('W/"unknown"', 412), ('"unknown"', 412)]
)
def test_update_requires_a_matching_strong_validator(
    client: TestClient, book: Book, method: str, value: str | None, expected: int
) -> None:
    url = f"/api/v1/books/{book.id}"
    headers = {} if value is None else {"If-Match": value}

    response = client.request(
        method, url, json={"title": "New", "author": "New author"}, headers=headers
    )

    assert response.status_code == expected
    if expected == 428:
        assert response.headers["cache-control"] == "no-store"
    assert client.get(url).json()["title"] == "Original"


@pytest.mark.parametrize("method", ["put", "patch"])
def test_updates_do_not_create_missing_books(client: TestClient, method: str) -> None:
    missing_id = uuid4()
    response = client.request(
        method,
        f"/api/v1/books/{missing_id}",
        json={"title": "New", "author": "Author"},
        headers={"If-Match": book_etag(missing_id, 1)},
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": None},
        {"author": None},
        {"title": " "},
        {"title": "t" * 101},
        {"author": "a" * 81},
        {"isbn": "9780321125217"},
        {"id": "anything"},
    ],
)
def test_patch_rejects_invalid_changes(
    client: TestClient, book: Book, payload: dict[str, object]
) -> None:
    response = client.patch(
        f"/api/v1/books/{book.id}", json=payload, headers={"If-Match": book_etag(book.id, 1)}
    )
    assert response.status_code == 422


def test_put_requires_both_fields(client: TestClient, book: Book) -> None:
    response = client.put(
        f"/api/v1/books/{book.id}",
        json={"title": "Only title"},
        headers={"If-Match": book_etag(book.id, 1)},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "author"]


@pytest.mark.parametrize("method", ["post", "put", "patch"])
def test_http_accepts_exact_text_limits(client: TestClient, book: Book, method: str) -> None:
    payload = {"title": "t" * 100, "author": "a" * 80}
    url = "/api/v1/books" if method == "post" else f"/api/v1/books/{book.id}"
    if method == "post":
        payload["isbn"] = "9780321125217"
    response = client.request(
        method, url, json=payload, headers={"If-Match": book_etag(book.id, 1)}
    )
    assert response.status_code == (201 if method == "post" else 200)


@pytest.mark.parametrize("method", ["post", "put"])
@pytest.mark.parametrize("field,limit", [("title", 100), ("author", 80)])
def test_http_rejects_text_beyond_limits(
    client: TestClient, book: Book, method: str, field: str, limit: int
) -> None:
    payload = {"title": "Title", "author": "Author"}
    payload[field] = "x" * (limit + 1)
    url = "/api/v1/books" if method == "post" else f"/api/v1/books/{book.id}"
    if method == "post":
        payload["isbn"] = "9780321125217"
    response = client.request(
        method, url, json=payload, headers={"If-Match": book_etag(book.id, 1)}
    )
    assert response.status_code == 422


def test_if_match_supports_lists_repeated_headers_and_wildcard(
    client: TestClient, book: Book
) -> None:
    url = f"/api/v1/books/{book.id}"
    response = client.patch(
        url,
        json={"title": "First"},
        headers=[("If-Match", '"other,tag"'), ("If-Match", book_etag(book.id, 1))],
    )
    assert response.status_code == 200
    response = client.patch(url, json={"title": "Second"}, headers={"If-Match": "*"})
    assert response.status_code == 200


def test_openapi_documents_update_contract_and_concurrency(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    operations = schema["paths"]["/api/v1/books/{book_id}"]
    for method in ("put", "patch"):
        operation = operations[method]
        assert {"200", "400", "404", "412", "422", "428"} <= operation["responses"].keys()
        header = next(p for p in operation["parameters"] if p["name"] == "if-match")
        assert header["in"] == "header"
        assert "428" in header["description"]
    assert "ETag" in operations["get"]["responses"]["200"]["headers"]
    assert "ETag" in operations["patch"]["responses"]["200"]["headers"]
    models = schema["components"]["schemas"]
    assert set(models["ReplaceBookRequest"]["required"]) == {"title", "author"}
    assert models["PatchBookRequest"]["minProperties"] == 1
    for name in ("BookTitle", "BookAuthor"):
        assert models[name]["type"] == "string"
    assert models["BookTitle"]["maxLength"] == 100
    assert models["BookAuthor"]["maxLength"] == 80
