from uuid import UUID

from bookstore_api.domain.books.book import Book
from bookstore_api.domain.books.isbn import ISBN
from bookstore_api.infrastructure.persistence.mappers.book_mapper import BookMapper


def test_maps_domain_book_to_persistence_model() -> None:
    book = Book.create(
        isbn=ISBN("9780132350884"),
        title="Clean Code",
        author="Robert C. Martin",
    )

    model = BookMapper.to_model(book)

    assert model.id == str(book.id)
    assert model.isbn == book.isbn.value
    assert model.title == book.title
    assert model.author == book.author


def test_reconstructs_domain_book_from_persistence_model() -> None:
    book = Book.create(
        isbn=ISBN("9780132350884"),
        title="Clean Code",
        author="Robert C. Martin",
    )

    model = BookMapper.to_model(book)
    reconstructed = BookMapper.to_domain(model)

    assert isinstance(reconstructed.id, UUID)
    assert reconstructed.id == book.id
    assert reconstructed.isbn == book.isbn
    assert reconstructed.title == book.title
    assert reconstructed.author == book.author

    assert reconstructed is not book
