# Questions and Answers

Confirmed answers from the project learning sessions. Add each answered question with its
confirmed explanation; correct misunderstandings before recording the answer.
During a quiz, record the resolved question and answer when the user confirms readiness for the
next question, or when the user explicitly asks to record it. Do not duplicate existing entries.

## 1. When Dishka reaches `yield engine`, does it give the consumer an `Engine` instance or a generator?

The consumer receives the yielded `Engine` instance. Calling the provider creates a Python
generator, but Dishka advances that generator and supplies its yielded value to the dependency
that needs it. The generator remains paused until its owning scope closes.

## 2. With `Scope.APP`, is the engine disposed when an HTTP request finishes or when the application container closes?

The engine is disposed when the application container closes. Finishing an HTTP request does
not close the application scope. Dishka retains the engine for reuse across requests and resumes
the provider during container cleanup, executing its `finally` block and `engine.dispose()`.

## 3. When does the application container close? Does server shutdown close it?

In this application, FastAPI's lifespan cleanup calls `container.close()` during graceful server
shutdown. That triggers cleanup for resources the container created, including engine disposal.
The same cleanup runs when a context-managed `TestClient` exits. Forced termination, such as
`SIGKILL`, cannot run Python cleanup.

## 4. The engine is shared across requests. Are database sessions also shared?

Each unit of work gets a fresh session when it enters its context. The session factory is shared,
but it creates a new session for each unit of work. The unit of work closes its session on exit.
Sharing the engine and session factory does not mean sharing active sessions or transactions.

## 5. Who decides when to commit a database transaction: Dishka, the repository, or the application service?

The application service decides when to commit by explicitly calling `uow.commit()`. The unit of
work performs the commit through its SQLAlchemy session. This is a deliberate architectural
choice: application services own transaction decisions, repositories do not commit, and Dishka
supplies dependencies without deciding transaction outcomes.

## 6. Is there a clearer way to annotate `uow_factory: Callable[[], UnitOfWork]`, perhaps using a lambda?

Use a descriptive type alias for this complex annotation:

```python
type UnitOfWorkFactory = Callable[[], UnitOfWork]
```

Then annotate the constructor parameter as `uow_factory: UnitOfWorkFactory`. The alias names the
contract: a callable that takes no arguments and returns a `UnitOfWork`. It contains no framework
injection instructions and does not create an object.

A lambda creates a callable implementation, not a type annotation. The existing
`partial(SqlAlchemyUnitOfWork, session_factory)` implements the factory contract by pre-supplying
the session factory; each subsequent call creates a new unit of work.

The project uses Python `type` aliases for complex annotations when a descriptive name improves
clarity. Define aliases beside their owning contracts and use them consistently across consumers,
providers, and tests. Keep simple annotations direct. The installed Dishka version supports this
alias in registration and resolution; application and domain code remain independent of Dishka.
For overrides, use a provider function annotated `-> UnitOfWorkFactory` and let Dishka infer its
registrations. In Dishka 1.10.1, explicitly setting `provides=UnitOfWorkFactory` alone does not
override the underlying callable type used for constructor resolution. See the
[testing guidance](docs/testing.md) for the verified override pattern.

## 7. When the service calls `self._uow_factory()`, what does it return, and when is the database session created?

Calling `self._uow_factory()` creates a new `SqlAlchemyUnitOfWork`. Its constructor receives the
session factory; it does not create the session yet. Entering `with self._uow_factory() as uow`
calls the unit of work's `__enter__()`, which creates a fresh SQLAlchemy `Session`.

Dishka injects the unit-of-work factory into the service. The service calls that factory, and the
unit of work manages its session. Dishka does not manage each unit of work or its session.

## 8. What happens if a service raises an exception inside the unit-of-work context before calling `uow.commit()`?

The uncommitted transaction is rolled back, so its pending changes are not persisted. The unit
of work closes the session when the context exits. The exception continues to propagate unless
application code handles it.

## 9. Why can concurrent requests share an application-scoped `CreateBookService` while using separate database sessions?

The shared service stores a unit-of-work factory, not an active unit of work or session. Each
`execute()` call calls the factory to create a separate unit of work. Entering that unit of
work's context creates its own session. Calling the factory is an ordinary function call, not
a Python `yield` operation.

This separation is not specific to Python or threads. Concurrent requests within one process
can share application-scoped objects, whether concurrency involves asynchronous tasks or
threads. A SQLAlchemy `Session` contains mutable transaction state and must not be shared across
concurrent units of work. Separate worker processes have separate containers and objects.

Traditional PHP request lifecycles make shared application state less visible. Long-lived
Laravel workers, such as Octane, require similar care. Share factories while keeping active
sessions and transactions local to each unit of work.

## 10. Why would storing the current unit of work on `self._current_uow` be unsafe in the shared service?

Concurrent requests use the same service instance. If each request assigns its unit of work to
`self._current_uow`, one request can overwrite another request's reference. Subsequent code could
then use the wrong session or transaction. This is a race condition. Keep the unit of work local
to each `execute()` call instead.

Dishka's `Scope.APP` makes `CreateBookService` effectively a singleton per application container:
it creates the service on first resolution and reuses it within that container. Each worker
process has its own application container and service instance.

## 11. Does Dishka select a constructor dependency using the parameter name or its type annotation?

Dishka uses the type annotation to resolve the dependency. For `uow_factory: UnitOfWorkFactory`,
it resolves the registered factory matching `UnitOfWorkFactory`. Renaming the parameter does not
change which dependency Dishka selects.

## 12. Why does `provide(CreateBookService)` need an assigned class attribute, and how does Dishka discover it?

Dishka requires registrations for the dependencies it resolves. Autowiring supplies constructor
arguments from those registrations; it does not automatically discover every class that could
consume them. Objects created directly by application code, such as entities and units of work
created by our factory, do not need their own Dishka registrations.

The standalone `provide(CreateBookService)` call returns registration metadata rather than a
service instance. Assigning it to a provider class attribute retains that metadata where Dishka
can discover it. Dishka inspects provider attributes for these registration declarations. The
attribute name is arbitrary: the metadata identifies `CreateBookService` as the type to construct.
The provider's `Scope.APP` determines its lifetime unless the registration specifies another scope.
A bare standalone call inside the class body would discard the returned metadata.

This is framework magic in the sense of implicit inspection: the visible assignment does not
show the discovery and registration work that Dishka performs. It is a documented library pattern,
not custom machinery added by this project. Calling a provider instance's `provide` method is an
alternative that registers directly on that instance:

```python
books_provider = Provider(scope=Scope.APP)
books_provider.provide(CreateBookService)
```

Calling `CreateBookService(...)` directly instead constructs an instance immediately, with the
caller supplying its dependencies and managing its lifetime.

## 13. Why does the engine provider call `engine.dispose()` in `finally` after yielding, rather than before yielding?

The provider defers cleanup until its application scope closes. FastAPI's lifespan cleanup closes
our Dishka container, which finalizes the provider's generator and executes its `finally` block.
The `finally` block ensures disposal runs when control leaves the suspended generator.

Disposing an engine does not permanently disable it. With the default disposal behavior, SQLAlchemy
replaces its connection pool and closes the old pool's checked-in connections. Connections already
checked out are not forcibly closed. Subsequent use of the engine can establish new connections.

Therefore, disposing before yielding would still allow this application to serve requests. A newly
created engine normally has no pooled connections yet, so disposal at that point accomplishes
little. Without disposal after yielding, the provider would perform no explicit pool cleanup when
the container closes. Process termination eventually releases connections, but closing a container
does not necessarily terminate its process. The reason for the placement is cleanup timing, not
that a disposed engine becomes unusable.

## 14. Does `type UnitOfWorkFactory = Callable[[], UnitOfWork]` create a factory, and where does the callable come from?

The declaration defines a named type alias. It describes a callable that takes no arguments and
returns a `UnitOfWork`; it does not create that callable or a unit-of-work instance. The name
makes the contract easier to read and import without repeating the underlying annotation.

Saying the alias does nothing is too broad. Type checkers use it, and Dishka interprets the
annotation during dependency registration and resolution. It describes the dependency rather
than implementing its behavior.

Our persistence provider supplies the callable implementation:

```python
partial(SqlAlchemyUnitOfWork, session_factory)
```

This binds the session factory argument in advance. Each subsequent call constructs a new
`SqlAlchemyUnitOfWork`; entering its context creates the session.
# Bookstore API — Architecture Knowledge Checks




Python 3.14 • DDD • Hexagonal Architecture • MySQL 8.4 • SQLAlchemy 2.x • Unit of Work • Dishka

Updated: 2026-10-21. This file records questions, the learner's actual answers (summarized faithfully unless quoted), evaluation, and unresolved questions. Extend it after each exchange; do not mark unanswered questions as answered.

## Question 1 — Unit of Work and external payments

**Scenario:** The purchase use case modifies books/orders in one SQLAlchemy session, charges an external payment provider, and commits the DB. Payment provider has idempotency keys but no distributed transactions. Endpoint can be retried.

**Question:** Which practical consistency strategy is strongest? A) Treat whole service as atomic; B) charge after commit and compensate; C) atomically persist order plus payment-request outbox event, process asynchronously with idempotency/reconciliation; D) separate sessions and sequential commits.

**Learner answer:** C.

**Evaluation:** Correct. Transactional outbox commits DB state and work request atomically. Asynchronous execution with durable attempts, provider idempotency, retry and reconciliation avoids assuming distributed atomicity. Explicitly note failures after provider success and before local acknowledgement; idempotency-key retention is finite.

**Follow-up (open):** Payment succeeds; worker crashes before recording PAID; retries 48h later after provider's 24h idempotency-key retention. How can the integration avoid duplicate charges and reconcile? No learner response recorded.

## Question 2 — Inventory concurrency

**Scenario:** MySQL InnoDB REPEATABLE READ. Two independent transactions load available=5, then reserve 4 and 3 respectively, using normal ORM updates without versions or explicit locks.

**Question:** Choose and defend one of: A) SERIALIZABLE; B) SELECT ... FOR UPDATE; C) optimistic version check and fresh retry; D) atomic conditional decrement checked by affected-row count. Discuss contention and boundaries.

**Learner answer:** C. Atomic SQL is ideal for the simple case, but specialized state updates can complicate evolving aggregate behavior. Optimistic locking is a practical trade-off: reload/re-execute on conflicts; bound retry attempts and allow application policy to determine when to retry or compensate. Pessimistic locking could work but learner was concerned about scaling and described it as 'locking tables.' Concurrency policy should be controlled in application layer rather than overly coupled to infrastructure.

**Evaluation:** C is defensible. Corrected mistaken characterization of pessimistic locking: indexed SELECT FOR UPDATE typically locks index records/rows, not an exclusive table lock. Atomic conditional updates remain suitable when business invariants permit them. Separate domain invariant enforcement, application retry/transaction policy, and infrastructure version checks. New UoW/rollback is required after failed flush. Initial grade 8.5/10.

## Question 2B — Optimistic locking vs idempotency

**Scenario:** Same UoW adds Order and updates versioned Book; Order itself has no version. One transaction commits, another receives StaleDataError during book flush after possibly inserting an order in the session.

**Question:** Does Book versioning alone prevent duplicate orders? Address flush ordering, rollback, retry and unique business intent/idempotency.

**Learner answer:** 'Mostly' sufficient for inventory integrity, not request intent: duplicate requests for one customer intent might each reserve valid stock and create multiple orders. Need stable idempotency identity for customer intent, but constructing a deterministic key from request characteristics is ambiguous: two genuine orders could have identical attributes. Proposed considering business-defined time window but recognized that is risky. Business and engineering need to agree on intent semantics. Later emphasized that a persisted idempotency record naturally follows given stateless HTTP APIs. Explained that rollback/flush behavior was obvious and intentionally omitted.

**Evaluation:** Fundamental architectural issue identified correctly. Do not deduct for omission of known rollback behavior. Avoid time-window heuristics and content-only deterministic idempotency keys. Prefer explicit, client-created operation/intent ID reused across retries, a request fingerprint to reject payload mismatch, durable status/result records, and DB uniqueness. Flush does not commit; failed transaction rollback removes inserted Order. Original grade 8/10, revised 9/10, and **final revised grade: 10/10 for Question 2B conceptual reasoning**. Learner clarified that the semantics of an intent must be defined jointly by business and engineering; the key MAY incorporate business, temporal, and technical attributes but need not be derived exclusively from any of them. The earlier deduction incorrectly attributed a content-derived deterministic-key requirement to the learner. A stable explicit operation ID remains one implementation option, not a correction to their principle. Implementation-level concerns (key ownership, uniqueness scope, retry horizon, payload fingerprint, atomic persistence) remain to be designed and tested; this does not undermine the conceptual answer. Initial Question 2 inventory-concurrency grade of 8.5/10 remains separate.

## Question 3 — Concurrent idempotency-key creation (NOT YET STARTED)

**Scenario:** idempotency_keys table has primary key idempotency_key, request_hash, nullable order_id, status. Two concurrent requests read no record; A inserts record and order and commits; B insert gets duplicate-key error.

**Question:** Design recovery for B; consider whether to retry entire use case, retrieve existing result, or report conflict; handle an in-progress request and response loss; prove correctness with MySQL REPEATABLE READ and avoid second create_order().

**Status:** Question was presented but the learner explicitly asked not to advance without permission. Do NOT evaluate or present Question 3 until learner approves.

## Standing assessment rules

- Senior/Staff-level realistic failure-mode questions; one at a time.
- Never reveal the answer before the learner responds.
- Evaluate the reasoning and technical precision; avoid grading down for omission of obvious details the learner understood.
- **Always ask for explicit readiness before advancing to the next question or component.**
- Record each question, learner answer, evaluation and revision in this file.
