from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def create_unique_phone() -> str:
    suffix = str(uuid4().int)[-8:]

    return f"09{suffix}"

def test_create_customer_returns_created_customer() -> None:
    phone = create_unique_phone()

    response = client.post(
        "/customers",
        json={
            "name": "API Test Customer",
            "phone": phone,
        },
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["name"] == "API Test Customer"
    assert response_data["phone"] == phone
    assert isinstance(response_data["id"], int)

def test_create_customer_rejects_duplicate_phone() -> None:
    phone = create_unique_phone()

    customer_data = {
        "name": "Duplicate Test",
        "phone": phone,
    }

    first_response = client.post(
        "/customers",
        json=customer_data,
    )

    second_response = client.post(
        "/customers",
        json=customer_data,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": "Customer phone already exists.",
    }

def test_get_missing_customer_returns_not_found() -> None:
    response = client.get(
        "/customers/999999999",
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Customer not found.",
    }


def test_list_customers_returns_list() -> None:
    response = client.get("/customers")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
