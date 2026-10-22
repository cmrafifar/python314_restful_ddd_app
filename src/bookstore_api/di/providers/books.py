from dishka import Provider, Scope, provide

from bookstore_api.application.books.create_book import CreateBookService
from bookstore_api.application.books.get_book_details import GetBookDetailsService


class BooksProvider(Provider):
    scope = Scope.APP

    create_book_service = provide(CreateBookService)

    get_book_details_service = provide(
        GetBookDetailsService,
        scope=Scope.REQUEST,
    )
