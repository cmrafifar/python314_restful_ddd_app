import pytest
from pydantic import ValidationError

from bookstore_api.config import get_settings


def test_settings_load_database_password_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_DB_PASSWORD", "test-settings-password")

    assert get_settings().db_password == "test-settings-password"


def test_settings_require_database_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_DB_PASSWORD", raising=False)

    with pytest.raises(ValidationError) as error:
        get_settings()

    assert any(
        issue["loc"] == ("db_password",) and issue["type"] == "missing"
        for issue in error.value.errors()
    )
