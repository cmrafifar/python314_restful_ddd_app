from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        extra="ignore",
    )

    name: str = "Bookstore API"
    environment: str = "development"
    debug: bool = False
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "bookstore"
    db_user: str = "bookstore"
    db_password: str


def get_settings() -> Settings:
    # BaseSettings loads required fields from the environment at runtime.
    return Settings()  # pyright: ignore[reportCallIssue]
