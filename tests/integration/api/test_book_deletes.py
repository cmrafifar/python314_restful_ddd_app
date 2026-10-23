from collections.abc import Iterator
from uuid import uuid4

import pytest
from dishka import Provider, Scope
from fastapi.testclient import TestClient

from bookstore_api.api.books.conditional_requests import book_etag
from bookstore_api.application.books.errors import BookVersionConflictError
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
def book(repository: FakeBookRepository) -> Book:
    book = Book.create(ISBN("9780132350884"), "Original", "Author")
    repository.add(book)
    return book


@pytest.fixture
def client(repository: FakeBookRepository, book: Book) -> Iterator[TestClient]:
    def provide_unit_of_work_factory() -> UnitOfWorkFactory:
        return lambda: FakeUnitOfWork(repository)

    overrides = Provider(scope=Scope.APP)
    overrides.provide(provide_unit_of_work_factory, override=True)
    with TestClient(create_app(provider_overrides=[overrides])) as test_client:
        yield test_client


@pytest.mark.parametrize("validator", ["tag", "list", "repeated", "wildcard"])
def test_delete_returns_empty_204_and_repeated_delete_returns_404(
    client: TestClient, book: Book, validator: str
) -> None:
    url = f"/api/v1/books/{book.id}"
    etag = client.get(url).headers["etag"]
    headers = {
        "tag": [("If-Match", etag)],
        "list": [("If-Match", f'"other", {etag}')],
        "repeated": [("If-Match", '"other"'), ("If-Match", etag)],
        "wildcard": [("If-Match", "*")],
    }[validator]

    response = client.delete(url, headers=headers)

    assert response.status_code == 204
    assert response.content == b""
    assert "etag" not in response.headers
    assert client.get(url).status_code == 404
    repeated = client.delete(url, headers=headers)
    assert repeated.status_code == 404
    assert repeated.json()["detail"]["code"] == "book_not_found"


@pytest.mark.parametrize(
    "value,status,code",
    [
        (None, 428, "precondition_required"),
        ("unquoted", 400, "invalid_if_match"),
        ('W/"unknown"', 412, "precondition_failed"),
        ('"unknown"', 412, "precondition_failed"),
    ],
)
def test_rejected_precondition_preserves_book(
    client: TestClient, book: Book, value: str | None, status: int, code: str
) -> None:
    url = f"/api/v1/books/{book.id}"
    response = client.delete(url, headers={} if value is None else {"If-Match": value})

    assert response.status_code == status
    assert response.json()["detail"]["code"] == code
    if status == 428:
        assert response.headers["cache-control"] == "no-store"
    assert client.get(url).status_code == 200


def test_stale_client_cannot_delete_updated_book(client: TestClient, book: Book) -> None:
    url = f"/api/v1/books/{book.id}"
    etag = client.get(url).headers["etag"]
    updated = client.patch(url, json={"title": "Accepted"}, headers={"If-Match": etag})
    assert updated.status_code == 200

    response = client.delete(url, headers={"If-Match": etag})

    assert response.status_code == 412
    assert client.get(url).json()["title"] == "Accepted"


def test_repository_conflict_returns_412(
    client: TestClient, book: Book, repository: FakeBookRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    def conflicting_delete(book: Book) -> None:
        raise BookVersionConflictError("Another writer won")

    monkeypatch.setattr(repository, "delete", conflicting_delete)

    response = client.delete(f"/api/v1/books/{book.id}", headers={"If-Match": "*"})

    assert response.status_code == 412
    assert response.json()["detail"]["code"] == "precondition_failed"


def test_missing_book_returns_404(client: TestClient) -> None:
    missing_id = uuid4()
    response = client.delete(
        f"/api/v1/books/{missing_id}", headers={"If-Match": book_etag(missing_id, 1)}
    )
    assert response.status_code == 404


def test_invalid_uuid_returns_422(client: TestClient) -> None:
    response = client.delete("/api/v1/books/not-a-uuid", headers={"If-Match": "*"})
    assert response.status_code == 422


def test_openapi_documents_delete_contract(client: TestClient) -> None:
    operation = client.get("/openapi.json").json()["paths"]["/api/v1/books/{book_id}"]["delete"]
    assert {"204", "400", "404", "412", "422", "428"} <= operation["responses"].keys()
    assert "content" not in operation["responses"]["204"]
    assert "requestBody" not in operation
    header = next(p for p in operation["parameters"] if p["name"] == "if-match")
    assert header["in"] == "header"
    assert "428" in header["description"]
