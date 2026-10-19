# Architecture

Read this document when adding behavior, changing a dependency, or deciding where code belongs. This is a small learning project: introduce architectural mechanisms only when current behavior needs them.

## Required dependency rules

Dependencies point toward the business core:

```text
HTTP adapter -> application -> domain
Persistence adapter -> application ports and domain
Composition root -> concrete adapters and application
```

- Domain code may use the Python standard library and other domain code. It must not import application, infrastructure, FastAPI, Pydantic, SQLAlchemy, or Alembic.
- Application code may use domain code and its own ports. It must not import concrete adapters or framework types.
- Ports describe capabilities the application needs, using domain or application types. Application owns the existing repository and unit-of-work ports.
- Adapters translate between external representations and core types. ORM models and HTTP schemas must not become domain entities.
- The composition root may depend on all layers to wire concrete implementations. Business decisions do not belong there.

These are project rules. Existing incomplete code is not a precedent for bypassing them.

## Current structure

| Location | Responsibility |
|---|---|
| [`domain/books/`](../src/bookstore_api/domain/books) | `Book`, `ISBN`, and local invariants |
| [`application/books/`](../src/bookstore_api/application/books) | Create command, result, service, and repository port |
| [`application/unit_of_work.py`](../src/bookstore_api/application/unit_of_work.py) | Transaction boundary port |
| [`infrastructure/persistence/`](../src/bookstore_api/infrastructure/persistence) | SQLAlchemy models, mapping, engine/session factories, repository, and unit of work |
| [`main.py`](../src/bookstore_api/main.py) | FastAPI factory and health route; intended composition root |
| [`config.py`](../src/bookstore_api/config.py) | Environment-backed settings |
| [`migrations/`](../migrations) | Database schema evolution |

The implemented repository is in `infrastructure/persistence/repositories/sqlalchemy_book_repository.py`. The similarly named file directly under `infrastructure/` is an incomplete stub. Do not use that stub as the adapter example.

## Current create-book flow

The use case is called directly by tests. There is no create-book HTTP route or production wiring for this flow yet.

1. A caller supplies a `CreateBookCommand` to `CreateBookService.execute`.
2. The service constructs `ISBN`, validating its representation and checksum before opening a unit of work.
3. The injected factory supplies a unit of work. Its repository checks for the ISBN.
4. An existing ISBN causes `BookAlreadyExistsError`; the service does not add or commit a book.
5. `Book.create` generates a UUID and validates title and author.
6. The repository adds the book, the service calls `commit`, and the result returns its UUID.

Sources: [service](../src/bookstore_api/application/books/create_book.py), [domain rules](domain/books.md), and [collaboration specifications](../tests/specs/application/books/test_create_book_spec.py).

A future HTTP adapter should parse its request, call this application boundary, and map the result or known errors to HTTP. It must not query SQLAlchemy or duplicate book invariants.

## Transactions and persistence

- The application service decides when the use case succeeds and explicitly requests a commit.
- `SqlAlchemyUnitOfWork` owns the session lifecycle, creates the repository on entry, and closes the session on exit.
- On exit, any remaining transaction is rolled back. Successful context exit alone does not commit.
- Repository methods do not commit. `add` creates an ORM model through `BookMapper` and adds it to the session.
- Mapping reconstructs domain objects using the persisted UUID. It must not generate a replacement identity.
- A database unique constraint protects ISBN uniqueness. The preliminary application lookup alone cannot prevent concurrent duplicates.

Current limitations: database uniqueness failures are not translated to `BookAlreadyExistsError`. Loaded books are reconstructed objects; changing one does not automatically update its ORM model. There is no repository update operation or rename use case.

## Change guidance

Keep invariants on entities and value objects; keep orchestration in use cases. Add ports for needed external capabilities, not for every class. Do not add generic repositories, event buses, CQRS infrastructure, or additional bounded contexts without a concrete requirement.

Document meaningful boundary changes in a [decision record](decisions/README.md). Keep domain meaning in [books](domain/books.md), HTTP policy in [API conventions](api-conventions.md), and migration mechanics in the [migration guide](../migrations/README.md).
