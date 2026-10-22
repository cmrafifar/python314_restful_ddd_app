from uuid import UUID, uuid4

from bookstore_api.domain.books.isbn import ISBN

MAX_TITLE_LENGTH = 100
MAX_AUTHOR_LENGTH = 80


class Book:
    id: UUID
    isbn: ISBN
    _title: str
    _author: str
    version: int

    def __init__(
        self,
        id: UUID,
        isbn: ISBN,
        title: str,
        author: str,
        version: int = 1,
    ) -> None:
        self.id = id
        self.isbn = isbn
        self._title = self._validate_text(title, "Title", MAX_TITLE_LENGTH)
        self._author = self._validate_text(author, "Author", MAX_AUTHOR_LENGTH)
        self.version = version

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
        self._title = self._validate_text(title, "Title", MAX_TITLE_LENGTH)

    def revise_details(self, *, title: str | None = None, author: str | None = None) -> None:
        # Validate both fields before changing either, so rejected updates leave the entity intact.
        new_title = (
            self._title if title is None else self._validate_text(title, "Title", MAX_TITLE_LENGTH)
        )
        new_author = (
            self._author
            if author is None
            else self._validate_text(author, "Author", MAX_AUTHOR_LENGTH)
        )
        self._title = new_title
        self._author = new_author

    @staticmethod
    def _validate_text(value: str, field: str, max_length: int) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError(f"{field} cannot be empty")

        if len(normalized) > max_length:
            raise ValueError(f"{field} cannot exceed {max_length} characters")

        return normalized
