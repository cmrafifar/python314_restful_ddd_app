# Testing

Read when adding tests or validating behavior. Use pytest files named `test_*.py` and functions named `test_*`.

## Current test boundaries

| Location | Purpose and current approach |
|---|---|
| [`tests/unit/domain/`](../tests/unit/domain) | Entity and value-object rules without frameworks or databases |
| [`tests/unit/application/`](../tests/unit/application) | Use-case behavior with in-memory repository and unit-of-work fakes |
| [`tests/specs/`](../tests/specs) | Collaboration specifications using autospecced repository and unit-of-work mocks |
| [`tests/unit/infrastructure/`](../tests/unit/infrastructure) | Mapper behavior and ORM metadata checks without a live database |
| [`tests/integration/persistence/`](../tests/integration/persistence) | MySQL fixtures; no integration test cases currently exist |
| [`tests/test_health.py`](../tests/test_health.py) | HTTP health behavior using FastAPI `TestClient` |
| [`tests/fakes/`](../tests/fakes) | Reusable in-memory adapters |

Prefer fakes for observable application outcomes. Use interaction assertions where the interaction is a contract, such as committing only on success. Do not assert every internal call or mirror implementation steps without a behavioral reason.

Fakes are not proof of database semantics. `FakeUnitOfWork` records whether commit was requested but does not implement transactional rollback. ORM metadata tests do not exercise live MySQL constraints.

## Required regression evidence

- Add regression tests for behavior changes at the responsible layer.
- Cover relevant success, rejection, and boundary cases. Include transaction outcomes when changing persistence orchestration.
- Keep domain and application tests independent of FastAPI and SQLAlchemy.
- When implementing adapter behavior, exercise it against the external system where fakes cannot prove the contract.
- For new HTTP behavior, verify status, response shape, and error translation through the public route.

Tests should be deterministic and isolated. No numeric coverage threshold is configured; meaningful behavioral proof is the goal.

## Running checks

Run from the repository root after `uv sync --frozen`:

```bash
export APP_DB_PASSWORD=development_password
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run basedpyright
```

The password is a local placeholder required because the health test imports the application, which loads settings. It does not cause that test to open a database connection.

For a focused domain/application run:

```bash
uv run pytest tests/unit/domain tests/unit/application tests/specs
```

Report commands actually run, their results, and material checks omitted. Existing unrelated failures should be reported rather than silently fixed or hidden.

## MySQL integration setup

[`conftest.py`](../tests/integration/persistence/conftest.py) requires `BOOKSTORE_TEST_DATABASE_URL` when its engine fixture is requested. It rejects non-MySQL URLs and any database name other than `bookstore_test`.

```bash
export BOOKSTORE_TEST_DATABASE_URL='mysql+pymysql://bookstore:development_password@127.0.0.1:3307/bookstore_test'
uv run pytest tests/integration
```

Provision that database and grant the test user access before use. Compose creates `bookstore`, not `bookstore_test`. The example URL assumes the matching local credentials and grant exist.

Apply migrations to the test database using `APP_DB_*` settings, as described in [development](development.md). `BOOKSTORE_TEST_DATABASE_URL` configures test fixtures only; Alembic does not read it. Fixtures do not create the schema.

The session fixture opens an outer transaction and uses savepoints so application commits can occur inside test isolation. It rolls back the outer transaction afterward. This is not a schema cleanup mechanism: MySQL DDL can implicitly commit. Keep schema changes outside per-test transactions.

Running the integration directory currently collects no test cases; it does not verify connectivity, migrations, or rollback behavior. Add those cases when persistence integration work is undertaken.
