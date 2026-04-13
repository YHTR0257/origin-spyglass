import pytest
from fastapi.testclient import TestClient

from origin_spyglass.main import app

client = TestClient(app)


def test_health_ok() -> None:
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app_name" in data
    assert "environment" in data


@pytest.mark.parametrize("method", ["post", "put", "delete", "patch"])
def test_health_method_not_allowed(method: str) -> None:
    response = getattr(client, method)("/v1/health")
    assert response.status_code == 405
