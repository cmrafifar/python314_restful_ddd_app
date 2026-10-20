import subprocess
from unittest.mock import Mock

import pytest
from sqlalchemy.engine import make_url

from scripts import test_integration as runner


@pytest.fixture
def local_environment() -> dict[str, str]:
    return {
        "APP_DB_HOST": "127.0.0.1",
        "APP_DB_PORT": "3308",
        "APP_DB_NAME": "bookstore_test",
        "APP_DB_USER": "bookstore_test",
        "APP_DB_PASSWORD": "test-password-with-@:/#%",
        "TEST_MYSQL_ROOT_PASSWORD": "test-root-password",
    }


def test_runner_derives_matching_connection_settings(
    local_environment: dict[str, str],
) -> None:
    local_environment["PYTEST_ADDOPTS"] = "--collect-only"

    environment = runner.build_environment(local_environment)
    url = make_url(environment["BOOKSTORE_TEST_DATABASE_URL"])

    assert url.get_backend_name() == "mysql"
    assert url.host == environment["APP_DB_HOST"]
    assert url.port == int(environment["APP_DB_PORT"])
    assert url.database == environment["APP_DB_NAME"]
    assert url.username == environment["APP_DB_USER"]
    assert url.password == environment["APP_DB_PASSWORD"]
    assert "PYTEST_ADDOPTS" not in environment
    assert "BOOKSTORE_TEST_DATABASE_URL" not in local_environment


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("APP_DB_HOST", "production.example.com"),
        ("APP_DB_PORT", "3307"),
        ("APP_DB_NAME", "bookstore"),
        ("APP_DB_USER", "root"),
        ("APP_DB_PASSWORD", ""),
        ("APP_DB_PASSWORD", "replace_with_local_test_password"),
        ("TEST_MYSQL_ROOT_PASSWORD", ""),
    ],
)
def test_runner_rejects_invalid_settings_before_starting_containers(
    local_environment: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    value: str,
) -> None:
    local_environment[name] = value
    monkeypatch.setattr(runner.os, "environ", local_environment)
    run = Mock()
    monkeypatch.setattr(runner.subprocess, "run", run)

    with pytest.raises(ValueError, match=name):
        runner.main()

    run.assert_not_called()


@pytest.mark.parametrize(
    "database_url",
    [
        "mysql+pymysql://bookstore_test:stale-password@127.0.0.1:3307/bookstore_test",
        "malformed-url-with-a-password",
    ],
)
def test_runner_rejects_conflicting_test_url(
    local_environment: dict[str, str], database_url: str
) -> None:
    local_environment["BOOKSTORE_TEST_DATABASE_URL"] = database_url

    with pytest.raises(ValueError, match="conflicting BOOKSTORE_TEST_DATABASE_URL") as error:
        runner.build_environment(local_environment)

    assert database_url not in str(error.value)


@pytest.mark.parametrize("failed_command", ["up", "upgrade", "check"])
def test_runner_does_not_run_tests_when_preparation_fails(
    local_environment: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    failed_command: str,
) -> None:
    monkeypatch.setattr(runner.os, "environ", local_environment)
    monkeypatch.setattr(runner, "wait_for_mysql", Mock())
    commands: list[list[str]] = []

    def run(command: list[str], **kwargs: object) -> None:
        commands.append(command)
        if failed_command in command:
            raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(runner.subprocess, "run", run)

    with pytest.raises(subprocess.CalledProcessError):
        runner.main()

    assert all("pytest" not in command for command in commands)
