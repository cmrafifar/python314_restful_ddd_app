#!/usr/bin/env -S uv run --locked --env-file .env.test python
"""Start isolated MySQL, migrate, check schema drift, and run integration tests."""

import os
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError, OperationalError

ROOT = Path(__file__).resolve().parents[1]


# Used Mapping (akin to php's \ArrayAccess) which allows to handle different dictionary classes + dict
def build_environment(source: Mapping[str, str]) -> dict[str, str]:
    expected = {
        "APP_DB_HOST": "127.0.0.1",
        "APP_DB_PORT": "3308",
        "APP_DB_NAME": "bookstore_test",
        "APP_DB_USER": "bookstore_test",
    }
    for name, value in expected.items():
        if source.get(name, value) != value:
            raise ValueError(f"{name} must be {value} for the local integration runner")

    for name in ("APP_DB_PASSWORD", "TEST_MYSQL_ROOT_PASSWORD"):
        if not source.get(name) or source[name].startswith("replace_with_"):
            raise ValueError(f"Set {name} to a local password in .env.test")

    url = URL.create(
        "mysql+pymysql",
        username=expected["APP_DB_USER"],
        password=source["APP_DB_PASSWORD"],
        host=expected["APP_DB_HOST"],
        port=int(expected["APP_DB_PORT"]),
        database=expected["APP_DB_NAME"],
    )
    existing_url = source.get("BOOKSTORE_TEST_DATABASE_URL")
    if existing_url is not None:
        try:
            matches = make_url(existing_url) == url
        except ArgumentError, ValueError:
            matches = False
        if not matches:
            raise ValueError(
                "Remove conflicting BOOKSTORE_TEST_DATABASE_URL; the runner derives it"
            )

    environment = dict(source)
    environment.update(expected)
    environment["BOOKSTORE_TEST_DATABASE_URL"] = url.render_as_string(hide_password=False)
    # Parent pytest flags must not change this runner's selected suite or integration opt-in.
    environment.pop("PYTEST_ADDOPTS", None)
    return environment


def wait_for_mysql(database_url: str) -> None:
    engine = create_engine(database_url, connect_args={"connect_timeout": 2})
    deadline = time.monotonic() + 90
    try:
        while True:
            try:
                with engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                return
            except OperationalError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        "Test MySQL did not become ready within 90 seconds. Check its logs and "
                        ".env.test credentials; changing the file does not rotate existing users."
                    ) from None
                time.sleep(1)
    finally:
        engine.dispose()


def main() -> None:
    environment = build_environment(os.environ)
    compose = [
        "podman",
        "compose",
        "--env-file",
        ".env.test",
        "-p",
        "bookstore-integration",
        "-f",
        "compose.test.yaml",
    ]
    print("Starting test MySQL at 127.0.0.1:3308/bookstore_test", flush=True)
    subprocess.run([*compose, "up", "-d", "mysql-test"], cwd=ROOT, env=environment, check=True)
    wait_for_mysql(environment["BOOKSTORE_TEST_DATABASE_URL"])

    for arguments in (
        ["alembic", "upgrade", "head"],
        ["alembic", "check"],
        ["pytest", "tests/integration", "--run-integration"],
    ):
        subprocess.run([sys.executable, "-m", *arguments], cwd=ROOT, env=environment, check=True)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, TimeoutError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
