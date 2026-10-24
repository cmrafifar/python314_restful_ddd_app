# Testing

Read when adding tests or validating behavior. Keep this guide focused on test boundaries,
shared patterns, execution, and safeguards. Discover individual tests from the codebase;
do not maintain a file-by-file inventory here.

## Test boundaries

| Location | What it proves |
|---|---|
| `tests/unit/` | Domain rules, application outcomes, DI wiring, and mapping/metadata without a live database |
| `tests/specs/` | Collaboration contracts using autospecced mocks |
| `tests/integration/api/` | HTTP behavior and OpenAPI through `TestClient`, using fake persistence |
| `tests/integration/persistence/` | Real MySQL constraints, conditional writes, commit visibility, and rollback; explicitly enabled |
| `tests/fakes/` | Reusable in-memory adapters supporting tests |

Fakes do not prove database semantics. `FakeUnitOfWork` records whether commit was requested
but does not implement rollback. ORM metadata checks do not exercise live constraints.
For concurrency regressions, use independent database connections and verify persisted
outcomes. A stale object in one session alone does not prove competing-writer behavior.

## Writing tests

- Use pytest files named `test_*.py` and functions named `test_*`.
- Add regression evidence at the layer responsible for the behavior. Cover relevant success,
  rejection, and boundary cases; include commit and rollback outcomes for persistence changes.
- Keep domain and application tests independent of FastAPI and SQLAlchemy. Inject their
  dependencies directly through constructors.
- Prefer fakes and observable outcomes. Assert interactions when they are contracts, such
  as committing only on success; avoid mirroring internal implementation steps.
- Verify HTTP statuses, response shapes, headers, and error translation through public routes.
- Exercise external adapters against the external system where fakes cannot prove guarantees.
- Keep tests deterministic and isolated. No numeric coverage threshold is configured.

### HTTP dependency overrides

Use `create_app(provider_overrides=[provider])` to replace dependencies for one application.
Register service overrides on a Dishka `Provider` using the production dependency type:

```python
from dishka import Provider, Scope

provider = Provider(scope=Scope.APP)
provider.provide(lambda: service, provides=CreateBookService, override=True)
app = create_app(provider_overrides=[provider])
```

To exercise real service orchestration with fake persistence, override `UnitOfWorkFactory`
instead. Register a function with that return annotation:

```python
def provide_unit_of_work_factory() -> UnitOfWorkFactory:
    return fake_unit_of_work_factory


provider.provide(provide_unit_of_work_factory, override=True)
```

Dishka 1.10.1 expands the annotated alias into registrations for both the alias and its underlying
type. Explicit `provides=UnitOfWorkFactory` alone can leave the production factory active.
Verify the override reaches the use case. Use `TestClient` as a context manager so application
shutdown closes the container and its resources.

## Local checks

Run from the repository root after `uv sync --frozen`:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run basedpyright
```

Default pytest runs without a database and skips MySQL tests, even when a database URL is
exported. The root test configuration supplies a dummy application password when absent;
production settings still require a password. BasedPyright discovers `.venv` through
`pyproject.toml` and needs no database configuration.

For a focused domain/application run:

```bash
uv run pytest tests/unit/domain tests/unit/application tests/specs
```

Report commands actually run, results, and material checks omitted. Report unrelated
failures rather than silently fixing or hiding them. Passing default pytest does not verify MySQL.

## MySQL integration setup

### Setup and execution

The isolated stack in [compose.test.yaml](../compose.test.yaml) uses MySQL on
`127.0.0.1:3308`, database/user `bookstore_test`, and its own volume. It is separate from the
development stack. Keep its server settings aligned with development and CI.

One-time configuration:

```bash
cp .env.test.example .env.test
chmod 600 .env.test
```

Set distinct local `APP_DB_PASSWORD` and `TEST_MYSQL_ROOT_PASSWORD` values. Keep `.env.test`
private and uncommitted. The Bash runner sources it as shell code, so use trusted,
Bash-compatible assignments. Single-quote passwords containing shell characters.

Run the full provision/migrate/check/test workflow from the repository root:

```bash
./scripts/test_integration.sh
```

The Bash runner loads `.env.test`, fixes the target to the isolated stack, and clears inherited
`PYTEST_ADDOPTS`. It waits up to 90 seconds for an authenticated query, applies migrations,
runs `alembic check`, and runs the integration suite. A failed prerequisite stops execution.
The MySQL service remains available afterward.

The runner derives `BOOKSTORE_TEST_DATABASE_URL` from the same settings used by Compose and
Alembic, including password URL-encoding. It replaces an exported URL; `.env.test` assignments
override exported settings. The Python runner, `./scripts/test_integration.py`, provides the
same workflow but rejects conflicting target settings or an existing conflicting database URL.

To run persistence tests directly against an already migrated test database:

```bash
uv run pytest tests/integration/persistence --run-integration
```

Direct pytest requires `BOOKSTORE_TEST_DATABASE_URL`; it does not provision MySQL, apply
migrations, or check drift. Without `--run-integration`, MySQL tests skip. With it, missing
configuration is an error. Fixtures reject non-MySQL URLs and database names other than
`bookstore_test` before connecting.

### Isolation and schema ownership

The session fixture opens an outer transaction and uses savepoints so application commits
can occur inside test isolation. It rolls back the outer transaction afterward. Tests needing
independent connections and durable commits must clean up their rows in `finally` blocks.
Use unique ISBNs so repeated runs do not depend on clearing existing rows. Interrupted runs
can leave durable rows behind; use only the dedicated test database.

Migrations own the schema. Do not use `metadata.create_all()` or maintain a separate test
schema. MySQL DDL can implicitly commit; keep schema changes outside per-test transactions.
`alembic check` detects supported schema differences, not behavioral correctness. See the
[migration guide](../migrations/README.md) for migration review and rollout.

### Inspecting and resetting the test stack

```bash
podman compose --env-file .env.test -p bookstore-integration -f compose.test.yaml logs mysql-test
podman compose --env-file .env.test -p bookstore-integration -f compose.test.yaml stop mysql-test
```

MySQL initializes credentials only on a fresh volume. Editing `.env.test` does not rotate
existing database passwords. To rebuild the disposable stack, the following command
**deletes all test-stack data**; it does not select the development stack:

```bash
podman compose --env-file .env.test -p bookstore-integration -f compose.test.yaml down --volumes
```

The next runner invocation creates the database and reapplies migrations.

## Continuous integration

[The workflow](../.github/workflows/ci.yml) defines job names, commands, runner versions,
and triggers. Specs and unit tests run as separate parallel checks. Integration provisions
MySQL, applies migrations, and checks schema drift before testing. CI uses disposable
credentials and does not need local `.env.test`.

Checks run for non-draft pull requests; standalone pushes and manual runs do not trigger
this workflow. The optional functional job repeats the health test already included in
integration. Enable it with repository Actions variable `RUN_FUNCTIONAL_TESTS=true`.
Branch protection must require the desired checks to enforce them at merge time.

When comparing CI changes, measure several comparable runs, separate cold and warm caches,
and distinguish elapsed time from billed runner minutes. A shared matrix reduces YAML
duplication, not runner count. Consult current GitHub pricing rather than recording rates here.
