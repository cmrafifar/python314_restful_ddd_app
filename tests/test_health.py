from fastapi.testclient import TestClient
from httpx import Response

from bookstore_api.main import create_app


def test_health_endpoint() -> None:
    app = create_app()

    with TestClient(app) as client:
        response: Response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
