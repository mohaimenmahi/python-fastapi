from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_docs_accessible_without_auth():
    response = client.get("/docs")

    assert response.status_code == 200


def test_openapi_accessible_without_auth():
    response = client.get("/openapi.json")

    assert response.status_code == 200
