from uuid import UUID, uuid4

from bookstore_api.domain.books.isbn import ISBN


class Book:
    id: UUID
    isbn: ISBN
    _title: str
    _author: str

    def __init__(
        self,
        id: UUID,
        isbn: ISBN,
        title: str,
        author: str,
    ) -> None:
        self.id = id
        self.isbn = isbn
        self._title = self._validate_text(title, "Title")
        self._author = self._validate_text(author, "Author")

    @classmethod
    def create(
        cls,
        isbn: ISBN,
        title: str,
        author: str,
    ) -> Book:
        return cls(
            id=uuid4(),
            isbn=isbn,
            title=title,
            author=author,
        )

    @property
    def title(self) -> str:
        return self._title

    @property
    def author(self) -> str:
        return self._author

    def rename(self, title: str) -> None:
        self._title = self._validate_text(title, "Title")

    @staticmethod
    def _validate_text(value: str, field: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError(f"{field} cannot be empty")

        if len(normalized) > 255:
            raise ValueError(f"{field} cannot exceed 255 characters")

        return normalized
