import pytest

from bookstore_api.domain.books.isbn import ISBN


def test_valid_isbn() -> None:
    isbn = ISBN("9780132350884")

    assert isbn.value == "9780132350884"


def test_invalid_checksum() -> None:
    with pytest.raises(ValueError, match="checksum"):
        ISBN("9780132350885")


def test_invalid_length() -> None:
    with pytest.raises(ValueError):
        ISBN("12345")


def test_isbn_equality() -> None:
    first = ISBN("9780132350884")
    second = ISBN("9780132350884")

    assert first == second
    assert first is not second


def test_isbn_is_immutable() -> None:
    from dataclasses import FrozenInstanceError

    isbn = ISBN("9780132350884")

    with pytest.raises(FrozenInstanceError):
        isbn.value = "9780132350885"  # type: ignore[misc]
