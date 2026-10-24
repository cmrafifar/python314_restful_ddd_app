from typing import Annotated
from uuid import UUID

from dishka.integrations.fastapi import DishkaSyncRoute, FromDishka
from fastapi import APIRouter, Header, HTTPException, Query, Response, status

from bookstore_api.api.books.conditional_requests import (
    IF_MATCH_DESCRIPTION,
    book_etag,
    parse_if_match,
)
from bookstore_api.api.books.pagination import decode_cursor, encode_cursor
from bookstore_api.api.books.responses import BOOK_NOT_FOUND_RESPONSES, BOOK_READ_RESPONSES
from bookstore_api.api.books.schemas import (
    BookDetailsResponse,
    BookListParams,
    BookListResponse,
    BookResponse,
    CreateBookRequest,
    PatchBookRequest,
    ReplaceBookRequest,
)
from bookstore_api.api.responses import CONDITIONAL_UPDATE_RESPONSES, ErrorResponse
from bookstore_api.application.books.commands import (
    CreateBookCommand,
    DeleteBookCommand,
    UpdateBookCommand,
)
from bookstore_api.application.books.create_book import (
    BookAlreadyExistsError,
    CreateBookService,
)
from bookstore_api.application.books.delete_book import DeleteBookService
from bookstore_api.application.books.errors import BookVersionConflictError
from bookstore_api.application.books.get_book_details import (
    BookNotFoundError,
    GetBookDetailsResult,
    GetBookDetailsService,
)
from bookstore_api.application.books.list_books import ListBooksQuery, ListBooksService
from bookstore_api.application.books.update_book import UpdateBookService

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
            detail="A resource with the supplied ISBN already exists",
        ) from exc

    return BookResponse(id=result.book_id)


@router.get(
    "",
    response_model=BookListResponse,
    status_code=status.HTTP_200_OK,
    summary="List matching books",
    description=(
        "Returns the first matching books ordered by ISBN ascending. Optional title and author "
        "filters use case- and accent-sensitive literal substrings and combine with AND. "
        "Trims outer filter whitespace; blank or oversized filters, unknown query parameters, "
        "and invalid limits return 422. Percent and underscore characters are literal. "
        "The limit defaults to 20 and must be between 1 and 100. Empty collections return 200. "
        "Use the opaque next_cursor or previous_cursor as the cursor query parameter to navigate; "
        "unavailable cursors are null. Preserve title and author filters across requests; changing "
        "filters starts a new traversal without a cursor. Limits may change between requests. "
        "Cursors encode version 1, an ISBN boundary, and direction using unpadded URL-safe Base64. "
        "Malformed cursors, unsupported versions, and invalid boundaries or directions return 422. "
        "Items always use ISBN ascending order. has_more means next_cursor is available, including "
        "when navigating backward. Empty pages return null cursors and has_more=false; restart "
        "without a cursor if collection changes leave a continuation empty. Deleted boundary books "
        "do not invalidate cursors. Navigation does not provide a snapshot across requests. "
        "Returns no collection ETag; retrieve a book individually before conditional writes."
    ),
)
def list_books(
    params: Annotated[BookListParams, Query()],
    service: FromDishka[ListBooksService],
) -> BookListResponse:
    result = service.execute(
        ListBooksQuery(
            title=params.title,
            author=params.author,
            limit=params.limit,
            cursor=decode_cursor(params.cursor) if params.cursor is not None else None,
        )
    )
    return BookListResponse(
        items=[_book_response(item) for item in result.items],
        has_more=result.has_more,
        next_cursor=encode_cursor(result.next_cursor),
        previous_cursor=encode_cursor(result.previous_cursor),
    )


@router.get(
    "/{book_id}",
    response_model=BookDetailsResponse,
    status_code=status.HTTP_200_OK,
    responses=BOOK_READ_RESPONSES,
)
def get_book(
    book_id: UUID,
    response: Response,
    service: FromDishka[GetBookDetailsService],
) -> BookDetailsResponse:
    try:
        book_details_result = service.execute(book_id)
    except BookNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "book_not_found",
                "message": "Resource not found",
            },
        ) from exc
    response.headers["ETag"] = book_etag(book_id, book_details_result.version)
    return _book_response(book_details_result)


@router.put(
    "/{book_id}",
    response_model=BookDetailsResponse,
    responses={**CONDITIONAL_UPDATE_RESPONSES, **BOOK_NOT_FOUND_RESPONSES},
    summary="Replace the resource's writable details",
    description=(
        "Requires title and author; ISBN and ID are read-only. Uses If-Match to prevent lost updates. "
        "Trims outer whitespace. Returns the updated representation, but no ETag because PUT input "
        "may be transformed; GET the resource to obtain its next validator. "
        "Does not create missing resources."
    ),
)
def replace_book(
    book_id: UUID,
    request: ReplaceBookRequest,
    service: FromDishka[UpdateBookService],
    if_match: Annotated[list[str] | None, Header(description=IF_MATCH_DESCRIPTION)] = None,
) -> BookDetailsResponse:
    result = _update_book(book_id, request.title, request.author, if_match, service)
    return _book_response(result)


@router.patch(
    "/{book_id}",
    response_model=BookDetailsResponse,
    responses={**CONDITIONAL_UPDATE_RESPONSES, **BOOK_READ_RESPONSES},
    summary="Change selected resource details",
    description=(
        "Send title, author, or both as application/json. Omitted fields remain unchanged. "
        "An empty object, explicit null, unknown fields, and invalid text return 422. "
        "This is a field-update contract, not JSON Patch or JSON Merge Patch. "
        "Requires If-Match; returns a fresh ETag on success."
    ),
)
def patch_book(
    book_id: UUID,
    request: PatchBookRequest,
    response: Response,
    service: FromDishka[UpdateBookService],
    if_match: Annotated[list[str] | None, Header(description=IF_MATCH_DESCRIPTION)] = None,
) -> BookDetailsResponse:
    result = _update_book(book_id, request.title, request.author, if_match, service)
    response.headers["ETag"] = book_etag(book_id, result.version)
    return _book_response(result)


@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **CONDITIONAL_UPDATE_RESPONSES,
        **BOOK_NOT_FOUND_RESPONSES,
        status.HTTP_412_PRECONDITION_FAILED: {
            "model": ErrorResponse,
            "description": (
                "No strong tag matched, or the resource changed or was deleted before the "
                "operation completed. Retrieve its current state and reconcile before retrying."
            ),
        },
    },
    summary="Delete the resource",
    description=(
        "Permanently deletes the resource and frees its ISBN for reuse. Requires If-Match; "
        "supports strong tag lists and *. Success returns an empty 204 without ETag. "
        "Missing or already deleted resources return 404; version conflicts return 412."
    ),
)
def delete_book(
    book_id: UUID,
    service: FromDishka[DeleteBookService],
    if_match: Annotated[list[str] | None, Header(description=IF_MATCH_DESCRIPTION)] = None,
) -> None:
    versions = parse_if_match(book_id, if_match)

    try:
        service.execute(DeleteBookCommand(book_id, expected_versions=versions))

    except BookNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "book_not_found", "message": "Resource not found"},
        ) from exc

    except BookVersionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail={
                "code": "precondition_failed",
                "message": (
                    "The resource changed or was deleted; "
                    "reconcile its current state before retrying"
                ),
            },
        ) from exc


def _update_book(
    book_id: UUID,
    title: str | None,
    author: str | None,
    if_match: list[str] | None,
    service: UpdateBookService,
) -> GetBookDetailsResult:
    versions = parse_if_match(book_id, if_match)
    try:
        return service.execute(
            UpdateBookCommand(
                book_id=book_id,
                expected_versions=versions,
                title=title,
                author=author,
            )
        )
    except BookNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "book_not_found", "message": "Resource not found"},
        ) from exc
    except BookVersionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail={
                "code": "precondition_failed",
                "message": (
                    "The resource changed or was deleted; "
                    "reconcile its current state before retrying"
                ),
            },
        ) from exc


def _book_response(result: GetBookDetailsResult) -> BookDetailsResponse:
    return BookDetailsResponse(
        id=result.book_id,
        title=result.title,
        author=result.author,
        isbn=result.isbn.value,
    )
