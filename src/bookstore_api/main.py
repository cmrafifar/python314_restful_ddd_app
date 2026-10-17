from fastapi import FastAPI

from bookstore_api.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else get_settings()

    app = FastAPI(
        title=config.name,
        debug=config.debug,
        version="0.1.0",
    )

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
