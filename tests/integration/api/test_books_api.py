from unittest.mock import create_autospec, patch
from uuid import uuid4

from dishka import Provider, Scope
from fastapi.testclient import TestClient

from bookstore_api.application.books.create_book import (
    CreateBookResult,
    CreateBookService,
)
from bookstore_api.application.unit_of_work import UnitOfWork, UnitOfWorkFactory
from bookstore_api.main import create_app
from tests.fakes.book_repository import FakeBookRepository
from tests.fakes.unit_of_work import FakeUnitOfWork


def test_create_book_returns_201() -> None:
    service = create_autospec(
        CreateBookService,
        instance=True,
    )

    book_id = uuid4()
    service.execute.return_value = CreateBookResult(
        book_id=book_id,
    )

    overrides = Provider(scope=Scope.APP)
    overrides.provide(lambda: service, provides=CreateBookService, override=True)
    app = create_app(provider_overrides=[overrides])

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/books",
            json={
                "isbn": "9780132350884",
                "title": "Clean Code",
                "author": "Robert C. Martin",
            },
        )

    assert response.status_code == 201
    assert response.json() == {
        "id": str(book_id),
    }

    service.execute.assert_called_once()
    command = service.execute.call_args.args[0]

    assert command.isbn == "9780132350884"
    assert command.title == "Clean Code"
    assert command.author == "Robert C. Martin"


def test_create_book_uses_configured_service() -> None:
    repository = FakeBookRepository()
    create_uow = FakeUnitOfWork(repository)
    duplicate_uow = FakeUnitOfWork(repository)
    payload = {
        "isbn": "9780132350884",
        "title": "Clean Code",
        "author": "Robert C. Martin",
    }

    units_of_work = iter([create_uow, duplicate_uow])

    def unit_of_work_factory() -> UnitOfWork:
        return next(units_of_work)

    def provide_unit_of_work_factory() -> UnitOfWorkFactory:
        return unit_of_work_factory

    overrides = Provider(scope=Scope.APP)
    overrides.provide(
        provide_unit_of_work_factory,
        override=True,
    )
    app = create_app(provider_overrides=[overrides])

    with TestClient(app) as client:
        created = client.post("/api/v1/books", json=payload)
        duplicate = client.post("/api/v1/books", json=payload)

    assert created.status_code == 201
    book = next(iter(repository.books.values()))
    assert created.json() == {"id": str(book.id)}
    assert book.title == payload["title"]
    assert create_uow.committed
    assert duplicate.status_code == 409
    assert duplicate.json() == {
        "detail": "Book with ISBN 9780132350884 already exists",
    }
    assert not duplicate_uow.committed
    assert len(repository.books) == 1


def test_create_book_rejects_missing_fields() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/api/v1/books", json={"isbn": "9780132350884"})

    assert response.status_code == 422
    assert {tuple(error["loc"]) for error in response.json()["detail"]} == {
        ("body", "title"),
        ("body", "author"),
    }


def test_app_disposes_database_engine_on_shutdown() -> None:
    with (
        patch(
            "bookstore_api.di.providers.persistence.create_db_engine", autospec=True
        ) as create_engine,
        patch(
            "bookstore_api.di.providers.persistence.SqlAlchemyUnitOfWork",
            side_effect=lambda _: FakeUnitOfWork(FakeBookRepository()),
        ),
    ):
        app = create_app()
        engine = create_engine.return_value

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/books",
                json={
                    "isbn": "9780132350884",
                    "title": "Clean Code",
                    "author": "Robert C. Martin",
                },
            )
            assert response.status_code == 201
            engine.dispose.assert_not_called()

        engine.dispose.assert_called_once_with()
