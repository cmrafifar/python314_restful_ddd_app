
from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from bookstore_api.infrastructure.persistence.base import Base


class BookModel(Base):
    __tablename__ = "books"

    __table_args__ = (
        UniqueConstraint("isbn", name="uq_books_isbn"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    isbn: Mapped[str] = mapped_column(
        String(13),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    author: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

