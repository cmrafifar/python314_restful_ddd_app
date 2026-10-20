from typing import Annotated

from fastapi import Depends, Request

from bookstore_api.application.books.create_book import (
    CreateBookService,
)


def get_create_book_service(
    request: Request,
) -> CreateBookService:
    return request.app.state.create_book_service


CreateBookServiceDep = Annotated[
    CreateBookService,
    Depends(get_create_book_service),
]
