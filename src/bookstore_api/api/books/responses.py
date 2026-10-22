"""Book response descriptions shared by the read and update operations."""

from fastapi import status

from bookstore_api.api.books.schemas import BookNotFoundResponse
from bookstore_api.api.responses import ETAG_HEADERS

BOOK_NOT_FOUND_RESPONSES: dict[int | str, dict[str, object]] = {
    status.HTTP_404_NOT_FOUND: {
        "model": BookNotFoundResponse,
        "description": "No book exists with the requested ID. PUT does not create missing books.",
    },
}

BOOK_READ_RESPONSES: dict[int | str, dict[str, object]] = {
    **BOOK_NOT_FOUND_RESPONSES,
    status.HTTP_200_OK: {
        "description": "Book representation with a strong ETag for subsequent conditional updates.",
        "headers": ETAG_HEADERS,
    },
}
