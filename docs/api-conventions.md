# API Conventions

Read when adding or changing HTTP behavior. Current behavior and proposed conventions below have different status.

## Current HTTP surface

[`create_app`](../src/bookstore_api/main.py) registers `GET /health`, which returns HTTP 200 and `{"status": "ok"}`. It is a process health response and does not check database readiness.

FastAPI exposes generated documentation at `/docs` and `/redoc`, and its schema at `/openapi.json`. Treat the running application's generated schema as the source for implemented HTTP operations.

There are no book endpoints, custom application error handlers, pagination contracts, authentication rules, or API versioning conventions yet. The internal create-book command/result is not an established wire format.

## Required adapter boundaries

- Keep request/response schemas and FastAPI dependencies at the HTTP boundary.
- Translate request data into application commands and results into explicit response representations.
- Do not return ORM models or expose sessions to callers.
- Let the domain enforce its invariants. Request validation may additionally reject malformed transport input.
- Map known application/domain failures deliberately. Do not catch every `ValueError` or unexpected exception and label it a client mistake.
- Never expose database exception text, SQL, credentials, or tracebacks as a designed error payload.
- Verify HTTP behavior with route-level tests and update generated schema descriptions alongside endpoints.

## Proposed defaults for the first book endpoints

These are design starting points, not implemented contracts. Confirm them in the endpoint change and replace this section with the chosen contract.

| Concern | Proposed convention |
|---|---|
| Resource naming | Plural nouns, such as `/books` and `/books/{book_id}` |
| Create | `POST /books`, HTTP 201, explicit response containing the created identity, and `Location` for a retrievable resource |
| Read | `GET`, HTTP 200; HTTP 404 for a missing requested book |
| Duplicate ISBN | HTTP 409 after deliberate application error translation |
| Invalid input | HTTP 422 for request/domain validation failures attributable to caller input |
| Unexpected failure | HTTP 500 with a generic client message |

Before exposing book errors, choose one documented error representation with a stable code and readable message. Specify its relationship to FastAPI's request-validation response, and test both. No project-wide error envelope is selected yet.

Choose pagination, update semantics, and versioning when a concrete endpoint needs them. Do not add empty abstractions for future operations. See [architecture](architecture.md) and [books terminology](domain/books.md).
