from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateBookCommand:
    isbn: str
    title: str
    author: str
