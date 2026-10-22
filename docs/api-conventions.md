# API Conventions

Read when adding or changing HTTP behavior. Current behavior and proposed conventions below have different status.

## Current HTTP surface

[`create_app`](../src/bookstore_api/main.py) registers `GET /health`, which returns HTTP 200 and `{"status": "ok"}`. It is a process health response and does not check database readiness.

FastAPI exposes generated documentation at `/docs` and `/redoc`, and its schema at `/openapi.json`. Treat the running application's generated schema as the source for implemented HTTP operations.

`POST /api/v1/books` accepts a JSON object with required string fields `isbn`, `title`, and
`author`. Extra fields are rejected. Success returns HTTP 201 and `{"id": "<uuid>"}`.
Duplicate ISBNs reported as `BookAlreadyExistsError` return HTTP 409 with
`{"detail": "<message>"}`. Request shape errors use FastAPI's standard HTTP 422 validation
response. No `Location` header is emitted by the create endpoint.

`GET /api/v1/books/{book_id}` returns the book's `id`, `isbn`, `title`, and `author`
with HTTP 200 and a strong `ETag` header. A missing book returns HTTP 404 with
`{"detail": {"code": "book_not_found", "message": "Book not found"}}`.
Invalid UUID path parameters retain FastAPI's standard HTTP 422 validation response.
The structured 404 detail does not change the existing duplicate-ISBN response format.

### Updating book details

`PUT /api/v1/books/{book_id}` requires both `title` and `author`, replacing the writable
details. `PATCH` on the same path accepts either field or both and preserves omitted fields.
PATCH uses an `application/json` field-update object; it is not JSON Patch or JSON Merge Patch.
Both operations return the updated book representation with HTTP 200 and never create records.
ID, ISBN, and version are not writable JSON fields. Unknown fields, explicit null, an empty
PATCH object, and invalid text return FastAPI's standard HTTP 422 response.

POST, PUT, and PATCH trim outer whitespace before checking text: title must contain 1–100
characters and author 1–80. Internal whitespace is preserved. These rules also exist in the
domain so non-HTTP callers cannot bypass them.

Both update operations require `If-Match`. Copy the complete quoted ETag from GET, such as
`"book-5d23d9a6-4198-4fca-ae01-f962d7b71401-v1"`. The adapter supports comma-separated tag
lists and repeated header lines. Any matching strong tag suffices; weak tags never match.
`If-Match: *` requires existence but does not protect against changes since the client's read.
It still uses the database version check for races after the application's read.

| Condition | Response |
|---|---|
| Missing `If-Match` on an otherwise valid request | 428, `precondition_required`, with `Cache-Control: no-store` |
| Malformed `If-Match` | 400, `invalid_if_match` |
| No matching strong validator, or concurrent write detected during flush | 412, `precondition_failed` |
| Missing book at lookup | 404, `book_not_found` |

These errors use `{"detail": {"code": "...", "message": "..."}}`. Request validation
can return 422 before header parsing in the handler. Fetch and reconcile the latest book
after a 412; retrying the old validator cannot overwrite the accepted change.

GET and successful PATCH responses expose the current ETag. PUT returns no ETag: input can
be transformed by whitespace normalization, so fetch the book again to obtain its next
validator. See [RFC 9110, PUT](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.4)
and [If-Match](https://www.rfc-editor.org/rfc/rfc9110.html#section-13.1.1). Every accepted
update advances the counter, including unchanged details. Reusing the old ETag then returns 412.

Handler metadata and request schemas document these contracts in generated OpenAPI. The
version counter stays out of JSON responses and appears only through ETag.

Current limitation: domain `ValueError` failures, such as an invalid ISBN checksum, are not
translated into client errors yet and result in HTTP 500. There are no custom application
error handlers, pagination contracts, authentication rules, or general API versioning policy.

## Required adapter boundaries

- Keep request/response schemas and FastAPI dependencies at the HTTP boundary.
- Translate request data into application commands and results into explicit response representations.
- Do not return ORM models or expose sessions to callers.
- Let the domain enforce its invariants. Request validation may additionally reject malformed transport input.
- Map known application/domain failures deliberately. Do not catch every `ValueError` or unexpected exception and label it a client mistake.
- Never expose database exception text, SQL, credentials, or tracebacks as a designed error payload.
- Verify HTTP behavior with route-level tests and update generated schema descriptions alongside endpoints.

## Proposed defaults for future endpoint work

These remain design starting points where the current contract above does not specify behavior.
Confirm them in the relevant endpoint change.

| Concern | Proposed convention |
|---|---|
| Resource naming | Plural nouns, such as `/books` and `/books/{book_id}` |
| Create | `POST /books`, HTTP 201, explicit response containing the created identity, and `Location` for a retrievable resource |
| Read | `GET`, HTTP 200; HTTP 404 for a missing requested book |
| Duplicate ISBN | HTTP 409 after deliberate application error translation |
| Invalid input | HTTP 422 for request/domain validation failures attributable to caller input |
| Unexpected failure | HTTP 500 with a generic client message |

Before exposing book errors, choose one documented error representation with a stable code and readable message. Specify its relationship to FastAPI's request-validation response, and test both. No project-wide error envelope is selected yet.

Choose pagination and API versioning when concrete requirements need them. Do not add empty abstractions for future operations. See [architecture](architecture.md) and [books terminology](domain/books.md).
