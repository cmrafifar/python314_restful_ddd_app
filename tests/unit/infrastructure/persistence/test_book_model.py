from sqlalchemy import Table, UniqueConstraint

from bookstore_api.infrastructure.persistence.models.book import BookModel


def test_book_model_maps_to_books_table() -> None:
    table = BookModel.__table__
    assert isinstance(table, Table)

    assert table.name == "books"
    assert set(table.columns.keys()) == {
        "id",
        "isbn",
        "title",
        "author",
        "version",
    }


def test_book_model_defines_primary_key() -> None:
    table = BookModel.__table__
    assert isinstance(table, Table)

    assert {column.name for column in table.primary_key.columns} == {"id"}


def test_book_model_enforces_unique_isbn() -> None:
    table = BookModel.__table__
    assert isinstance(table, Table)

    constraints = [
        constraint for constraint in table.constraints if isinstance(constraint, UniqueConstraint)
    ]

    assert any(
        constraint.name == "uq_books_isbn"
        and {column.name for column in constraint.columns} == {"isbn"}
        for constraint in constraints
    )
