from collections.abc import Callable
from unittest.mock import create_autospec, patch

from sqlalchemy.orm import Session

from bookstore_api.application.books.create_book import CreateBookService
from bookstore_api.application.unit_of_work import UnitOfWork
from bookstore_api.config import Settings
from bookstore_api.di.container import create_container


def test_shared_service_creates_and_closes_a_session_per_unit_of_work() -> None:
    sessions = [create_autospec(Session, instance=True) for _ in range(2)]
    for session in sessions:
        session.in_transaction.return_value = False

    with patch(
        "bookstore_api.di.providers.persistence.create_session_factory", autospec=True
    ) as create_session_factory:
        create_session_factory.return_value.side_effect = sessions

        with create_container(Settings(db_password="test-only-password")) as container:
            with container() as first_request:
                first_service = first_request.get(CreateBookService)
            with container() as second_request:
                assert second_request.get(CreateBookService) is first_service

            factory = container.get(Callable[[], UnitOfWork])
            with factory() as first_uow:
                first_uow.commit()
            with factory() as second_uow:
                assert second_uow is not first_uow

    sessions[0].commit.assert_called_once_with()
    sessions[1].commit.assert_not_called()
    for session in sessions:
        session.close.assert_called_once_with()


def test_containers_isolate_settings_and_services() -> None:
    first_settings = Settings(name="First API", db_password="test-only-password")
    second_settings = Settings(name="Second API", db_password="test-only-password")

    with (
        create_container(first_settings) as first,
        create_container(second_settings) as second,
    ):
        assert first.get(Settings) is first_settings
        assert second.get(Settings) is second_settings
        assert first.get(CreateBookService) is not second.get(CreateBookService)
