# Bookstore API

A small Python learning project for building a REST-like API with Domain-Driven Design and hexagonal architecture.

The project explores Python 3.14+, FastAPI, SQLAlchemy, Alembic, MySQL, pytest, and typed ports. Business rules belong to the domain; application use cases coordinate those rules through ports; adapters handle external systems.

## Learning goals and working approach

The developer is a senior backend engineer experienced with PHP 8.4 and Laravel 12. Focus explanations on Python and its libraries, architectural tradeoffs, and differences from Laravel rather than introductory backend concepts.

Preserve familiar DDD and hexagonal boundaries while using idiomatic Python. Professional quality means explicit dependencies, protected business rules, deliberate transaction ownership, useful type annotations, and meaningful tests. Add complexity when a concrete requirement or learning objective justifies it.

The AI collaborator may choose contrived business requirements and explain consequential choices. Keep the exercise coherent: the chosen scope is a bookstore catalog, where each Book represents one edition in one format. The [domain document](docs/domain/books.md) defines the terminology; [decision 0001](docs/decisions/0001-learning-strategy.md) records this direction.

The next planned learning slice is to create a book through HTTP, persist it in MySQL, retrieve it, and verify validation, duplicate handling, and transaction behavior. This describes the learning direction, not implemented endpoints.

## Current scope

- A `Book` entity and immutable `ISBN` value object.
- An internal create-book use case with duplicate-ISBN detection.
- Repository and unit-of-work ports, SQLAlchemy persistence adapters, and a books-table migration.
- A `GET /health` endpoint returning `{"status": "ok"}`.

Book use cases are not yet exposed through HTTP. Inventory, ordering, pricing, and authentication are outside the current implementation.

## Quick start

Run from the repository root with Python 3.14+ and `uv` installed:

```bash
uv sync --frozen
cp .env.example .env
chmod 600 .env
# Replace the password placeholders in .env before continuing.
uv run --env-file .env uvicorn bookstore_api.main:app --reload
```

Open `/health` or the generated API documentation at `/docs` on `http://127.0.0.1:8000`.

`APP_DB_PASSWORD` is required when settings are loaded, including application import. The health endpoint does not connect to MySQL. Settings do not automatically load `.env`; see [development](docs/development.md) for configuration and database setup.

To start the API and MySQL through containers:

```bash
podman compose up --build -d
```

First configure `.env` using [.env.example](.env.example); see [development](docs/development.md#local-api-and-database).
Compose starts services but does not apply database migrations. Follow the [migration guide](migrations/README.md) before exercising persistence.

## Tests

```bash
uv run pytest
```

No database or credentials are required. MySQL tests are skipped unless explicitly enabled:

```bash
./scripts/test_integration.py
```

First configure `.env.test` using [.env.test.example](.env.test.example). The command starts a
separate MySQL service, applies migrations, checks schema drift, and runs the persistence tests.
See [testing](docs/testing.md#mysql-integration-setup) for setup and lifecycle details.

## Documentation

Start with [AGENTS.md](AGENTS.md) for task-specific reading and validation commands.

- [Architecture](docs/architecture.md): boundaries, dependencies, transactions, and use-case flow.
- [Coding guidelines](docs/coding-guidelines.md): Python style and practical design rules.
- [Books domain](docs/domain/books.md): terminology, invariants, and unresolved questions.
- [Testing](docs/testing.md): test boundaries, doubles, and database requirements.
- [API conventions](docs/api-conventions.md): existing HTTP behavior and endpoint guidance.
- [Development](docs/development.md): configuration, tools, containers, and troubleshooting.
- [Codex how-tos](docs/ai/codex.md): human reference for command approvals and practical agent setup; excluded from routine agent context.
- [Decision records](docs/decisions/README.md): how to record consequential design decisions.

Tool settings in [pyproject.toml](pyproject.toml), formatting in [.editorconfig](.editorconfig), and dependencies in [uv.lock](uv.lock) remain authoritative for their respective concerns.
