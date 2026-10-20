# Testing

Read when adding tests or validating behavior. Use pytest files named `test_*.py` and functions named `test_*`.

## Current test boundaries

| Location | Purpose and current approach |
|---|---|
| [`tests/unit/domain/`](../tests/unit/domain) | Entity and value-object rules without frameworks or databases |
| [`tests/unit/application/`](../tests/unit/application) | Use-case behavior with in-memory repository and unit-of-work fakes |
| [`tests/specs/`](../tests/specs) | Collaboration specifications using autospecced repository and unit-of-work mocks |
| [`tests/unit/infrastructure/`](../tests/unit/infrastructure) | Mapper behavior and ORM metadata checks without a live database |
| [`tests/integration/persistence/`](../tests/integration/persistence) | MySQL repository, rollback, uniqueness, and durable-commit tests; explicitly enabled |
| [`tests/test_health.py`](../tests/test_health.py) | Functional test of HTTP health behavior using FastAPI `TestClient` |
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
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run basedpyright
```

BasedPyright discovers `.venv` through `pyproject.toml`; no database settings or extra flags are
needed. With the virtual environment activated, `basedpyright` runs the same check directly.
The settings factory has a targeted type-checker exception because Pydantic loads required fields
from the environment at runtime. Unit tests verify that the database password remains required.

Plain `uv run pytest` runs tests without a database and reports MySQL tests as skipped. Even an exported database URL does not enable them. [`tests/conftest.py`](../tests/conftest.py) supplies a dummy password before application import if none is set; production settings still require a password. The health test does not open a database connection.

For a focused domain/application run:

```bash
uv run pytest tests/unit/domain tests/unit/application tests/specs
```

Report commands actually run, their results, and material checks omitted. Existing unrelated failures should be reported rather than silently fixed or hidden.

## Continuous integration

[GitHub Actions](../.github/workflows/ci.yml) runs jobs only for non-draft pull requests: when opened,
updated with new commits, reopened, or marked ready for review. Draft pull request events can create
a workflow entry, but every job is skipped. Standalone pushes and manual runs do not trigger CI.
All jobs use the Python version in `.python-version` and install dependencies with
`uv sync --locked`, which rejects an outdated lockfile.

| Job | Command | Default |
|---|---|---|
| `Specs` | `uv run --locked pytest tests/specs` | Enabled |
| `Unit tests` | `uv run --locked pytest tests/unit` | Enabled |
| `Integration tests` | `uv run --locked pytest tests/integration --run-integration` | Disabled |
| `Functional tests` | `uv run --locked pytest tests/test_health.py` | Disabled |
| `BasedPyright` | `uv run --locked basedpyright` | Enabled |
| `Ruff` | `uv run --locked ruff check .` and `uv run --locked ruff format --check .` | Enabled |

Both Ruff checks report violations without modifying files. The current functional suite consists
of the health endpoint test in `tests/test_health.py`.

Integration and functional jobs remain fully defined. To enable either, open repository Settings >
Secrets and variables > Actions > Variables and add `RUN_INTEGRATION_TESTS` or `RUN_FUNCTIONAL_TESTS`
with the exact value `true`. Missing variables keep these jobs disabled. Set a variable to `false`
or delete it to disable its job again. The non-draft requirement still applies when enabled.

The integration job starts a disposable MySQL 8.4 service with a dedicated `bookstore_test` database
and applies Alembic migrations before running tests. Its committed credentials are test-only values
for that service; no repository secrets or `.env.test` are needed. Disabled jobs start no runners
or service containers.

After committing and opening a non-draft pull request, check the run in the repository's Actions tab.
To block merges when an enabled job fails, configure a branch protection rule for the default branch
under Settings > Branches. Enable required pull requests and require `Specs`, `Unit tests`,
`BasedPyright`, and `Ruff`. Replace any previous required `Pytest` check with these names.
Add integration and functional checks when enabling those jobs. Workflow files run checks; branch
protection enforces their results at merge time.

## MySQL integration setup

Integration tests require `--run-integration`. When enabled, missing configuration is an error rather than a skip. [`conftest.py`](../tests/integration/persistence/conftest.py) rejects non-MySQL URLs and any database name other than `bookstore_test` before opening a connection.

One-time local setup:

```bash
podman compose up -d mysql
podman compose exec mysql mysql -u root -p
```

Enter the local root password when prompted. Create a dedicated database and user in the MySQL shell, replacing the password placeholder with a local test password:

```sql
CREATE DATABASE IF NOT EXISTS bookstore_test;
CREATE USER IF NOT EXISTS 'bookstore_test'@'%' IDENTIFIED BY 'replace_with_local_test_password';
GRANT ALL PRIVILEGES ON bookstore_test.* TO 'bookstore_test'@'%';
```

This user has privileges only on the test database. Compose publishes MySQL on localhost port 3307 and creates only the development database automatically.

```bash
cp .env.test.example .env.test
chmod 600 .env.test
```

Edit `.env.test` with the matching test password in both password fields. URL-encode special characters in the URL credentials. Keep `APP_DB_NAME=bookstore_test`. This file is ignored by Git; never put real credentials in the committed example.

Apply reviewed migrations to the test database, with settings scoped to that command:

```bash
uv run --env-file .env.test alembic upgrade head
```

Alembic reads `APP_DB_*`, while tests read `BOOKSTORE_TEST_DATABASE_URL`. Keep both pointed at the same test database. Exported shell variables override values from `--env-file`; use a shell without conflicting `APP_DB_*` or `BOOKSTORE_TEST_DATABASE_URL` exports, especially before migrations.

For each subsequent full run:

```bash
uv run --env-file .env.test pytest --run-integration
```

To run only the MySQL tests:

```bash
uv run --env-file .env.test pytest tests/integration --run-integration
```

CI should provision the test database, apply migrations, and run with `--run-integration`; a passing default run does not verify MySQL. See [development](development.md) and the [migration guide](../migrations/README.md) for migration details. Fixtures do not create the schema.

The session fixture opens an outer transaction and uses savepoints so application commits can occur inside test isolation. It rolls back the outer transaction afterward. This is not a schema cleanup mechanism: MySQL DDL can implicitly commit. Keep schema changes outside per-test transactions.

The durable-commit test uses a separate connection and commits a real row. Its `finally` block deletes that row. An interrupted process can leave a test row behind, so use only the dedicated test database. Tests use unique ISBNs to support repeated runs without clearing existing rows.
