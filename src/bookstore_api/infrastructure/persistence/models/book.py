from sqlalchemy import Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from bookstore_api.infrastructure.persistence.base import Base


class BookModel(Base):
    __tablename__ = "books"

    __table_args__ = (UniqueConstraint("isbn", name="uq_books_isbn"),)

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

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    # The repository increments on every accepted write, including unchanged details.
    # SQLAlchemy includes the previous version in UPDATE's WHERE clause.
    __mapper_args__ = {  # noqa: RUF012 - SQLAlchemy declares this mapping as an instance attribute.
        "version_id_col": version,
        "version_id_generator": False,
    }
