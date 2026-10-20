import os

import pytest

# Application import validates settings before pytest runs fixtures.
os.environ.setdefault("APP_DB_PASSWORD", "test-only-password")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run MySQL integration tests against the configured bookstore_test database.",
    )
