from fastapi.testclient import TestClient

from api.main import app


def test_prediction_and_metrics():
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ready"
        assert client.get("/metrics").json()["calls"] == 0
        response = client.post("/predict", json={"features": [14.23,1.71,2.43,15.6,127,2.8,3.06,.28,2.29,5.64,1.04,3.92,1065]})
        assert response.status_code == 200
        result = response.json()
        assert result["prediction"] in (1, 2, 3)
        assert 0 <= result["confidence"] <= 1
        assert client.get("/version").json()["model"] == result["modelVersion"]
        assert client.get("/metrics").json()["calls"] == 1


def test_invalid_input():
    with TestClient(app) as client:
        assert client.post("/predict", json={"features": [1]}).status_code == 422


def test_missing_body():
    with TestClient(app) as client:
        assert client.post("/predict").status_code == 422
