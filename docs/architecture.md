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

## Library integration

Use each framework or library's documented, idiomatic patterns within the required dependency
boundaries. FastAPI supplies the HTTP framework; Dishka, SQLAlchemy, and Alembic supply separate
capabilities. The application needs integration code to connect them, but that code should remain
small and specific to actual application requirements.

When planning features or explaining unfamiliar behavior:

- Check the installed version and official documentation before designing a custom mechanism.
  Reuse supported integrations and lifecycle hooks where they meet the requirement.
- Explain which behavior comes from Python, which comes from the library, and why the documented
  pattern fits. An unfamiliar convention alone is not a reason to replace it with an abstraction.
- Keep application assembly in the composition root and library details in the appropriate adapters.
  Do not introduce a custom container API, provider discovery system, decorators, or lifecycle
  framework when the chosen libraries already supply the needed behavior.
- Add a custom abstraction only for a concrete requirement or architectural boundary that the
  documented patterns do not adequately serve. Explain the gap and tradeoff; record significant
  departures in a decision record.

For example, Dishka's [documented generator providers](https://dishka.readthedocs.io/en/stable/provider/provide.html)
support resource setup and finalization. The engine provider yields one `Engine`, then disposes it
in `finally` when the application container closes. This is a Dishka lifecycle convention built on
Python generators, not a custom resource-management protocol. Retain that pattern rather than
adding a wrapper solely to hide `yield`.

## Current structure

| Location | Responsibility |
|---|---|
| [`domain/books/`](../src/bookstore_api/domain/books) | `Book`, `ISBN`, and local invariants |
| [`application/books/`](../src/bookstore_api/application/books) | Create, read, list, update, and delete use cases, commands/results, and repository port |
| [`application/unit_of_work.py`](../src/bookstore_api/application/unit_of_work.py) | Transaction boundary port |
| [`infrastructure/persistence/`](../src/bookstore_api/infrastructure/persistence) | SQLAlchemy models, mapping, engine/session factories, repository, and unit of work |
| [`api/books/`](../src/bookstore_api/api/books) | Book HTTP schemas and Dishka-enabled router |
| [`di/`](../src/bookstore_api/di) | Composition root: container construction and modular dependency providers |
| [`main.py`](../src/bookstore_api/main.py) | FastAPI factory, container integration and shutdown, and health route |
| [`config.py`](../src/bookstore_api/config.py) | Environment-backed settings |
| [`migrations/`](../migrations) | Database schema evolution |

The implemented repository is in `infrastructure/persistence/repositories/sqlalchemy_book_repository.py`. The similarly named file directly under `infrastructure/` is an incomplete stub. Do not use that stub as the adapter example.

## Current create-book flow

`POST /api/v1/books` calls the use case through the HTTP adapter. `create_app` builds a Dishka
container from settings and the registered providers. The router uses `DishkaSyncRoute` and
requests `FromDishka[CreateBookService]`. Dishka constructs the service from its constructor
annotations, supplying a unit-of-work factory that creates a fresh `SqlAlchemyUnitOfWork` for
each execution. Dependencies are created lazily. Creating the engine does not connect to MySQL;
a health-only request does not construct it. Application shutdown closes the container and
disposes any engine it created.

1. A caller supplies a `CreateBookCommand` to `CreateBookService.execute`.
2. The service constructs `ISBN`, validating its representation and checksum before opening a unit of work.
3. The injected factory supplies a unit of work. Its repository checks for the ISBN.
4. An existing ISBN causes `BookAlreadyExistsError`; the service does not add or commit a book.
5. `Book.create` generates a UUID and validates title and author.
6. The repository adds the book, the service calls `commit`, and the result returns its UUID.

Sources: [service](../src/bookstore_api/application/books/create_book.py), [domain rules](domain/books.md), and [collaboration specifications](../tests/specs/application/books/test_create_book_spec.py).

The HTTP adapter parses its request, builds the command, and returns the created UUID with
HTTP 201. It maps `BookAlreadyExistsError` to HTTP 409. See [API conventions](api-conventions.md)
for the current validation limits.

## Dependency injection

[`di/container.py`](../src/bookstore_api/di/container.py) is the explicit provider registry and
container factory. It registers the supplied `Settings` instance as application context, then
combines the persistence and books providers. This package may import every layer because it
owns assembly; application and domain code must not import Dishka or resolve services themselves.

Providers group related registrations, similar to Laravel service providers:

- [`PersistenceProvider`](../src/bookstore_api/di/providers/persistence.py) owns engine creation
  and disposal, session-factory construction, and the `UnitOfWorkFactory` binding.
- [`BooksProvider`](../src/bookstore_api/di/providers/books.py) registers `CreateBookService`, `GetBookDetailsService`, and `UpdateBookService`
  using constructor autowiring. Add book use cases here; add other cohesive providers when
  additional features require them. Register each provider explicitly in `create_container`.

Settings, engine, session factory, unit-of-work factory, and stateless book services use
`Scope.APP`. A fresh unit of work and session belong to each use-case execution, not the HTTP
request scope. The unit of work still constructs its repositories so they share its session.
Dishka does not control commits or construct domain entities from request data.

`application/unit_of_work.py` names the factory contract with
`type UnitOfWorkFactory = Callable[[], UnitOfWork]`. Services and providers use that same alias;
follow the [type annotation convention](coding-guidelines.md#type-annotations) for complex contracts.

HTTP routers use `DishkaSyncRoute` with direct `FromDishka[ServiceType]` parameters. Avoid custom
dependency annotation aliases and per-service lookups through `Request` or `app.state`.
`setup_dishka` manages the container reference internally. Use a synchronous container while
persistence uses synchronous SQLAlchemy and PyMySQL; the integration opens request scopes, and
the application lifespan closes the root container.

For HTTP tests, `create_app(provider_overrides=[...])` accepts Dishka providers whose replacement
registrations specify `override=True`. Overrides belong to that application's container and must
be supplied before construction. Unit tests continue passing dependencies directly to constructors.
See [decision 0002](decisions/0002-dishka-dependency-injection.md) for alternatives and rationale.

## Transactions and persistence

- The application service decides when the use case succeeds and explicitly requests a commit.
- `SqlAlchemyUnitOfWork` owns the session lifecycle, creates the repository on entry, and closes the session on exit.
- On exit, any remaining transaction is rolled back. Successful context exit alone does not commit.
- Repository methods do not commit. `add` creates an ORM model through `BookMapper` and adds it to the session.
- Mapping reconstructs domain objects using the persisted UUID. It must not generate a replacement identity.
- A database unique constraint protects ISBN uniqueness. The preliminary application lookup alone cannot prevent concurrent duplicates.

The unit of work translates MySQL duplicate-key failures for `uq_books_isbn` into
`BookAlreadyExistsError`; unrelated integrity errors propagate. Loaded books are reconstructed
objects, so changing one does not automatically update its ORM model. The update use case
explicitly calls the repository's `update` operation before committing.

## Collection reads

`ListBooksService` validates query bounds and normalizes optional text filters before opening
a unit of work. The repository applies literal substring filters, combines them with AND,
orders by unique ISBN, and limits rows in SQL. The MySQL adapter explicitly selects a binary
collation for case- and accent-sensitive matching and escapes LIKE wildcard characters.
The fake uses Python substring matching with the same intended semantics; agreement with
MySQL still requires persistence tests.

The service requests one extra row to determine whether more matches exist in the requested
direction, then removes that row. For backward navigation the repository seeks below the
boundary in descending ISBN order; the service reverses the retained rows so all responses
remain ascending. For forward navigation the repository seeks above the boundary. The stored
ISBN boundary does not require its original row to exist.

For a nonempty continuation, the repository checks whether matching rows exist on the opposite
side using SQL `EXISTS` with the same filters. The service uses lookahead and this existence
result to supply nullable navigation positions; it does not assume the incoming cursor proves
that an earlier or later page still exists. Empty pages supply no navigation positions.
The existing `has_more` flag always describes availability in forward display order.

Application pagination records in `application/books/pagination.py` carry an ISBN and direction
without transport encoding. The HTTP codec in `api/books/pagination.py` translates these records
to versioned JSON encoded with unpadded URL-safe Base64. Pydantic query validation rejects
invalid cursors before the service opens a unit of work. Clients retain the current filters
between requests; the cursor does not bind or embed those filters. No snapshot spans requests.

Reads never commit. The HTTP adapter constructs an explicit collection representation without
exposing book versions or ORM models. Route metadata and schemas own the endpoint contract.

This bounds fetched rows, not database scan cost: substring filters may scan the catalog.
ISBN uniqueness supplies the seek index; no schema change is required for this read path.
The accepted [bidirectional keyset pagination decision](decisions/0003-bidirectional-keyset-pagination.md)
records the rationale and limitations.

## Conditional update flow

The HTTP adapter translates `If-Match` into an `UpdateBookCommand`: a set of acceptable versions,
or `None` for the wildcard. The application loads the book, rejects missing or stale records,
and invokes `revise_details`. The domain validates both proposed fields before mutating either.
Omitted fields retain their values. ID and ISBN do not participate in this operation.

The repository copies the revised details into the ORM model and increments its version,
including when the supplied values are unchanged. `BookModel` configures SQLAlchemy's
`version_id_col` and disables automatic generation because the repository increments explicitly.
During `flush`, SQLAlchemy emits the equivalent of:

```sql
UPDATE books SET title = :title, author = :author, version = :next_version
WHERE id = :id AND version = :previous_version;
```

Only a matching version can update the row. If no row matches, SQLAlchemy raises
`StaleDataError`; the repository translates that into `BookVersionConflictError`. This closes
the race between reading a version and writing the changes. The earlier Python comparison
alone cannot provide that guarantee. See SQLAlchemy's
[version counter documentation](https://docs.sqlalchemy.org/en/20/orm/versioning.html).

Flushing checks the write without committing it. The service commits only after `update`
succeeds. On failure or an unfinished transaction, the unit of work rolls back and closes the
session. Version checks cover these ORM writes; direct SQL and bulk writes must implement
their own predicate and version increment. A wildcard bypasses the client's version check,
but competing writes after the application's read can still produce a conflict.

HTTP tests use fakes. The independent-connection MySQL regression tests live in
[`test_sqlalchemy_book_updates.py`](../tests/integration/persistence/test_sqlalchemy_book_updates.py); their presence
does not assert a live run. See [testing](testing.md) for execution and verification limits.

## Conditional repository deletion

The repository's `delete(book)` operation executes a single SQL DELETE with predicates for
both `book.id` and `book.version`, using the session's existing transactional connection.
It does not reload an ORM model or commit. An affected-row count other than one raises
`BookVersionConflictError`, covering a concurrent update or deletion after the service's read.
The application still checks client expectations against the loaded entity before deletion.

This explicit statement supplies its own version predicate; it does not use ORM automatic
version checking or synchronize loaded ORM instances. Each use case owns a short-lived unit
of work, and callers should use repository reads rather than retained ORM instances after deletion.
The caller must commit; leaving the unit of work without committing rolls back the deletion.
The DELETE endpoint translates HTTP preconditions into application version expectations.
Its route metadata defines the response contract; [API conventions](api-conventions.md#conditional-writes)
defines the shared precondition policy.

## Change guidance

Keep invariants on entities and value objects; keep orchestration in use cases. Add ports for needed external capabilities, not for every class. Do not add generic repositories, event buses, CQRS infrastructure, or additional bounded contexts without a concrete requirement.

Document meaningful boundary changes in a [decision record](decisions/README.md). Keep domain meaning in [books](domain/books.md), HTTP policy in [API conventions](api-conventions.md), and migration mechanics in the [migration guide](../migrations/README.md).
