# Testing

Read when adding tests or validating behavior. Use pytest files named `test_*.py` and functions named `test_*`.

## Current test boundaries

| Location | Purpose and current approach |
|---|---|
| [`tests/unit/domain/`](../tests/unit/domain) | Entity and value-object rules without frameworks or databases |
| [`tests/unit/application/`](../tests/unit/application) | Use-case behavior with in-memory repository and unit-of-work fakes |
| [`tests/specs/`](../tests/specs) | Collaboration specifications using autospecced repository and unit-of-work mocks |
| [`tests/unit/di/`](../tests/unit/di) | Container isolation and per-unit-of-work session ownership without a live database |
| [`tests/unit/infrastructure/`](../tests/unit/infrastructure) | Mapper behavior and ORM metadata checks without a live database |
| [`tests/integration/persistence/`](../tests/integration/persistence) | MySQL repository, rollback, uniqueness, and durable-commit tests; explicitly enabled |
| [`tests/integration/api/test_health.py`](../tests/integration/api/test_health.py) | HTTP health behavior using FastAPI `TestClient`, without a database |
| [`tests/integration/api/test_books_api.py`](../tests/integration/api/test_books_api.py) | Create-book route, configured service with fake units of work, validation, and engine cleanup without a database |
| [`tests/fakes/`](../tests/fakes) | Reusable in-memory adapters |

HTTP tests replace dependencies through `create_app(provider_overrides=[provider])`. Register
replacement factories on a Dishka `Provider` with `override=True`, using the production dependency
type as `provides`. For example:

```python
from dishka import Provider, Scope

provider = Provider(scope=Scope.APP)
provider.provide(lambda: service, provides=CreateBookService, override=True)
app = create_app(provider_overrides=[provider])
```

This replaces the service only for that application. To exercise real service orchestration,
override `Callable[[], UnitOfWork]` with a factory returning fake units of work instead. Use
`TestClient` as a context manager so application shutdown closes the container and its resources.
Application and domain tests still use direct constructor injection without a container.

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

All jobs run on `ubuntu-24.04`. Python is selected with `actions/setup-python` using
`.python-version`, allowing reuse of the runner's installed Python tool cache. uv's dependency
cache remains enabled. A new run cancels older runs for the same pull request.

Specs and unit tests use one matrix definition but run as separate parallel jobs. Their check
names remain `Specs` and `Unit tests`. Matrix fail-fast is disabled so a failure in one suite
does not cancel the other. Ruff continues to install the full project and development dependencies.

| Job | Command | Default |
|---|---|---|
| `Specs` | `uv run --locked pytest tests/specs` | Enabled |
| `Unit tests` | `uv run --locked pytest tests/unit` | Enabled |
| `Integration tests` | `uv run --locked pytest tests/integration --run-integration` | Enabled |
| `Functional tests` | `uv run --locked pytest tests/integration/api/test_health.py` | Disabled |
| `BasedPyright` | `uv run --locked basedpyright` | Enabled |
| `Ruff` | `uv run --locked ruff check .` and `uv run --locked ruff format --check .` | Enabled |

Both Ruff checks report violations without modifying files. The current functional suite consists
of the health endpoint test in `tests/integration/api/test_health.py`; the integration job also
runs this test as part of `tests/integration`.

Integration tests run for every non-draft pull request; `RUN_INTEGRATION_TESTS` is no longer used.
Functional tests remain optional. To enable them, open repository Settings > Secrets and
variables > Actions > Variables and set `RUN_FUNCTIONAL_TESTS` to exactly `true`. Delete it or
set it to `false` to disable the functional job.

The integration job starts a disposable MySQL 8.4 service with a dedicated `bookstore_test` database
and runs `alembic upgrade head` followed by `alembic check` before running tests. Its committed
credentials belong only to that disposable service; no repository secrets or `.env.test` are
needed. Draft pull requests start no integration runner or service container.

After committing and opening a non-draft pull request, check the run in the repository's Actions tab.
To block merges when an enabled job fails, configure a branch protection rule for the default branch
under Settings > Branches. Enable required pull requests and require `Specs`, `Unit tests`,
`BasedPyright`, and `Ruff`. Replace any previous required `Pytest` check with these names.
Also require `Integration tests`, and add functional checks when enabling that job. Workflow files run checks; branch
protection enforces their results at merge time.

### Comparing CI performance and cost

Compare at least five completed runs before and after a workflow change with the same enabled
jobs, Python version, dependency lockfile, and similar test workload. Record the first run after
a dependency change separately from runs with a restored cache. Use median results to reduce
the effect of shared-runner variability.

In Actions, open each run and record:

- Time from the workflow starting to its last job finishing, plus queue time separately, to
  measure feedback speed.
- Each job's elapsed time and the durations of Python setup, dependency synchronization, and
  cache restore/save steps to identify where time changed.
- The sum of each job's duration rounded up to whole minutes to estimate billable runner minutes.
  Include canceled runs when comparing total consumption over a period; cancellation saves work
  across runs rather than speeding up a completed run.

For private repositories, multiply rounded runner minutes by the applicable rate in
[GitHub's runner pricing](https://docs.github.com/en/billing/reference/actions-runner-pricing).
Standard Linux x64 usage currently costs $0.006 per minute after included allowances. For example,
four jobs taking 35 seconds each and four taking 25 seconds each both round to four runner minutes.
The second run is faster but has the same estimated compute cost. Standard hosted runners in public
repositories are free. Check account billing usage for actual charges and allowance consumption;
elapsed-time estimates do not replace billing records.

The matrix reduces duplicated YAML; it does not reduce the number of runners. Python tool-cache
reuse may reduce setup time, but verify the timings before claiming a speed or cost improvement.

## MySQL integration setup

Integration tests require `--run-integration`. When enabled, missing configuration is an error rather than a skip. [`conftest.py`](../tests/integration/persistence/conftest.py) rejects non-MySQL URLs and any database name other than `bookstore_test` before opening a connection.

The local integration stack is defined in `compose.test.yaml`, separate from the development
stack. It uses MySQL 8.4 on `127.0.0.1:3308`, database/user `bookstore_test`, and its own named
volume. Keep its MySQL image version and server settings aligned with development and CI.
The test user's privileges are limited to `bookstore_test`.

One-time local configuration:

```bash
cp .env.test.example .env.test
chmod 600 .env.test
```

Replace `APP_DB_PASSWORD` and `TEST_MYSQL_ROOT_PASSWORD` with distinct local passwords. A value
from `uv run python -c 'import secrets; print(secrets.token_hex(24))'` works without quoting or
interpolation concerns. The ignored `.env.test` is plaintext; do not commit credentials.

Run from the repository root:

```bash
./scripts/test_integration.py
```

This executable uses `uv` to load `.env.test` and the locked Python environment. It validates the
local test target before starting containers or applying migrations, starts the standalone
`bookstore-integration` Compose project, and waits for an authenticated connection. It then runs
the shared Alembic migrations, checks for model/schema differences, and runs the integration
suite. A failed prerequisite stops the sequence. The service remains available for later runs.

Compose and Alembic use the same `APP_DB_PASSWORD`. The runner builds
`BOOKSTORE_TEST_DATABASE_URL` from `APP_DB_*`, including URL-encoding its password, so there is
only one test password to maintain. Remove the old URL entry when migrating an existing
`.env.test`; port 3307 changes to 3308. Exported shell variables override `uv --env-file` values;
conflicting targets and URLs are rejected before migrations.

The shared migration history is the schema source of truth. Do not create test tables with
`metadata.create_all()` or maintain a separate SQL schema. `alembic check` detects differences
supported by Alembic autogeneration; migration review and behavior tests remain necessary.
Fresh CI databases verify that the migration history can build the schema from scratch.

Inspect or stop only the test stack:

```bash
podman compose --env-file .env.test -p bookstore-integration -f compose.test.yaml logs mysql-test
podman compose --env-file .env.test -p bookstore-integration -f compose.test.yaml stop mysql-test
```

MySQL initializes credentials only on a fresh volume. Changing `.env.test` does not rotate an
existing user's password. To rebuild the disposable test database, the following command
**deletes all test-stack data**; it does not select the development stack:

```bash
podman compose --env-file .env.test -p bookstore-integration -f compose.test.yaml down --volumes
```

The next runner invocation provisions a new database and reapplies all migrations. Direct pytest
invocations still accept `BOOKSTORE_TEST_DATABASE_URL` for CI or externally provisioned MySQL,
but they do not provision the database, run migrations, or check drift. A passing default pytest
run does not verify MySQL. See [development](development.md) and the
[migration guide](../migrations/README.md) for migration details.

The session fixture opens an outer transaction and uses savepoints so application commits can occur inside test isolation. It rolls back the outer transaction afterward. This is not a schema cleanup mechanism: MySQL DDL can implicitly commit. Keep schema changes outside per-test transactions.

The durable-commit test uses a separate connection and commits a real row. Its `finally` block deletes that row. An interrupted process can leave a test row behind, so use only the dedicated test database. Tests use unique ISBNs to support repeated runs without clearing existing rows.
