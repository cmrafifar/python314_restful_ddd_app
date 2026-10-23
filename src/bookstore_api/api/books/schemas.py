from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)
from pydantic.json_schema import SkipJsonSchema

from bookstore_api.application.books.list_books import MAX_LIST_LIMIT
from bookstore_api.domain.books.book import MAX_AUTHOR_LENGTH, MAX_TITLE_LENGTH

type BookTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_TITLE_LENGTH),
]
type BookAuthor = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_AUTHOR_LENGTH),
]


class CreateBookRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    isbn: str
    title: BookTitle
    author: BookAuthor


class ReplaceBookRequest(BaseModel):
    """Replace the writable representation; both fields are required."""

    model_config = ConfigDict(extra="forbid")

    title: BookTitle
    author: BookAuthor


class PatchBookRequest(BaseModel):
    """Omission preserves a field; explicit null and an empty patch are invalid."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"minProperties": 1})

    # None represents omission internally, but is not an accepted JSON value.
    title: BookTitle | SkipJsonSchema[None] = Field(
        default=None, description="New title; omit to preserve."
    )
    author: BookAuthor | SkipJsonSchema[None] = Field(
        default=None, description="New author; omit to preserve."
    )

    @field_validator("title", "author")
    @classmethod
    def reject_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Explicit null is not allowed; omit the field to preserve it")
        return value

    @model_validator(mode="after")
    def require_changes(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Supply at least one of title or author")
        return self


class BookListParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: BookTitle | None = Field(
        default=None, description="Case-sensitive literal substring of the title."
    )
    author: BookAuthor | None = Field(
        default=None, description="Case-sensitive literal substring of the author."
    )
    limit: int = Field(default=20, ge=1, le=MAX_LIST_LIMIT)


class BookResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID


class BookDetailsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    isbn: str
    title: BookTitle
    author: BookAuthor


class BookListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[BookDetailsResponse]
    has_more: bool = Field(
        description="Whether more matching books exist beyond the returned limit."
    )


class BookNotFoundDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Literal["book_not_found"]
    message: str


class BookNotFoundResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: BookNotFoundDetail
