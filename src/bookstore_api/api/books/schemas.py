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
