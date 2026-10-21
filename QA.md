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
