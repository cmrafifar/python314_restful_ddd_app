from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CreateBookRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    isbn: str
    title: str
    author: str


class BookResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID


class BookDetailsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    isbn: str
    title: str
    author: str


class BookNotFoundDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Literal["book_not_found"]
    message: str


class BookNotFoundResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: BookNotFoundDetail
