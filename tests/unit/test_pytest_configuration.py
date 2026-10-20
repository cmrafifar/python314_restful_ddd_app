import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("run_integration", "database_url", "expected_code", "expected_output"),
    [
        pytest.param(
            False,
            None,
            0,
            "1 skipped",
            id="disabled-without-url",
        ),
        pytest.param(
            False,
            "mysql+pymysql://unused:unused@127.0.0.1:1/bookstore",
            0,
            "1 skipped",
            id="disabled-with-unsafe-url",
        ),
        pytest.param(
            True,
            None,
            1,
            "BOOKSTORE_TEST_DATABASE_URL must be configured",
            id="enabled-without-url",
        ),
        pytest.param(
            True,
            "mysql+pymysql://unused:unused@127.0.0.1:1/bookstore",
            1,
            "Refusing to run against a non-test database",
            id="enabled-with-unsafe-database",
        ),
        pytest.param(
            True,
            "sqlite:///bookstore_test",
            1,
            "Integration tests require MySQL",
            id="enabled-with-non-mysql-url",
        ),
    ],
)
def test_database_tests_require_explicit_safe_configuration(
    run_integration: bool,
    database_url: str | None,
    expected_code: int,
    expected_output: str,
) -> None:
    environment = os.environ.copy()
    environment.pop("APP_DB_PASSWORD", None)
    environment.pop("BOOKSTORE_TEST_DATABASE_URL", None)
    environment.pop("PYTEST_ADDOPTS", None)
    if database_url is not None:
        environment["BOOKSTORE_TEST_DATABASE_URL"] = database_url

    # Select one real database test so adding integration tests cannot change these outcomes.
    test_node = (
        "tests/integration/persistence/test_sqlalchemy_unit_of_work.py"
        "::test_repository_persists_and_reconstructs_book"
    )
    command = [sys.executable, "-m", "pytest", test_node, "-q"]
    if run_integration:
        command.append("--run-integration")

    result = subprocess.run(
        command,
        cwd=Path(__file__).resolve().parents[2],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    output = result.stdout + result.stderr
    assert result.returncode == expected_code, output
    assert expected_output in output, output
