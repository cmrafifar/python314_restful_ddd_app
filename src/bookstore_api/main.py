from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

from dishka import Provider
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from bookstore_api.api.books.router import router as books_router
from bookstore_api.config import Settings, get_settings
from bookstore_api.di.container import create_container


def create_app(
    settings: Settings | None = None,
    *,
    provider_overrides: Sequence[Provider] = (),
) -> FastAPI:
    config = settings if settings is not None else get_settings()
    container = create_container(config, *provider_overrides)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            container.close()

    app = FastAPI(
        title=config.name,
        debug=config.debug,
        version="0.1.0",
        lifespan=lifespan,
    )

    setup_dishka(container, app)
    app.include_router(books_router)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
