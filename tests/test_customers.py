from uuid import uuid4

from fastapi.testclient import TestClient
#from app.main import app
#client = TestClient(app)

def create_unique_phone() -> str:
    return f"09{str(uuid4().int)[-8:]}"

def test_create_customer_returns_created_customer(
    client: TestClient,
) -> None:
    response = client.post(
        "/customers",
        json={
            "name": "API Test Customer",
            "phone": create_unique_phone(),
        },
    )

    assert response.status_code == 201

def test_create_customer_rejects_duplicate_phone(
    client: TestClient,
) -> None:
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

def test_get_missing_customer_returns_not_found(
    client: TestClient,
) -> None:
    response = client.get(
        "/customers/999999999",
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Customer not found.",
    }


def test_list_customers_returns_list(
    client: TestClient,
) -> None:
    response = client.get("/customers")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
