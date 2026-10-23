# Development

Read for local setup, configuration, containers, and persistence workflows. Run commands from the repository root.

## Tooling

Use Python 3.14+ and `uv`. Container workflows use Podman Compose; persistence uses MySQL 8.4 in the committed Compose configuration.

```bash
uv sync --frozen
uv build
```

Use [testing](testing.md) for pytest and static checks. Dependency declarations and tool settings live in [pyproject.toml](../pyproject.toml); resolved versions live in [uv.lock](../uv.lock).

## Manual security scan

The [Security workflow](../.github/workflows/security.yml) runs only when manually triggered. It installs locked runtime and development dependencies, exports `uv.lock` to a temporary pip requirements file, and runs Snyk Open Source against that environment. The export adapts uv's lockfile to Snyk's [documented Python CLI support](https://docs.snyk.io/supported-languages/supported-languages-list/python/snyk-cli-for-python); it does not add a second dependency file to the repository.

Before the first run:

1. Get an API token from your Snyk account. See [Snyk's token instructions](https://github.com/snyk/actions#getting-your-snyk-token).
2. In GitHub, open **Settings > Secrets and variables > Actions** and create a repository secret named `SNYK_TOKEN`.
3. Merge the workflow into the repository's default branch so GitHub exposes the manual trigger.

To scan, open **Actions > Security > Run workflow**, select the branch, and click **Run workflow**. Repository write access is required. See [GitHub's manual workflow guide](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).

Results appear in the workflow logs. Vulnerabilities of any severity fail the scan; missing credentials or scan errors also fail the workflow. This workflow checks Python dependencies, including transitive dependencies; it does not scan application source code or container images.

## Settings

[`Settings`](../src/bookstore_api/config.py) reads environment variables with the `APP_` prefix. Unknown settings are ignored. No `env_file` is configured, so host commands must explicitly load `.env` with `uv --env-file`. [.env.example](../.env.example) documents application and development database settings.

| Variable | Current default or requirement |
|---|---|
| `APP_NAME` | `Bookstore API` |
| `APP_ENVIRONMENT` | `development` |
| `APP_DEBUG` | `False` |
| `APP_DB_HOST` | `localhost` |
| `APP_DB_PORT` | `3306` |
| `APP_DB_NAME` | `bookstore` |
| `APP_DB_USER` | `bookstore` |
| `APP_DB_PASSWORD` | Required; no default |

Application import creates the module-level FastAPI app and loads settings. Pytest supplies a dummy password when none is set, so the default test run needs no credentials. Other application entry points still require the password. `get_settings` constructs a new settings object on each call; it is not cached.

Keep real secrets out of commits. Compose reads passwords from the ignored `.env`; no password
defaults are embedded in the development Compose file. Local environment files are plaintext,
not a production secret store. Use a managed secret store with workload identity, rotation, and
restricted runtime database permissions for production.

## Local API and database

On first setup, copy `.env.example` to `.env`, restrict its permissions, and replace both password
placeholders with distinct local passwords. For example, `uv run python -c
'import secrets; print(secrets.token_hex(24))'` generates a password suitable for these files.

```bash
cp .env.example .env
chmod 600 .env
```

Start MySQL after editing `.env`:

```bash
podman compose up -d mysql
```

For an API process running on the host, load the same settings explicitly:

```bash
uv run --env-file .env uvicorn bookstore_api.main:app --reload
```

Alternatively, start both services:

```bash
podman compose up --build -d
podman compose ps
```

The container API uses `mysql:3306`; the host uses `127.0.0.1:3307`. The API is published at `127.0.0.1:8000`. Container environment variables do not configure commands run on the host.

Compose mounts `src/` for API reload and stores MySQL data in a named volume. Service startup does not run Alembic. The `bookstore-api` console command currently prints a greeting; use Uvicorn to serve HTTP.

MySQL initialization variables only configure a fresh data directory. Changing `.env` does not
rotate an existing database user's password. When adopting this configuration with an existing
volume, use the existing credentials in `.env` or rotate the users explicitly with `ALTER USER`.
Do not delete the development volume to resolve a credential mismatch.

## MySQL data persistence

The MySQL service mounts the named volume `mysql_data` at `/var/lib/mysql`, where MySQL
stores its database files. Podman manages this volume separately from the container, so
the data does not appear in a directory inside this repository. A replacement container
reuses the existing data when Compose mounts the same volume.

With the default project name for this checkout, the volume is named
`python314_restful_ddd_app_mysql_data`. Find its host storage location with:

```bash
podman volume ls
podman volume inspect python314_restful_ddd_app_mysql_data --format '{{.Mountpoint}}'
```

For rootless Podman on Linux, the location is typically
`~/.local/share/containers/storage/volumes/python314_restful_ddd_app_mysql_data/_data`.
Use the inspection command for the actual location; storage configuration can change it.

| Operation | Effect on database data |
|---|---|
| Restart, rebuild, or recreate the services | Preserves data in the existing volume |
| `podman compose down` followed by `podman compose up -d` | Preserves and reuses the volume |
| `podman compose down -v` | Deletes the volume and its database data |
| Change the Compose project name | Uses a different volume; the original volume remains |

A persistent volume is not a backup. Keep database backups separately when the data matters.

## Migrations

The [migration guide](../migrations/README.md) owns detailed migration procedures and MySQL limitations. Alembic is already initialized; do not initialize it again.

With `.env` configured for the development database:

```bash
uv run --env-file .env alembic current
uv run --env-file .env alembic upgrade head
uv run --env-file .env alembic check
```

For schema changes, generate a revision, review its operations, then apply and verify it. Do not apply autogenerated migrations without review. Commit model and migration changes together. Downgrades can lose data; use the migration guide to plan recovery.

Integration tests use the optional standalone `compose.test.yaml` stack, with its own MySQL
service, network, volume, and host port 3308. After configuring `.env.test`, run
`./scripts/test_integration.sh` from the repository root. It starts MySQL, applies the shared
migrations, checks schema drift, and runs the integration suite. See
[testing](testing.md#mysql-integration-setup) for setup and lifecycle commands. Default pytest
runs skip MySQL tests.

## Troubleshooting

| Symptom | Check |
|---|---|
| Required `db_password` validation error | Export `APP_DB_PASSWORD` in the process environment; `.env` is not loaded automatically |
| Host database connection fails | Use port 3307 and check `podman compose ps` and `podman compose logs mysql` |
| Container database connection fails | Use host `mysql` and port 3306 inside Compose |
| Health succeeds but persistence fails | Health does not verify MySQL; inspect settings, connectivity, grants, and migration state |
| Integration fixture rejects configuration | Use a MySQL URL whose database is exactly `bookstore_test` |
| Integration table is missing | Apply migrations to the test database; fixtures do not create tables |

When changing configuration, update examples and this guide together. Never include real credentials in diagnostics or documentation.
