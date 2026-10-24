# API conventions

This document explains the implemented HTTP behavior. Generated OpenAPI at `/openapi.json`
describes operation schemas; Swagger UI at `/docs` and ReDoc at `/redoc` display that specification.
Update controllers, DTO metadata, and this guide together when changing a contract.

## Resources and representations

Catalog routes use `/api/v1/books`. Resource identifiers are UUIDs; ISBN identifies an edition
and format independently of the resource ID. Requests and successful responses use JSON, except
the empty deletion response. Versions remain outside JSON and are exposed through ETags.

| Method | Path                      | Success | Representation              | ETag   |
| ------ | ------------------------- | ------- | --------------------------- | ------ |
| POST   | `/api/v1/books`           | 201     | `{id}`                      | None   |
| GET    | `/api/v1/books`           | 200     | Collection page             | None   |
| GET    | `/api/v1/books/{book_id}` | 200     | `{id, isbn, title, author}` | Strong |
| PUT    | `/api/v1/books/{book_id}` | 200     | Updated resource            | None   |
| PATCH  | `/api/v1/books/{book_id}` | 200     | Updated resource            | Strong |
| DELETE | `/api/v1/books/{book_id}` | 204     | Empty body                  | None   |

`GET /health` reports process liveness, not database readiness. Authentication and authorization
are not implemented. Documentation endpoints describe the current application, not a separate
hand-maintained specification.

## Input and output validation

Nest's global ValidationPipe transforms request DTOs and rejects unknown properties. DTO decorators
provide runtime checks; TypeScript types alone cannot validate network input. Domain constructors
and methods enforce business invariants for callers outside HTTP too.

Creation requires `isbn`, `title`, and `author`. ISBN must contain exactly 13 ASCII digits with a
valid checksum; hyphens and whitespace are not removed. Title and author trim outer whitespace
and preserve internal whitespace. Their lengths are 1–100 and 1–80 Unicode code points after
trimming. See [architecture](architecture.md#domain-rules) for JavaScript whitespace differences.

PUT requires both writable fields, `title` and `author`, and never creates a missing resource.
PATCH accepts either or both writable fields. Omitted fields remain unchanged; null, unknown
fields, and an empty object are invalid. PATCH uses a field-update object, not JSON Patch
operations. Neither operation permits changes to ID or ISBN.

Successful JSON responses are explicitly mapped and validated recursively with class-transformer
and class-validator. Invalid outgoing data produces a server error. Swagger metadata does not
enforce response validation, and Prisma records never serve directly as HTTP representations.

## Conditional writes

GET of an individual resource returns a strong ETag such as:

```http
ETag: "book-550e8400-e29b-41d4-a716-446655440000-v1"
```

Send the complete quoted value as `If-Match` when using PUT, PATCH, or DELETE. Accepted updates
increment the version even when the supplied details equal their current values. PATCH returns
the new ETag. PUT omits it because input text can be transformed; GET the resource to obtain its
current validator. Express's automatic weak ETags are disabled.

| Condition                                                  | Result                                                                |
| ---------------------------------------------------------- | --------------------------------------------------------------------- |
| Missing `If-Match`                                         | 428 with `Cache-Control: no-store`                                    |
| Malformed header                                           | 400                                                                   |
| Current strong tag, including one member of a tag list     | Write may proceed                                                     |
| Weak tag without a matching strong tag                     | 412 for an existing resource                                          |
| Stale tag or conflicting write after lookup                | 412                                                                   |
| `*`                                                        | Requires an existing resource; does not protect a stale client's view |
| Resource missing at lookup after valid precondition syntax | 404                                                                   |

Database writes also check the version loaded inside the transaction. A concurrent change between
lookup and mutation therefore fails even with `If-Match: *`. Rejected preconditions do not permit
writes. Request validation can fail before precondition handling; clients should not depend on
which error wins when several parts of a request are invalid.

DELETE permanently removes the resource and frees its ISBN for reuse. Recreating that ISBN
creates a new UUID. A subsequent deletion of the missing resource returns 404.

## Collection filtering and pagination

Supported query parameters are `title`, `author`, `limit`, and `cursor`. Unknown parameters are
rejected. Optional filters trim outer whitespace, reject blank values, and use the corresponding
field's length limit. Title and author filters combine with AND. Matching is case-sensitive,
accent-sensitive, and literal: `%`, `_`, and backslash are ordinary characters.

Results always appear in ascending ISBN order. `limit` defaults to 20 and accepts integers from
1 through 100. Offset pagination and caller-selected sorting are not implemented.

```json
{
  "items": [],
  "has_more": false,
  "next_cursor": null,
  "previous_cursor": null
}
```

Follow `next_cursor` or `previous_cursor` by passing its value as `cursor`. Preserve filters across
requests. `has_more` always means a next page exists in ascending order, including after backward
navigation. An empty continuation has no cursors.

Cursors are opaque, versioned, unpadded Base64url values, limited to 512 characters. Clients must
not construct or edit them. They contain an ISBN boundary and direction; deleting the anchor row
does not invalidate navigation. They are not signed and do not bind filters or preserve a database
snapshot. Concurrent changes can affect later pages. Invalid cursors return 400.

## Errors

Known catalog and conditional-request errors use this envelope:

```json
{
  "detail": {
    "code": "book_not_found",
    "message": "Resource not found"
  }
}
```

| Status | Code                    | Meaning                                          |
| ------ | ----------------------- | ------------------------------------------------ |
| 400    | `invalid_book`          | Business input violates a book rule              |
| 400    | `invalid_if_match`      | Conditional header syntax is invalid             |
| 404    | `book_not_found`        | Resource does not exist                          |
| 409    | `book_already_exists`   | ISBN already belongs to a resource               |
| 412    | `precondition_failed`   | Version does not match or a concurrent write won |
| 428    | `precondition_required` | Required conditional header is absent            |

Nest request validation, UUID parsing, and cursor parsing use the framework's HTTP error envelope,
typically containing `statusCode`, `message`, and `error`. The message can be a string or an array
depending on the failure. Clients must not assume every 400 uses the catalog envelope. Unexpected
failures return 500 without database details; response validation failures also remain 500.

## Differences from the Python reference

Nest returns 400 for invalid requests where FastAPI commonly returns 422. Invalid ISBN checksums
also return 400, closing the Python reference's known unmapped-error gap at translation time.
Known catalog errors consistently use the detail envelope, including duplicate ISBN errors.
These are deliberate contract differences; this project is not a wire-compatible replacement.

FastAPI supplies documentation and response-model integration directly. Here, `@nestjs/swagger`
generates OpenAPI and serves Swagger UI, a small route hosts ReDoc, and explicit response
validation enforces outgoing DTOs. Both documentation interfaces consume the same specification;
ReDoc's pinned CDN script requires browser internet access.
