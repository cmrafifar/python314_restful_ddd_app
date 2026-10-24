# Bookstore REST API — Senior Engineering Tutorial

**Canonical course specification**  
**Edition:** 2026-10-20  
**Primary implementation:** Python 3.14  
**Portable curriculum:** Can be reimplemented in TypeScript or another ecosystem  
**Project progress:** See [the task list](docs/task-list.json) for completed work, current focus, remaining tasks, and verification evidence.

> This document defines the **course**, not a complete transcript or exact snapshot of the repository. An agent replicating the tutorial from scratch should start at Lesson 1. An agent resuming the current Python project should use [the task list](docs/task-list.json) for progress and inspect the actual repository to verify implementation state.

---

## 1. Abstract

Build a production-oriented **Bookstore REST API** while learning how an experienced backend engineer applies **Domain-Driven Design (DDD), Hexagonal Architecture (ports and adapters), dependency inversion, explicit transaction management, relational persistence, automated testing, security, concurrency, and deployment** in a modern programming language.

The application starts as a small **Book Catalog** domain: ISBN value objects, book entities, use cases, repositories, and HTTP endpoints. It grows incrementally into a realistic service with queries and pagination, external integrations, authentication, authorization, Redis, domain events, reliable message delivery, observability, and deployment infrastructure. Each capability must earn its architectural complexity through a concrete requirement.

This is **not** a quick CRUD walkthrough or a mechanical translation of patterns from another language. It is a guided engineering course focused on *why* a design is chosen, where it can fail, how to test it, and when an alternative is more appropriate.

The curriculum is **language-neutral** at the lesson and learning-objective level. Implementation-specific material belongs in a language profile (Python or TypeScript), so the same architectural problems and acceptance criteria can be taught in either ecosystem.

### Intended learner

An experienced software engineer familiar with PHP, Laravel, DDD, Hexagonal Architecture, and PHPSpec-style behavioral testing, learning a new language and ecosystem at senior/backend/full-stack depth.

### Learning outcomes

By the end of the course, the learner should be able to:

1. Design use cases and HTTP contracts while preserving clear architectural boundaries.
2. Model entities, value objects, aggregates, and invariants pragmatically.
3. Express ports with the language's type system; inject adapters through a composition root.
4. Make transaction ownership, session lifecycles, isolation, and consistency explicit.
5. Test pure domain behavior, collaborations, real persistence, and API behavior at appropriate boundaries.
6. Handle concurrent writes, uniqueness races, idempotency, pagination, timeouts, and retries.
7. Implement secure identity integration, authorization, caching, rate limiting, and reliable event publication.
8. Measure synchronous versus asynchronous execution rather than assume performance advantages.
9. Operate, observe, containerize, and deploy a service with CI/CD and infrastructure as code.
10. Explain architectural tradeoffs and defend them in code review.

---

## 2. Course structure and syllabus

**Planned scope: 12 lessons total.** The syllabus describes learning goals, not completion status or authorization to implement every topic. Component breakdowns after Lesson 3 are a suggested teaching plan, adjustable without changing the learning objectives. Consult [the task list](docs/task-list.json) for accepted work and current progress.

**At the start of every lesson:** suggest a concise, descriptive Git branch name such as `feature/bookstore-http-api`. At the end of a completed component or lesson: provide a professional **Conventional Commit** subject and explanatory body. Never claim that unobserved tests or commits succeeded.

| Lesson | Topic | Essential outcomes | Suggested Git branch |
|---|---|---|---|
| **1** | Project foundation | Package/tooling setup; configuration; application factory; health endpoint; containerized local environment; basic tests | `feature/project-foundation` |
| **2** | Domain and application core | ISBN value object; Book entity; command/result DTOs; repository port; create-book use case; fake and collaboration tests | `feature/book-domain` |
| **3** | MySQL persistence and application wiring | Engine/session factory; ORM mapping; migrations; repository adapter; Unit of Work; MySQL integration tests; dependency injection; POST endpoint | `feature/persistence-and-di` |
| **4** | REST resources and query design | Read/list/update/delete where justified; HTTP contracts; pagination, sorting, filtering, validation, conditional requests | `feature/book-query-api` |
| **5** | Advanced testing and concurrent correctness | Test pyramid and boundaries; transactions; test isolation; concurrency races; deterministic fixtures; contract tests | `test/advanced-bookstore-coverage` |
| **6** | External services and resilience | Typed HTTP clients; outbound ports/adapters; timeouts, retries, backoff, error translation, resilience tests | `feature/external-integrations` |
| **7** | Authentication and authorization | Educational local credentials/token flows; authorization; production-oriented OAuth2/OIDC, JWKS, token validation | `feature/authentication-authorization` |
| **8** | Redis and distributed concerns | Cache-aside; invalidation; rate limiting across multiple instances; failure semantics | `feature/redis-rate-limiting` |
| **9** | Advanced DDD and reliable events | Aggregate boundaries; domain events; transaction outbox; consumers, idempotency, eventual consistency | `feature/domain-events-outbox` |
| **10** | Async execution and performance | Async language/runtime patterns; async DB and HTTP clients where appropriate; concurrency limits; benchmarks | `feature/async-performance` |
| **11** | Production readiness | Structured logs, metrics, traces, health/readiness, configuration/secrets, CI, security, container hardening | `chore/production-readiness` |
| **12** | Cloud deployment | AWS architecture choices; Kubernetes deployment/services/ingress/jobs; OpenTofu; rollout/operations | `infra/aws-kubernetes-deployment` |

### Lesson 1 — Project foundation

- Create a working service skeleton and reproducible dependency lockfile.
- Organize source and tests; explain packaging and module imports.
- Implement configuration management and an application factory.
- Provide `/health` and an OpenAPI-capable HTTP application.
- Build and run locally using Podman and Compose.
- Start unit and HTTP functional tests; establish linting and type checks.

### Lesson 2 — Domain and application core

- Define a **Book Catalog** business vocabulary and scope.
- Build an ISBN-13 value object with checksum validation.
- Build a Book entity with UUID identity and behavioral invariants.
- Discuss object identity versus domain identity.
- Introduce an application command and result separate from HTTP DTOs.
- Create the repository port, `CreateBookService`, fake repository, and collaborator specifications.
- Distinguish state assertions from mock interaction assertions; both can be unit tests.

### Lesson 3 — Persistence, transactions, and DI

1. Configure MySQL and typed SQLAlchemy engine/session factories.
2. Declare persistence models separate from domain objects.
3. Manage schema evolution through Alembic migrations.
4. Implement domain-to-persistence mapping and `SqlAlchemyBookRepository`.
5. Introduce the typed `UnitOfWork` port and `SqlAlchemyUnitOfWork`, with explicit `commit()` and rollback-on-exit semantics.
6. Test repository/UoW behavior against **real MySQL** with a dedicated test database, SAVEPOINT-based isolation, and a separate actual-commit test.
7. Compose the application and expose `POST /api/v1/books`; validate 201/409/422 contracts, UUID response IDs, and uniqueness-race handling.

**Python project update:** Dishka is now the chosen DI container. Its adoption supersedes older illustrative wiring based only on `app.state`, FastAPI `Depends`, or manually constructed services. Preserve the architecture, but inspect the actual Dishka providers/scopes before giving code. Do not invent the project's current Dishka implementation.

### Lesson 4 — REST and query design (proposed components)

- Design read-by-ID and list endpoints, response schemas, HTTP status codes, and error contracts.
- Introduce read-oriented repository ports and query DTOs where valuable.
- Compare OFFSET pagination to keyset pagination and stable compound cursors.
- Add filtering, ordering, bounds, and query validation.
- Implement updates with domain invariants and consider optimistic locking.
- Address conditional requests, caching headers, and DELETE semantics when appropriate.

### Lesson 5 — Advanced testing (proposed components)

- Distinguish unit, collaboration/spec, integration, functional, and contract tests.
- Make fixtures deterministic and parallel-safe.
- Test transaction rollback after flush, uniqueness races, and failure translation.
- Exercise realistic multi-request and multi-connection behavior.
- Evaluate coverage and mutation testing without substituting percentage targets for quality.

### Lesson 6 — External integrations (proposed components)

- Define an outbound client port and HTTP adapter.
- Handle deadlines, timeouts, retries, backoff, and cancellation correctly.
- Classify transient and permanent failures; consider idempotency.
- Test with controlled responses and failure injection.

### Lesson 7 — Security and identity (proposed components)

- Explain authentication, authorization, sessions, bearer tokens, and JWT claims.
- Implement educational local authentication safely, including password hashing and token expiration.
- Integrate external OIDC; validate issuer, audience, signature, expiry, and JWKS rotation.
- Apply authorization policies to use cases; test deny-by-default behavior.
- Do not position custom token issuance as preferable to mature identity providers in production.

### Lesson 8 — Redis and distributed systems (proposed components)

- Integrate a Redis adapter with explicit failure handling.
- Use cache-aside and examine stale reads and invalidation.
- Design distributed rate limits for multiple workers; test boundary cases.
- Consider eviction, reconnects, and graceful degradation.

### Lesson 9 — Advanced DDD and messaging (proposed components)

- Introduce new domain behaviors before introducing domain events.
- Revisit consistency and aggregate boundaries.
- Implement a transactional outbox and message publication.
- Address at-least-once delivery, duplicate handling, idempotent consumers, and ordering.
- Explain why local database transactions do not atomically commit to an independent message broker.

### Lesson 10 — Async and benchmarking (proposed components)

- Understand event loops, tasks/promises, blocking I/O, and concurrency.
- Change **selected** paths to async DB and HTTP clients.
- Measure throughput, latency, pool saturation, and operational cost.
- Explain tradeoffs rather than declaring async universally better.

### Lesson 11 — Production readiness (proposed components)

- Structured logging, correlation IDs, metrics, tracing, readiness/liveness.
- Secret management, environment validation, defensive error handling.
- Static checks, test automation, build provenance, deployment pipelines.
- Harden containers and review operational failure scenarios.

### Lesson 12 — Cloud deployment (proposed components)

- Select AWS services deliberately and assess managed-platform alternatives.
- Provision reproducible resources using OpenTofu.
- Deploy with Kubernetes workloads, services, ingress/egress, secrets, migrations, CronJobs, and Jobs as required.
- Evaluate rollout, scaling, monitoring, backup, recovery, and rollback.
- Conclude with a full architecture review and operational runbook.

---

## 3. Technology profiles

The **course syllabus and architecture principles are shared**; tooling is selected per language. Do not force a one-to-one mapping of libraries when the language offers a better idiom.

### 3.1 Python 3.14 profile — committed course stack

| Concern | Library/framework | Role |
|---|---|---|
| Language | Python 3.14 | Typed Python implementation |
| Dependency/project manager | **uv** | Environment, installation, lockfile, execution |
| HTTP | **FastAPI** | Routing, request lifecycle, OpenAPI |
| API serialization/validation | **Pydantic 2** | HTTP request/response models |
| Configuration | **pydantic-settings** | Typed settings with `APP_` environment prefix |
| Dependency injection | **Dishka** | Explicit DI providers and scopes; current project choice |
| Persistence | **SQLAlchemy 2** | ORM/Core, Engine, Session, transactions |
| Database | **MySQL 8.4 / InnoDB** | Relational integrity and transactional storage |
| Driver | **PyMySQL** | Initial synchronous MySQL driver |
| Migrations | **Alembic** | Reviewed schema changes |
| Unit/spec testing | **pytest**, `unittest.mock.create_autospec` | State-based tests and PHPSpec-style collaboration specifications |
| HTTP testing | **HTTPX**, FastAPI TestClient | Functional and adapter tests |
| Lint/format | **Ruff** | Linting and formatting |
| Static typing | **BasedPyright** | Standard globally; strict domain/application |
| Cache/rate limiting | **Redis** | Future distributed concerns |
| Containers | **Podman + Compose** on Fedora | Local API and MySQL runtime |
| Cloud/infrastructure | **AWS, Kubernetes, OpenTofu** | Final deployment |

Additional rules:
- `pyproject.toml` is the central tooling declaration; commit `uv.lock`.
- Set BasedPyright `typeCheckingMode = "standard"` globally and strict diagnostics for `src/bookstore_api/domain` and `src/bookstore_api/application`.
- Use Python `Protocol` for ports, `dataclass(frozen=True, slots=True)` for suitable value objects/commands, explicit instance annotations for ordinary classes, and `ClassVar` for shared constants.
- Keep initial application services and DB access synchronous; introduce async later with evidence.
- Commands use `uv run pytest`, `uv run basedpyright`, `uv run ruff check .`, and `uv run ruff format --check .`.
- Use `podman` / `podman compose`, not Docker CLI. For Fedora SELinux, use appropriate bind labels such as `./src:/app/src:ro,z` where safe.
- Never put credentials into committed files, example transcripts, or command histories with real passwords.

### 3.2 TypeScript profile — adaptation guide, not an agreed stack

The following are **candidate tools**, not decisions already made for a TypeScript implementation. Select and document them before Lesson 1.

| Concern | Candidate choices | Selection principle |
|---|---|---|
| Runtime | Node.js LTS | Prefer a maintained release |
| Language/compiler | TypeScript in strict mode | Explicit types and boundaries |
| Package manager | pnpm / npm | Reproducible lockfile |
| HTTP | Fastify / NestJS / Express | Avoid framework logic leaking into domain/application |
| Request schemas | Zod / TypeBox | Transport validation separate from domain invariants |
| DI | Explicit composition or a container | Match lifetimes and scope to use cases |
| Persistence | Prisma / Drizzle / TypeORM / Kysely | Evaluate transaction APIs, mapping, and domain independence |
| Database | MySQL 8.4 / InnoDB | Hold persistence requirements constant |
| Migrations | Tool matching selected DB stack | Explicit, reviewed migrations |
| Tests | Vitest / Jest | Unit/spec and integration tests |
| HTTP testing | Framework test client / HTTP client | Exercise transport boundary |
| Lint/format | ESLint + formatter | Repeatable style |
| Cache/rate limiting | Redis client | Distributed correctness |
| Runtime/containers/deploy | Podman, AWS, Kubernetes, OpenTofu | Preserve operating scenarios |

**Cross-language fidelity:** Teach the same domain rules, HTTP contracts, transaction outcomes, testing scenarios, and failure modes. Change only the implementation idioms. For example, TypeScript `interface` is not identical to Python's runtime-visible `Protocol`, and an ORM transaction callback may not have the same semantics as a manually managed SQLAlchemy `Session`. Explain these differences explicitly.

---

## 4. Architecture specification

### 4.1 Architectural style

Use **DDD (pragmatically)** plus **Hexagonal Architecture**:

```text
Inbound adapters                   Application                    Outbound adapters
────────────────                   ───────────                    ────────────────

HTTP route + schema ────────>  Use case / command  ────────>  Repository port
                                      │                              ▲
                                      v                              │
                               Domain model                    SQLAlchemy adapter
                                      │                              │
                           Entities / value objects                  v
                                                                MySQL database

Composition root / DI container assembles the graph.
Unit of Work controls transaction scope around participating repositories.
```

**Dependency direction:** Domain imports no framework or database library. Application imports domain and abstract ports, not FastAPI, Pydantic, SQLAlchemy, Dishka, or MySQL. Infrastructure implements application-required ports. The outer HTTP adapter maps transport DTOs to application DTOs and results. The **composition root** is intentionally allowed to reference the concrete components.

### 4.2 Current domain and contracts

**Initial bounded context:** Book Catalog.

- `ISBN`: immutable ISBN-13 value object; exactly 13 ASCII decimal digits with valid check digit.
- `Book`: regular domain entity with `UUID` identity, ISBN, title, author, and domain methods/invariants.
- `CreateBookCommand`: independent application input DTO.
- `CreateBookResult`: application output carrying `book_id: UUID`.
- `BookRepository`: application port providing `get_by_id`, `get_by_isbn`, and `add`.
- `CreateBookService`: orchestration of ISBN validation, existing-book check, book creation, repository write, and commit.
- `UnitOfWork`: application port exposing the typed `books: BookRepository` and explicit `commit()` in a context-managed lifetime.
- `SqlAlchemyBookRepository` + mapper + persistence model: infrastructure adapter.
- `SqlAlchemyUnitOfWork`: creates/closes a Session, supplies the repository, commits explicitly, and rolls back uncommitted work on exit.

**Decision retained for now:** The UoW directly exposes `books: BookRepository`. This is not a universal repository registry. Multiple repositories can be added later, sharing **one Session** when an atomic use case requires it. Do not redesign ahead of a demonstrated need.

### 4.3 Transactions and consistency

- Transaction boundaries are owned by **application use cases**; repositories must not independently commit.
- `Session.add()` does not by itself commit. `flush()` sends SQL into an uncommitted transaction. `commit()` flushes and commits. `rollback()` undoes only uncommitted work.
- If `commit()` succeeds and later code raises an exception, the commit stays committed.
- Application uniqueness pre-checks are user-friendly but race-prone. **MySQL's unique constraint is authoritative**.
- Translate **recognized** uniqueness errors into an application conflict; do not indiscriminately catch every DB `IntegrityError` as a duplicate ISBN.
- Decide transaction boundaries and isolation based on use-case requirements; avoid distributed transactions by default.
- Domain objects and ORM persistence models are distinct; do not return SQLAlchemy models as domain entities.

### 4.4 HTTP boundary and expected behavior

The Book API currently targets:

| Endpoint | Purpose | Expected behavior |
|---|---|---|
| `GET /health` | Basic process health | Success without coupling to business logic |
| `POST /api/v1/books` | Create book | `201` with UUID ID |
| `POST /api/v1/books` with duplicate ISBN | Conflict | `409` |
| Invalid request payload | Validation failure | `422` in Python/FastAPI profile |

The exact treatment of invalid *domain* ISBN values must be explicit: arbitrary domain `ValueError` exceptions are not automatically HTTP `422`. Distinguish transport validation from domain validation and translate intentionally.

Read/list/update endpoints come later.

### 4.5 DI and lifecycle

- Configure dependency graphs in the **composition root**, currently using **Dishka** for Python.
- Application services depend on ports and factories, not DI framework types.
- An application-wide engine/pool and session factory may be reused.
- Each use-case invocation should obtain its own Unit of Work and SQLAlchemy Session.
- Do **not** share an active SQLAlchemy Session across concurrent requests.
- Define and verify provider scope, application startup/shutdown, and engine disposal.
- Keep dependency overrides or equivalent mechanisms available for isolated HTTP tests.

### 4.6 Domain growth and complexity rules

- Add aggregates, services, events, CQRS separation, read replicas, or event-driven workflows **only when use cases warrant them**.
- Keep bounded contexts conceptually separate. Do not create a single global repository locator because the service may someday grow.
- Make cross-aggregate transactions an explicit decision; consider eventual consistency when crossing independently deployed boundaries.
- Prefer clear code and testable behavior to pattern ceremony.

---

## 5. Testing strategy

The curriculum intentionally includes **both state-based unit tests and PHPSpec-style collaboration specs**, even when they exercise the same use case, because they teach different perspectives. Both are unit tests.

| Test category | Test subject | Doubles / real dependencies | Key assertion |
|---|---|---|---|
| Domain unit | `ISBN`, `Book` | No database | Invariants, values, state transitions |
| Application state unit | `CreateBookService` | Fake repository + fake UoW | Observable outcomes |
| Collaboration/spec unit | `CreateBookService` | `create_autospec` mocks | Correct calls, no unwanted commit |
| Persistence integration | Repository, mapper, UoW | Actual SQLAlchemy + MySQL | Persistence, rollback, constraints |
| HTTP functional | FastAPI route | TestClient with mocked app service or real stack | HTTP contract and serialization |
| End-to-end | Deployed/local service | Real process/services | End-to-end behavior |

### Integration-test isolation

- Test against a dedicated `bookstore_test` database, never the development database.
- Apply **Alembic migrations**; don't silently bypass migrations using `Base.metadata.create_all()` as the test schema source.
- For suitable tests, pytest owns an outer transaction and injects sessions configured with `join_transaction_mode="create_savepoint"`.
- A UoW `commit()` releases the SAVEPOINT; pytest rolls back the **outer** transaction at teardown.
- These tests do **not** prove durable commits across connections. Add a separate real-commit test with explicit cleanup.
- Avoid shared/fixed ISBNs in parallel tests; generate valid, unique test identifiers.
- Test flushed rollback and concurrent uniqueness separately.
- MySQL DDL may implicitly commit, so do not casually run schema migrations inside a rollback-scoped fixture.

### Mocking guidance

`create_autospec` checks method names and call signatures more rigorously than plain `Mock(spec=...)`, but it does not reproduce persistence or enforce full runtime generic annotations. Never assume a passing mock test proves transaction correctness.

---

## 6. Engineering conventions and delivery workflow

### 6.1 Component-by-component teaching contract (mandatory for any agent)

1. **Do not dump an entire lesson** unless explicitly requested. Teach **one component at a time**.
2. Before starting **every next component**, ask: **“Are you ready to proceed to Lesson N, Component M: [title]?”** Wait for an explicit yes. The same applies between lessons.
3. After presenting a component, stop and invite questions. Do not interpret a correct quiz answer as permission to proceed.
4. Knowledge checks must have **no answer preselected** and must not reveal the answer before submission. If interactive UI is used, disable submission until a choice is made.
5. Explain design decisions, alternatives, failure modes, and tradeoffs at senior-engineer depth. Welcome counterarguments; do not rubber-stamp choices.
6. Do not quietly change earlier architecture or libraries; distinguish planned changes from the code actually applied.
7. On the first response of **each lesson**, recommend a descriptive Git branch name **at the top**.
8. After a completed component/lesson, provide an appropriate **Conventional Commit** subject and bullet-point body; do not imply a commit happened automatically.
9. When asked to edit a configuration file, provide the **complete final file** rather than disconnected snippets, except where the learner explicitly requests a small excerpt. Avoid needless full Compose reposts.
10. Ask one focused follow-up question at a time. If the learner has unresolved questions, remain on the current component.

### 6.2 Recommended teaching unit

For each component:

1. **Goal and prerequisite:** What problem are we solving, and what must already exist?
2. **Design rationale:** Relevant domain and architecture tradeoffs.
3. **Implementation:** File paths, complete applicable definitions, and minimal working code.
4. **Testing:** State/spec/integration/HTTP tests as appropriate.
5. **Commands:** Exact local run and verification instructions.
6. **Failure analysis:** At least one realistic pitfall or race when relevant.
7. **Knowledge check:** Only when appropriate, no preselected answer.
8. **Review and pause:** Resolve learner questions.
9. **Conventional Commit:** Only when the work is ready to consider completed.
10. **Permission to advance:** Explicitly request approval for the next named component.

### 6.3 Git conventions

Use lowercase, concise, descriptive branch names with a prefix such as `feature/`, `test/`, `fix/`, `refactor/`, or `infra/`. Branch-per-lesson is the default, not a requirement to merge on every component.

Example commit:

```text
feat(persistence): introduce explicit unit of work

- Define the transaction abstraction in the application layer.
- Implement SQLAlchemy-backed session lifecycle and commit behavior.
- Keep repositories independent of transaction commits.
- Add state-based tests and collaboration specifications.
```

### 6.4 Project-quality bar

- Prefer realistic, runnable examples over pseudo-production abstractions.
- Make imports, dependency versions, file locations, and environment assumptions explicit.
- Never claim tests pass unless observed.
- Check correctness of transaction ownership, error mapping, object lifecycle, and concurrency.
- Maintain type-checker cleanliness without blanket ignores.
- Favor design decisions that remain understandable in another implementation language.

---

## 7. Cross-language replication contract

An agent teaching this course in TypeScript must preserve the **same learning sequence and behavioral requirements** rather than translating Python statements line-for-line.

### Stable across language editions

- Book Catalog domain vocabulary and invariants.
- ISBN-13 algorithm and UUID book identity.
- Separation of transport DTOs, application DTOs, entities, and persistence models.
- Repository abstractions and transaction boundaries.
- MySQL schema, uniqueness guarantees, and concurrent-write scenarios.
- REST routes, relevant status codes, and response semantics.
- State-based, collaboration/spec, integration, and HTTP tests.
- Authentication, Redis, outbox, async, operations, and deployment learning goals.
- Component gates, code-review standards, and Git conventions.

### Allowed to differ by language

- Framework, DI library, migration tool, ORM/query builder, package manager, test runner.
- Syntax for interfaces and protocols.
- Async/runtime model and transaction APIs.
- Package layout and file naming when idiomatic.
- Configuration and lifecycle primitives.

### Required artifacts in each language edition

Each language edition should maintain:

- `tutorial.md` — shared course spec and language profile.
- `README.md` — how to run the concrete implementation.
- A machine-readable dependency manifest and lockfile.
- Project-specific `architecture.md` or ADRs for major deviations/decisions.
- A task list recording completed components, unresolved issues, and verification evidence; this project's canonical progress file is [docs/task-list.json](docs/task-list.json).
- Tests and migration instructions.

### Suggested agent startup procedure

If beginning from scratch:

1. Confirm the implementation language and chosen stack.
2. Read this specification and explicitly identify candidate-vs-committed tools.
3. Start at Lesson 1, Component 1; recommend the lesson's branch.
4. Teach in increments and pause at each gate.

If resuming existing code:

1. Read this course specification, [the task list](docs/task-list.json), and the repository's current source/tests/config.
2. Reconcile task-list claims with the **observed repository** and the learner's latest direct decisions.
3. State the current lesson/component, unresolved questions, and notable unverified assumptions.
4. Continue the **current** component only; obtain approval before advancing.

---

## 8. Source-of-truth rules

[docs/task-list.json](docs/task-list.json) is the single progress record for this project. Maintain completed tasks, current focus, remaining work, and verification evidence there. Do not duplicate progress snapshots or next-task instructions in this curriculum. Completion status does not imply a fresh test run; consult recorded verification limits and the current checkout.

**Authority order when there is a conflict:**

1. Learner's newest explicit instruction or architectural decision.
2. Current checked-out repository source and tests (for actual code state).
3. The task list for progress; ADRs and project documentation for established decisions.
4. This curriculum (for course structure and standards).
5. Historical examples, which may be superseded.

Historical handoffs provide background only. Use the task list and current source/tests to determine where to resume.

---

## 9. Final deliverables

At course completion, prepare:

1. A runnable Bookstore API implementation with tests and migrations.
2. A consolidated tutorial documenting design rationale, alternatives, and common failures.
3. A practical language cheat sheet, including Python-vs-PHP comparisons for the Python edition; optionally TypeScript-vs-Python/PHP comparisons for the TypeScript edition.
4. A testing reference with a realistic example distinguishing state-based unit tests, collaboration specifications, database integration tests, and HTTP functional tests.
5. A deployment/operations guide for the final environment.
6. A concise architecture decision record of tradeoffs made during the course.

The objective is **transferable engineering judgment**, not a fixed collection of libraries or patterns.
