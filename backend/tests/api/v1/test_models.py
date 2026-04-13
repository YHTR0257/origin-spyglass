import pytest
from fastapi.testclient import TestClient

from origin_spyglass.main import app

client = TestClient(app)


def test_models_ok() -> None:
    response = client.get("/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert len(data["data"]) == 1
    assert data["data"][0]["object"] == "model"
    assert "id" in data["data"][0]


@pytest.mark.parametrize("method", ["post", "put", "delete", "patch"])
def test_models_method_not_allowed(method: str) -> None:
    response = getattr(client, method)("/v1/models")
    assert response.status_code == 405
