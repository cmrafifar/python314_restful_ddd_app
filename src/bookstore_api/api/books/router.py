from dishka.integrations.fastapi import DishkaSyncRoute, FromDishka
from fastapi import APIRouter, HTTPException, status

from bookstore_api.api.books.schemas import (
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
