from dataclasses import dataclass
from typing import Literal

from bookstore_api.domain.books.isbn import ISBN


@dataclass(frozen=True, slots=True)
class BookPageCursor:
    isbn: ISBN
    direction: Literal["next", "previous"]

    def __post_init__(self) -> None:
        if self.direction not in ("next", "previous"):
            raise ValueError("Cursor direction must be next or previous")
