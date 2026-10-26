# 0004: Callback transactions

Status: Accepted
Date: 2026-10-25

## Context

The explicit unit-of-work protocol required a factory, context-manager methods, manual session
state, and commit calls in write services. Current use cases each need one transaction and do
not need partial commits. The TypeScript comparison exposed that this complexity was a design
choice rather than a Python requirement.

## Decision

Replace the unit-of-work factory with the application-owned `BookTransactions.run(work)` port.
The callback receives a transaction-bound `BookRepository` and returns a typed result. Successful
completion commits; callback or commit failure rolls back. The result reaches the caller only
after commit succeeds.

Use SQLAlchemy's documented `sessionmaker.begin()` context in `SqlAlchemyBookTransactions`
to create, complete, and close each session. Keep the runner application-scoped and stateless
between calls. Each call owns a fresh session, independent of HTTP request scope.

Retain MySQL ISBN uniqueness translation around the whole transaction, including commit.
Keep repository mapping, optimistic version checks, HTTP behavior, and separate use-case
services unchanged. Do not retain the old unit-of-work API as a second transaction mechanism.

## Alternatives

- Retain explicit commit: valid when early or multiple commits are needed, but adds lifecycle
  code without a current requirement.
- Commit automatically in a custom unit-of-work context: reduces commit calls but retains the
  context-manager protocol and factory that the callback port replaces.
- Use a request-scoped transaction: ties application operations to HTTP and hides their atomic
  boundaries; multiple operations in one request need not share a transaction.

## Consequences

Services choose atomic work without managing session mechanics. Domain and application remain
framework-free. Callbacks add a nested function in each service but remove the custom session
state machine, explicit commit calls, and callable-factory registration.

Reads use the same commit-on-success lifecycle; they no longer finish by rolling back an
otherwise successful read transaction. Read services still issue no writes. Exceptions must
escape the callback to trigger rollback. There are no automatic retries, ambient transactions,
or guarantees across separate `run` calls. Repositories must not escape their callback.

## Verification

Verify application outcomes, HTTP contracts, DI isolation, commit visibility, rollback after
flushed writes, duplicate translation, and stale-write protection. Fakes cannot establish
database guarantees; report live MySQL checks separately from the default pytest suite.

## References

- [Transaction port](../../src/bookstore_api/application/books/transactions.py)
- [SQLAlchemy adapter](../../src/bookstore_api/infrastructure/persistence/sqlalchemy_book_transactions.py)
- [SQLAlchemy session framing](https://docs.sqlalchemy.org/en/20/orm/session_basics.html#framing-out-a-begin-commit-rollback-block)
