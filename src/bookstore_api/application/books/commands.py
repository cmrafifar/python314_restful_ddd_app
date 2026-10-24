from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateBookCommand:
    isbn: str
    title: str
    author: str


@dataclass(frozen=True, slots=True)
class UpdateBookCommand:
    book_id: UUID
    # None means any existing version (HTTP If-Match: *); an empty set matches no version.
    expected_versions: frozenset[int] | None
    title: str | None = None
    author: str | None = None


@dataclass(frozen=True, slots=True)
class DeleteBookCommand:
    book_id: UUID
    # None means any existing version (HTTP If-Match: *); an empty set matches no version.
    expected_versions: frozenset[int] | None
