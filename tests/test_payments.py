from uuid import uuid4

from fastapi.testclient import TestClient


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
            "name": "Payment Test Customer",
            "phone": unique_phone(),
        },
    )

    assert response.status_code == 201

    return response.json()["id"]


def create_contract(
    client: TestClient,
) -> int:
    customer_id = create_customer(client)

    response = client.post(
        "/pawn-contracts",
        json={
            "contract_code": unique_contract_code(),
            "customer_id": customer_id,
            "principal_amount": 11000000,
            "monthly_interest_amount": 550000,
            "start_date": "2026-08-01",
            "due_date": "2026-09-01",
        },
    )

    assert response.status_code == 201

    return response.json()["id"]

def test_create_payment_success(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    response = client.post(
        "/payments",
        json={
            "contract_id": contract_id,
            "amount": 550000,
            "payment_type": "interest",
            "payment_date": "2026-08-13",
            "note": "Monthly interest",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["contract_id"] == contract_id
    assert data["payment_type"] == "interest"
    assert data["note"] == "Monthly interest"

def test_create_payment_rejects_missing_contract(
    client: TestClient,
) -> None:
    response = client.post(
        "/payments",
        json={
            "contract_id": 999999999,
            "amount": 550000,
            "payment_type": "interest",
            "payment_date": "2026-08-13",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Pawn contract not found.",
    }

def test_get_payment_success(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    create_response = client.post(
        "/payments",
        json={
            "contract_id": contract_id,
            "amount": 550000,
            "payment_type": "interest",
            "payment_date": "2026-08-13",
        },
    )

    assert create_response.status_code == 201

    payment_id = create_response.json()["id"]

    response = client.get(
        f"/payments/{payment_id}",
    )

    assert response.status_code == 200
    assert response.json()["id"] == payment_id

def test_get_missing_payment_returns_not_found(
    client: TestClient,
) -> None:
    response = client.get(
        "/payments/999999999",
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Payment not found.",
    }

def test_list_contract_payments(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    client.post(
        "/payments",
        json={
            "contract_id": contract_id,
            "amount": 550000,
            "payment_type": "interest",
            "payment_date": "2026-08-01",
        },
    )

    client.post(
        "/payments",
        json={
            "contract_id": contract_id,
            "amount": 1000000,
            "payment_type": "principal",
            "payment_date": "2026-08-13",
        },
    )

    response = client.get(
        f"/pawn-contracts/{contract_id}/payments",
    )

    assert response.status_code == 200

    payments = response.json()

    assert len(payments) == 2
    assert payments[0]["payment_type"] == "interest"
    assert payments[1]["payment_type"] == "principal"

def test_create_payment_rejects_redeemed_contract(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    update_response = client.patch(
        f"/pawn-contracts/{contract_id}",
        json={
            "status": "redeemed",
        },
    )

    assert update_response.status_code == 200

    response = client.post(
        "/payments",
        json={
            "contract_id": contract_id,
            "amount": 550000,
            "payment_type": "interest",
            "payment_date": "2026-08-13",
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Pawn contract is closed and cannot receive payments.",
    }
