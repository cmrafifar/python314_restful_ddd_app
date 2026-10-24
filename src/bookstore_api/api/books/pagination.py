import base64
import binascii
import json
import re

from bookstore_api.application.books.pagination import BookPageCursor
from bookstore_api.domain.books.isbn import ISBN

MAX_CURSOR_LENGTH = 512


def encode_cursor(cursor: BookPageCursor | None) -> str | None:
    if cursor is None:
        return None
    payload = {"v": 1, "isbn": cursor.isbn.value, "direction": cursor.direction}
    encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(encoded).rstrip(b"=").decode("ascii")


def decode_cursor(value: str) -> BookPageCursor:
    """Decode a bounded, unpadded URL-safe cursor without trusting its contents."""
    if len(value) > MAX_CURSOR_LENGTH or re.fullmatch(r"[A-Za-z0-9_-]+", value) is None:
        raise ValueError("Invalid pagination cursor")
    try:
        decoded = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
        payload: object = json.loads(decoded.decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid pagination cursor") from exc

    if not isinstance(payload, dict) or set(payload) != {"v", "isbn", "direction"}:
        raise ValueError("Invalid pagination cursor structure")
    if type(payload["v"]) is not int or payload["v"] != 1:
        raise ValueError("Unsupported pagination cursor version")
    if not isinstance(payload["isbn"], str):
        # Pydantic translates ValueError into 422; TypeError would escape validation.
        raise ValueError("Invalid pagination cursor ISBN")  # noqa: TRY004
    isbn = ISBN(payload["isbn"])
    if payload["direction"] == "next":
        return BookPageCursor(isbn, "next")
    if payload["direction"] == "previous":
        return BookPageCursor(isbn, "previous")
    raise ValueError("Invalid pagination cursor direction")
