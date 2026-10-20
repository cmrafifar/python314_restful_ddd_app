from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial

from fastapi import FastAPI

from bookstore_api.api.books.router import router as books_router
from bookstore_api.application.books.create_book import (
    CreateBookService,
)
from bookstore_api.config import Settings, get_settings
from bookstore_api.infrastructure.persistence.database import (
    create_db_engine,
    create_session_factory,
)
from bookstore_api.infrastructure.persistence.sqlalchemy_unit_of_work import (
    SqlAlchemyUnitOfWork,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else get_settings()
    engine = create_db_engine(config)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(
        title=config.name,
        debug=config.debug,
        version="0.1.0",
        lifespan=lifespan,
    )

    # Use the Engine already constructed from your Settings.
    session_factory = create_session_factory(engine)

    uow_factory = partial(
        SqlAlchemyUnitOfWork,
        session_factory,
    )

    app.state.create_book_service = CreateBookService(
        uow_factory=uow_factory,
    )
    app.include_router(books_router)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
