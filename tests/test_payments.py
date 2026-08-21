from uuid import uuid4

from fastapi.testclient import TestClient
from decimal import Decimal

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

def test_payment_summary_before_any_payment(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    response = client.get(
        f"/pawn-contracts/{contract_id}/payment-summary",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["contract_id"] == contract_id
    assert Decimal(data["total_interest_paid"]) == Decimal("0")
    assert Decimal(data["total_principal_paid"]) == Decimal("0")
    assert Decimal(data["total_redemption_paid"]) == Decimal("0")
    assert Decimal(data["outstanding_principal"]) == Decimal("11000000")

def test_interest_payment_does_not_reduce_principal(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    response = client.post(
        "/payments",
        json={
            "contract_id": contract_id,
            "amount": 550000,
            "payment_type": "interest",
            "payment_date": "2026-08-15",
        },
    )

    assert response.status_code == 201

    summary_response = client.get(
        f"/pawn-contracts/{contract_id}/payment-summary",
    )

    assert summary_response.status_code == 200

    data = summary_response.json()

    assert Decimal(data["total_interest_paid"]) == Decimal("550000")
    assert Decimal(data["total_principal_paid"]) == Decimal("0")
    assert Decimal(data["total_redemption_paid"]) == Decimal("0")
    assert Decimal(data["outstanding_principal"]) == Decimal("11000000")

def test_principal_payment_reduces_outstanding_principal(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    response = client.post(
        "/payments",
        json={
            "contract_id": contract_id,
            "amount": 2000000,
            "payment_type": "principal",
            "payment_date": "2026-08-15",
        },
    )

    assert response.status_code == 201

    summary_response = client.get(
        f"/pawn-contracts/{contract_id}/payment-summary",
    )

    assert summary_response.status_code == 200

    data = summary_response.json()

    assert Decimal(data["total_principal_paid"]) == Decimal("2000000")

    assert Decimal(
        data["outstanding_principal"]
    ) == Decimal("9000000")

def test_payment_summary_combines_multiple_payments(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    payments = [
        {
            "amount": 550000,
            "payment_type": "interest",
        },
        {
            "amount": 550000,
            "payment_type": "interest",
        },
        {
            "amount": 2000000,
            "payment_type": "principal",
        },
        {
            "amount": 1000000,
            "payment_type": "principal",
        },
    ]

    for payment in payments:
        response = client.post(
            "/payments",
            json={
                "contract_id": contract_id,
                "amount": payment["amount"],
                "payment_type": payment["payment_type"],
                "payment_date": "2026-08-15",
            },
        )

        assert response.status_code == 201

    response = client.get(
        f"/pawn-contracts/{contract_id}/payment-summary",
    )

    assert response.status_code == 200

    data = response.json()

    assert Decimal(
        data["total_interest_paid"]
    ) == Decimal("1100000")

    assert Decimal(
        data["total_principal_paid"]
    ) == Decimal("3000000")

    assert Decimal(
        data["outstanding_principal"]
    ) == Decimal("8000000")

def test_payment_summary_rejects_missing_contract(
    client: TestClient,
) -> None:
    response = client.get(
        "/pawn-contracts/999999999/payment-summary",
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Pawn contract not found.",
    }

def test_principal_payment_rejects_amount_above_outstanding(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    first_response = client.post(
        "/payments",
        json={
            "contract_id": contract_id,
            "amount": 3000000,
            "payment_type": "principal",
            "payment_date": "2026-08-18",
        },
    )

    assert first_response.status_code == 201

    response = client.post(
        "/payments",
        json={
            "contract_id": contract_id,
            "amount": 9000000,
            "payment_type": "principal",
            "payment_date": "2026-08-18",
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Principal payment exceeds outstanding principal.",
    }

def test_principal_payment_allows_exact_outstanding_amount(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    first_response = client.post(
        "/payments",
        json={
            "contract_id": contract_id,
            "amount": 3000000,
            "payment_type": "principal",
            "payment_date": "2026-08-18",
        },
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/payments",
        json={
            "contract_id": contract_id,
            "amount": 8000000,
            "payment_type": "principal",
            "payment_date": "2026-08-18",
        },
    )

    assert second_response.status_code == 201

def test_interest_payment_is_not_checked_against_outstanding_principal(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    response = client.post(
        "/payments",
        json={
            "contract_id": contract_id,
            "amount": 12000000,
            "payment_type": "interest",
            "payment_date": "2026-08-18",
        },
    )

    assert response.status_code == 201  

def test_redeem_contract_success(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    principal_response = client.post(
        "/payments",
        json={
            "contract_id": contract_id,
            "amount": 3000000,
            "payment_type": "principal",
            "payment_date": "2026-08-18",
        },
    )

    assert principal_response.status_code == 201

    response = client.post(
        f"/pawn-contracts/{contract_id}/redeem",
        json={
            "amount": 8000000,
            "payment_date": "2026-08-18",
            "note": "Redeemed",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["contract_id"] == contract_id
    assert data["payment"]["payment_type"] == "redemption"

    contract_response = client.get(
        f"/pawn-contracts/{contract_id}"
    )

    assert contract_response.status_code == 200
    assert contract_response.json()["status"] == "redeemed"

def test_redeem_contract_rejects_incorrect_amount(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    response = client.post(
        f"/pawn-contracts/{contract_id}/redeem",
        json={
            "amount": 10000000,
            "payment_date": "2026-08-18",
        },
    )

    assert response.status_code == 409

    assert response.json() == {
        "detail": "Redemption amount must equal outstanding principal.",
    }

def test_failed_redemption_does_not_change_contract_status(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    response = client.post(
        f"/pawn-contracts/{contract_id}/redeem",
        json={
            "amount": 10000000,
            "payment_date": "2026-08-18",
        },
    )

    assert response.status_code == 409

    contract_response = client.get(
        f"/pawn-contracts/{contract_id}"
    )

    assert contract_response.status_code == 200
    assert contract_response.json()["status"] == "active"

    payments_response = client.get(
        f"/pawn-contracts/{contract_id}/payments"
    )

    assert payments_response.status_code == 200

    payments = payments_response.json()

    assert all(
        payment["payment_type"] != "redemption"
        for payment in payments
    )

def test_redeemed_contract_cannot_be_redeemed_again(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    payload = {
        "amount": 11000000,
        "payment_date": "2026-08-18",
    }

    first_response = client.post(
        f"/pawn-contracts/{contract_id}/redeem",
        json=payload,
    )

    assert first_response.status_code == 201

    second_response = client.post(
        f"/pawn-contracts/{contract_id}/redeem",
        json=payload,
    )

    assert second_response.status_code == 409

def test_payment_summary_after_redemption_has_zero_outstanding(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    principal_response = client.post(
        "/payments",
        json={
            "contract_id": contract_id,
            "amount": 3000000,
            "payment_type": "principal",
            "payment_date": "2026-08-20",
        },
    )

    assert principal_response.status_code == 201

    redeem_response = client.post(
        f"/pawn-contracts/{contract_id}/redeem",
        json={
            "amount": 8000000,
            "payment_date": "2026-08-20",
        },
    )

    assert redeem_response.status_code == 201

    response = client.get(
        f"/pawn-contracts/{contract_id}/payment-summary"
    )

    assert response.status_code == 200

    data = response.json()

    assert Decimal(
        data["total_principal_paid"]
    ) == Decimal("3000000")

    assert Decimal(
        data["total_redemption_paid"]
    ) == Decimal("8000000")

    assert Decimal(
        data["outstanding_principal"]
    ) == Decimal("0")

def test_direct_redemption_payment_is_rejected(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    
    response = client.post(
        "/payments",
        json={
            "contract_id": contract_id,
            "amount": 11000000,
            "payment_type": "redemption",
            "payment_date": "2026-08-20",
        },
    )
    assert response.status_code == 409

    assert response.json() == {
        "detail": (
            "Redemption payments must be created "
            "through the contract redemption endpoint."
        ),
    }
    payments_response = client.get(
        f"/pawn-contracts/{contract_id}/payments"
    )
    assert payments_response.status_code == 200
    assert payments_response.json() == []
