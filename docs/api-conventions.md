# API Conventions

Read when adding or changing HTTP behavior. This document defines shared HTTP patterns,
adapter boundaries, and known exceptions. Update it when a shared convention changes,
not for each new endpoint.

## Contract ownership

Maintain endpoint paths, fields, validation constraints, response schemas, statuses, and
header descriptions in route metadata and HTTP schemas. FastAPI publishes these through
`/docs`, `/redoc`, and `/openapi.json`. Route tests verify the implemented contract.

Keep business rules and resource lifecycle decisions in [domain documentation](domain/books.md).
Keep implementation progress in [the task list](task-list.json). Do not duplicate endpoint
catalogs or request/response examples here.

## Resources and methods

- Use plural resource names and identity-based member paths.
- Use GET for retrieval, POST for creation, PUT for replacing writable details, PATCH for
  partial changes, and DELETE for removal.
- PUT and PATCH update existing resources; they do not create missing records.
- PATCH uses an `application/json` field-update object. Omitted fields remain unchanged;
  this is not JSON Patch or JSON Merge Patch.
- Define writable fields and treatment of unknown, omitted, and null values in request schemas.
- Keep representations separate from domain entities and persistence models.

## Status and error patterns

| Condition | Convention |
|---|---|
| Successful retrieval or update with a representation | 200 |
| Successful creation | 201 |
| Successful removal without a representation | 204 with an empty body |
| Missing requested resource | 404 |
| Uniqueness conflict | 409 |
| Invalid request shape, field value, or path parameter | FastAPI's standard 422 response |
| Unexpected failure | 500; never translate an unknown defect into a client error |

Known application errors use `{"detail": {"code": "...", "message": "..."}}`, with a
stable code and readable message. Exceptions remain: duplicate creation uses a string
`detail`, and request validation uses FastAPI's standard error list. A single API-wide error
envelope has not been agreed.

Domain validation failures are not consistently translated yet; an invalid ISBN checksum
can still return 500. Resolve that gap through explicit error mapping rather than catching
every `ValueError`. Creation currently emits no `Location` header; no shared policy requires it.

## Conditional writes

Use strong ETags and required `If-Match` for version-protected updates and deletion.
Keep version counters out of JSON representations. Clients copy the complete quoted
validator from a read response.

Accept comma-separated tag lists and repeated header lines. Any matching strong tag
suffices; weak tags never match. `If-Match: *` requires existence but does not protect
against changes since the client's read. Persistence must still reject races after the
application's lookup.

| Condition | Response |
|---|---|
| Missing `If-Match` | 428, `precondition_required`, with `Cache-Control: no-store` |
| Malformed `If-Match` | 400, `invalid_if_match` |
| Nonmatching validator or concurrent write conflict | 412, `precondition_failed` |

Request validation can return 422 before header parsing. Missing resources at application
lookup return 404. After a 412, clients must retrieve and reconcile the current representation.

Do not emit an ETag on a PUT response when input was transformed before persistence.
Clients retrieve the resulting representation for its validator. An empty DELETE response
also carries no ETag. Document applicable response headers in each operation's OpenAPI metadata.

## Adapter boundaries and verification

- Keep request/response schemas and FastAPI dependencies at the HTTP boundary.
- Translate requests into application commands and results into explicit representations.
- Do not return ORM models or expose sessions to callers.
- Let the domain enforce its invariants; transport validation additionally protects request shape.
- Translate known failures deliberately. Never expose database exception text, SQL,
  credentials, or tracebacks as a designed error payload.
- Test statuses, response shapes, headers, and error translation through public routes.
  Use persistence integration tests for database guarantees that fakes cannot prove.

Agree on pagination, authentication, rate limiting, and versioning policies when concrete
requirements need them. Their conventions are not defined here yet.
