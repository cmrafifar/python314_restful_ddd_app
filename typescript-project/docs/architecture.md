# Architecture and contract decisions

See [API conventions](api-conventions.md) for the HTTP contract and
[technology decisions](decisions.md) for the rationale behind the selected tools and patterns.

## Ownership and dependencies

This is a small modular monolith. `src/books/domain` owns Book, ISBN, and business rules.
`src/books/application` owns catalog orchestration and transaction/repository interfaces.
Neither layer imports Nest, Prisma, HTTP DTOs, or infrastructure. ESLint enforces the principal
framework restrictions. Nest modules compose plain services through a documented factory provider.
The HTTP controller receives BookCatalog through Nest's built-in DI container.

`src/books/adapters/http` owns request/response DTOs, conditional headers, cursors, and route
metadata. The persistence adapter maps Prisma records explicitly to domain objects. A single
cohesive BookCatalog class exposes catalog use cases; no generic service/repository framework,
custom DI container, CQRS bus, or speculative extension points are introduced.

## Domain rules

A Book identifies one edition in one format. A UUID is independent of immutable ISBN-13.
ISBN accepts exactly 13 ASCII digits with a valid checksum; there is no formatting normalization,
prefix requirement, or external assignment lookup. Equality compares the ISBN value. The ISBN
instance is frozen; TypeScript readonly fields alone are compile-time restrictions.

Titles and authors trim outer whitespace and preserve internal whitespace. Length uses Unicode
code points, with limits of 1–100 and 1–80. JavaScript `trim()` defines whitespace; unlike Python
`strip()`, it does not remove U+001C–U+001F or U+0085, and it does remove U+FEFF. This is an explicit
language-level difference. Both proposed detail values validate before either mutation occurs.
ID and ISBN cannot be updated through HTTP. PATCH omission preserves a field; null, unknown
properties, and an empty patch are rejected. Domain invariants protect non-HTTP callers too.

The database unique index protects concurrent ISBN creation. Accepted updates increment the
version even when details do not change. Hard deletion frees the ISBN; recreating it generates a
new UUID. No inventory, orders, payments, authentication, or background processing is implemented.

## Transactions and concurrency

The application owns a small callback transaction port. Its Prisma adapter supplies a repository
bound to the interactive transaction client. Successful callback completion commits; thrown
errors roll back. This deliberately replaces Python's explicit commit context with Prisma's
idiomatic callback lifecycle. Repositories never commit and never access a global client.

Conditional update/delete statements use both UUID and the loaded version and inspect affected
counts. This protects the race after lookup, including wildcard If-Match requests. A zero count
becomes a version conflict. Only recognized ISBN unique failures become duplicate errors; other
database failures propagate as server errors. Transactions use PostgreSQL's default Read Committed
isolation. No automatic retries hide conflicts from callers.

Persistence uses Prisma's typed model operations for writes and bound SQL fragments for literal
substring collection reads. PostgreSQL `strpos` with C collation avoids LIKE wildcard semantics;
percent, underscore, and backslash remain literal. Filters combine with AND. Unique ASCII ISBN
ordering supplies the seek boundary. Substring filtering may scan; bounded results do not imply
bounded scan cost.

Forward reads seek above ISBN ascending; backward reads seek below ISBN descending, then reverse
the retained rows. One extra row determines availability in that direction. An EXISTS query checks
the opposite direction. Opaque cursors contain only payload version 1, ISBN, and direction, using
unpadded Base64url. They do not depend on anchor-row existence, bind filters, or promise a snapshot.
Concurrent collection changes can affect navigation. Empty continuations have null cursors.

## HTTP and validation

The Python source and its running `/openapi.json` are the contract references. Preserve methods,
resource paths, successful response fields, query defaults, version preconditions, and status
semantics. Nest uses 400 for invalid requests instead of FastAPI's 422. Invalid ISBN checksums
also deliberately return 400, correcting the source's known unmapped-error gap.

Known catalog errors use `detail: {code, message}` consistently, including duplicate creation.
Nest validation errors retain the framework's standard error envelope. Unexpected failures remain
500 without database details. This is a standalone API adaptation, not wire-compatible replacement.

Missing If-Match returns 428 and Cache-Control no-store. Malformed syntax returns 400. Strong tag
lists match any supplied current tag; weak tags never match. Wildcard requires existence. Stale
tags and concurrent writes return 412; a missing resource at lookup returns 404. Missing headers
and rejected preconditions never permit writes. Versions are absent from JSON. PUT emits no
validator because text may be transformed; PATCH and GET emit a fresh strong ETag.

ValidationPipe rejects unknown request fields and validates DTO instances. Successful JSON responses
are explicitly mapped and recursively validated with the same libraries before returning. Response
validation failures remain server errors. There is no general-purpose custom validation framework.
The Swagger compiler plugin generates metadata alongside explicit DTO and operation annotations;
documentation does not substitute for runtime validation.

## Verification boundary

Automated tests are deferred by request. Compiler, lint, formatting, build, migration, container,
and manual HTTP checks should report only results actually observed. Initial manual smoke checks
cannot establish comprehensive concurrency, rollback, or regression guarantees. Add meaningful
domain/application tests, HTTP contract checks, and real PostgreSQL persistence proofs when asked.
Fakes do not prove database behavior. Do not copy Python's completed task statuses into this project.
