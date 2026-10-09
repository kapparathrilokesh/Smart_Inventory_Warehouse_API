
import sys
from pathlib import Path

# Add the project root to Python's import path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_docs_available():
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_available():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "paths" in response.json()
