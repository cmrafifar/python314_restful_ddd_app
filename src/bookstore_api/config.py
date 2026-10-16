from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        extra="ignore",
    )

    name: str = "Bookstore API"
    environment: str = "development"
    debug: bool = False


def get_settings() -> Settings:
    return Settings()



