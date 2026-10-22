class BookNotFoundError(Exception):
    pass


class BookVersionConflictError(Exception):
    """The book no longer has the version the caller expected."""
