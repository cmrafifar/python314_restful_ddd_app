from uuid import UUID

from dishka.integrations.fastapi import DishkaSyncRoute, FromDishka
from fastapi import APIRouter, HTTPException, status

from bookstore_api.api.books.schemas import (
    BookDetailsResponse,
    BookNotFoundResponse,
    BookResponse,
    CreateBookRequest,
)
from bookstore_api.application.books.commands import (
    CreateBookCommand,
)
from bookstore_api.application.books.create_book import (
    BookAlreadyExistsError,
    CreateBookService,
)
from bookstore_api.application.books.get_book_details import (
    BookNotFoundError,
    GetBookDetailsService,
)

router = APIRouter(prefix="/api/v1/books", tags=["books"], route_class=DishkaSyncRoute)


@router.post(
    "",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_book(
    request: CreateBookRequest,
    service: FromDishka[CreateBookService],
) -> BookResponse:
    command = CreateBookCommand(
        isbn=request.isbn,
        title=request.title,
        author=request.author,
    )

    try:
        result = service.execute(command)
    except BookAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return BookResponse(id=result.book_id)


@router.get(
    "/{book_id}",
    response_model=BookDetailsResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": BookNotFoundResponse,
            "description": "No book exists with the requested ID.",
        },
    },
)
def get_book(
    book_id: UUID,
    service: FromDishka[GetBookDetailsService],
) -> BookDetailsResponse:
    try:
        book_details_result = service.execute(book_id)
    except BookNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "book_not_found",
                "message": "Book not found",
            },
        ) from exc
    return BookDetailsResponse(
        id=book_details_result.book_id,
        title=book_details_result.title,
        author=book_details_result.author,
        isbn=book_details_result.isbn.value,
    )
