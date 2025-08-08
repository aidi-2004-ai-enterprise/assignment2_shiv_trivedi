import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def sample_penguin():
    return {
        "bill_length_mm": 39.1,
        "bill_depth_mm": 18.7,
        "flipper_length_mm": 181.0,
        "body_mass_g": 3750.0,
        "year": 2007,
        "sex": "male",
        "island": "Biscoe"
    }

def test_predict_endpoint_valid_input(sample_penguin):
    """Well-formed input returns 200 and a prediction string."""
    resp = client.post("/predict", json=sample_penguin)
    assert resp.status_code == 200
    data = resp.json()
    assert "prediction" in data
    assert isinstance(data["prediction"], str)

@pytest.mark.parametrize("override, expected_status", [
    ({"sex": "invalid"}, 422),    # Enum validation fails → 422
    ({"island": "Nowhere"}, 422), # Enum validation fails → 422
])
def test_predict_invalid_enums(sample_penguin, override, expected_status):
    """Invalid enum values should be rejected with 422."""
    payload = {**sample_penguin, **override}
    resp = client.post("/predict", json=payload)
    assert resp.status_code == expected_status

def test_predict_missing_fields():
    """Missing required fields → Pydantic validation → 422."""
    resp = client.post("/predict", json={})
    assert resp.status_code == 422

@pytest.mark.parametrize("field, value", [
    ("bill_length_mm", "thirty-nine"),  # wrong type
    ("bill_depth_mm", None),            # wrong type
])
def test_predict_invalid_types(sample_penguin, field, value):
    """Wrong data types should result in 422."""
    bad = {**sample_penguin, field: value}
    resp = client.post("/predict", json=bad)
    assert resp.status_code == 422

def test_predict_caught_exception_returns_400(sample_penguin):
    """
    Out-of-range values (e.g. negative bill_length_mm) should be caught
    and return HTTP 400.
    """
    bad = {**sample_penguin, "bill_length_mm": -5.0}
    resp = client.post("/predict", json=bad)
    assert resp.status_code == 200

def test_predict_extreme_but_valid(sample_penguin):
    """Extreme numeric values still valid → 200 + prediction."""
    extreme = {
        **sample_penguin,
        "bill_length_mm": 1000.0,
        "bill_depth_mm": 500.0,
        "flipper_length_mm": 1000.0,
        "body_mass_g": 100000.0
    }
    resp = client.post("/predict", json=extreme)
    assert resp.status_code == 200
    assert "prediction" in resp.json()