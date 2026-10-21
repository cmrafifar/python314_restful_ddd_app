from dishka import Provider, Scope, provide

from bookstore_api.application.books.create_book import CreateBookService


class BooksProvider(Provider):
    scope = Scope.APP

    create_book_service = provide(CreateBookService)
