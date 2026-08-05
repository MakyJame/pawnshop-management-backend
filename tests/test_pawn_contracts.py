from uuid import uuid4

from fastapi.testclient import TestClient

#from app.main import app
#lient = TestClient(app)


def unique_phone() -> str:
    return f"09{str(uuid4().int)[-8:]}"


def unique_contract_code() -> str:
    return f"HD-{str(uuid4())[:8]}"


def create_customer(
    client: TestClient,
) -> int:
    response = client.post(
        "/customers",
        json={
            "name": "Contract Test Customer",
            "phone": unique_phone(),
        },
    )

    assert response.status_code == 201

    return response.json()["id"]


def test_create_pawn_contract_success(
    client: TestClient,
) -> None:
    customer_id = create_customer(client)

    response = client.post(
        "/pawn-contracts",
        json={
            "contract_code": unique_contract_code(),
            "customer_id": customer_id,
            "principal_amount": 11000000,
            "monthly_interest_amount": 550000,
            "start_date": "2026-08-03",
            "due_date": "2026-09-03",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["customer_id"] == customer_id
    assert data["status"] == "active"


def test_create_pawn_contract_rejects_missing_customer(
    client: TestClient
) -> None:
    response = client.post(
        "/pawn-contracts",
        json={
            "contract_code": unique_contract_code(),
            "customer_id": 999999999,
            "principal_amount": 11000000,
            "monthly_interest_amount": 550000,
            "start_date": "2026-08-03",
            "due_date": "2026-09-03",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Customer not found.",
    }


def test_create_pawn_contract_rejects_duplicate_code(
    client: TestClient
) -> None:
    customer_id = create_customer(client)
    contract_code = unique_contract_code()

    payload = {
        "contract_code": contract_code,
        "customer_id": customer_id,
        "principal_amount": 11000000,
        "monthly_interest_amount": 550000,
        "start_date": "2026-08-03",
        "due_date": "2026-09-03",
    }

    first_response = client.post(
        "/pawn-contracts",
        json=payload,
    )

    second_response = client.post(
        "/pawn-contracts",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_create_pawn_contract_rejects_invalid_dates(
    client: TestClient
) -> None:
    customer_id = create_customer(client)

    response = client.post(
        "/pawn-contracts",
        json={
            "contract_code": unique_contract_code(),
            "customer_id": customer_id,
            "principal_amount": 11000000,
            "monthly_interest_amount": 550000,
            "start_date": "2026-09-03",
            "due_date": "2026-08-03",
        },
    )

    assert response.status_code == 422


def test_get_missing_pawn_contract_returns_not_found(
    client: TestClient
) -> None:
    response = client.get(
        "/pawn-contracts/999999999",
    )

    assert response.status_code == 404
