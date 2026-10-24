# 0003: Bidirectional keyset pagination

Status: Accepted
Date: 2026-10-23

## Context

BOOK-017 provides a bounded collection ordered by ISBN. BOOK-018 adds navigation
through that collection. The learning goal is a design that supports large collections,
including both next and previous navigation.

This decision records the implemented design. Route metadata and schemas own the public
endpoint specification; BOOK-018 records verification evidence.

## Decision

Use keyset pagination with the existing unique, immutable ISBN as the ordering key.
Always return items in ISBN ascending order, including when navigating backward.

Use a single opaque cursor query parameter. Encode the following JSON structure with
URL-safe Base64:

```json
{
  "v": 1,
  "isbn": "9780134494166",
  "direction": "next"
}
```

The encoded token omits Base64 padding. Input length is capped at 512 characters.

- `v` identifies the cursor format, independently of API and book versions.
- `isbn` stores the boundary value rather than a reference that must be looked up.
- `direction` is either `next` or `previous`.

The next cursor uses the last returned ISBN. The previous cursor uses the first
returned ISBN. Return nullable `next_cursor` and `previous_cursor` fields; unavailable
navigation uses `null`.

Keep the existing limit and text filters as query parameters. Clients preserve filters
between requests and may change the limit. The cursor does not contain a page number,
page size, filters, or configurable sort metadata. ISBN ascending remains the only
supported ordering. Changing filters starts a new traversal without a cursor.

Base64 is encoding, not encryption or a signature. Treat decoded content as untrusted
input. Reject malformed encoding, malformed JSON, unsupported versions, invalid ISBN
boundaries, and unsupported directions with the standard HTTP 422 validation response.
Keep decoding bounded and validate the exact structure before querying persistence.

## Query behavior

For next navigation, apply the current filters and seek above the boundary:

```sql
WHERE isbn > :cursor_isbn
ORDER BY isbn ASC
LIMIT :limit_plus_one
```

For previous navigation, apply the same filters and seek below the boundary:

```sql
WHERE isbn < :cursor_isbn
ORDER BY isbn DESC
LIMIT :limit_plus_one
```

Remove the lookahead row before reversing backward results into display order. The
lookahead establishes availability in the requested direction. Use a bounded existence
query with the same filters when necessary to establish availability on the other side;
do not infer availability solely from the presence of an incoming cursor.

Preserve the existing `has_more` field as an indication that a next page exists in
display order, consistent with `next_cursor`. Document this meaning for backward requests.
Empty pages return null cursors and `has_more=false`. If collection changes leave a
continuation empty, clients can restart without a cursor.

## Alternatives

- Offset pagination was rejected because scalable keyset traversal is an explicit goal.
- Forward-only cursors were rejected because previous-page navigation is required.
- Embedding filters, page size, and selectable sorting was rejected to keep this slice
  focused on the existing collection contract.

## Consequences

ISBN uniqueness removes ordering ties, so no additional identity tie-breaker is needed.
The stored boundary remains usable if its original book is deleted. Existing ISBN
uniqueness supplies an index for seeking; no schema migration is expected.

Navigation does not provide a snapshot across requests. New books above a forward
boundary can appear later; books inserted below it require restarting or navigating
backward. Deletions remove results. Title and author changes can affect filter membership,
but cannot move a book's ISBN position. Revisiting a page therefore need not reproduce
its original contents.

Keyset pagination avoids offset scan cost. Existing substring filters can still require
scanning candidates; bounded results and existence queries do not guarantee constant
query cost. Direct numbered page jumps and total page counts are outside this scope.

## Implementation

1. `application/books/pagination.py` defines the typed boundary and direction;
   `application/books/list_books.py` coordinates navigation without transport encoding.
2. `application/books/ports.py` declares bounded seek and existence capabilities.
   Reads never commit.
3. `infrastructure/persistence/repositories/sqlalchemy_book_repository.py` and
   `tests/fakes/book_repository.py` implement the same navigation semantics.
4. `api/books/pagination.py` encodes and strictly decodes cursors.
   `api/books/schemas.py` and `api/books/router.py` own validation, response fields,
   and generated OpenAPI documentation.
5. Existing application, HTTP, and MySQL listing test files verify behavior at their
   responsible boundaries.

Paths above are relative to `src/bookstore_api/`, except paths beginning with `tests/`.

## Verification

- Application tests: first, middle, last, empty, and single-page results; forward/backward
  round trips; limit changes; lookahead trimming; cursor availability; no commits.
- HTTP tests: opaque cursor requests and responses, invalid cursor validation, retained
  limit/filter validation, stable response ordering, and essential OpenAPI metadata.
- Live MySQL tests: seek predicates in both directions, bounded ordering, filtered
  navigation, deleted anchor rows, and inserts/deletions/filter-changing updates between
  requests using independent connections where needed.
- Run pytest, Ruff, formatting, BasedPyright, whitespace checks, and the integration-test
  orchestration script. Record actual results and verification limits in BOOK-018.

These checks passed on 2026-10-23. Counts and verification limits are recorded under
BOOK-018 in the task list. BOOK-019 remains outside this slice.

## References

- [Task list](../task-list.json)
- [Collection-read architecture](../architecture.md#collection-reads)
- [Testing boundaries and MySQL workflow](../testing.md)
