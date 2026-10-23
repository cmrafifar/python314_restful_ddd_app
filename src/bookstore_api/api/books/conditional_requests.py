"""Translate HTTP entity-tags into application version preconditions."""

import re
from uuid import UUID

from fastapi import HTTPException, status

_ENTITY_TAG = r'(?:W/)?"[\x21\x23-\x7e\x80-\xff]*"'
_IF_MATCH = re.compile(rf"[ \t]*(?:\*|{_ENTITY_TAG}(?:[ \t]*,[ \t]*{_ENTITY_TAG})*)[ \t]*")
_TAGS = re.compile(r'(W/)?"([\x21\x23-\x7e\x80-\xff]*)"')

IF_MATCH_DESCRIPTION = (
    "Required for updates and deletion. Copy the quoted ETag from GET, for example "
    '"book-5d23d9a6-4198-4fca-ae01-f962d7b71401-v1". '
    "A comma-separated list succeeds if any strong tag matches. Weak tags never match. "
    "* requires only that the book exist and does not protect against a stale client. "
    "Missing: 428; malformed: 400; stale or nonmatching: 412."
)


def book_etag(book_id: UUID, version: int) -> str:
    return f'"book-{book_id}-v{version}"'


def parse_if_match(book_id: UUID, values: list[str] | None) -> frozenset[int] | None:
    if values is None:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail={
                "code": "precondition_required",
                "message": "Supply If-Match from the book's ETag",
            },
            headers={"Cache-Control": "no-store"},
        )
    value = ",".join(values)
    if not _IF_MATCH.fullmatch(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_if_match", "message": "Invalid If-Match header"},
        )
    if value.strip() == "*":
        return None

    versions: set[int] = set()
    for weak, opaque_tag in _TAGS.findall(value):
        match = re.fullmatch(rf"book-{book_id}-v([1-9][0-9]{{0,18}})", opaque_tag)
        if not weak and match:
            versions.add(int(match[1]))
    return frozenset(versions)
