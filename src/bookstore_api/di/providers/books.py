from dishka import Provider, Scope, provide

from bookstore_api.application.books.create_book import CreateBookService
from bookstore_api.application.books.get_book_details import GetBookDetailsService
from bookstore_api.application.books.update_book import UpdateBookService


class BooksProvider(Provider):
    scope = Scope.APP

    create_book_service = provide(CreateBookService)
    update_book_service = provide(UpdateBookService)

    get_book_details_service = provide(
        GetBookDetailsService,
        scope=Scope.REQUEST,
    )
