from uuid import uuid4

from fastapi.testclient import TestClient

#from app.main import app
#lient = TestClient(app)


def unique_phone() -> str:
    return f"09{str(uuid4().int)[-8:]}"

def unique_contract_code() -> str:
    return f"HD-{str(uuid4())[:8]}"

def unique_license_plate() -> str:
    return f"TEST-{str(uuid4().int)[-6:]}"

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
            "start_date": "2026-08-22",
            "due_date": "2026-09-22",
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

def test_create_contract_with_assets_success(
    client: TestClient,
) -> None:
    customer_id = create_customer(client)

    response = client.post(
        "/pawn-contracts/with-assets",
        json={
            "contract_code": unique_contract_code(),
            "customer_id": customer_id,
            "principal_amount": 11000000,
            "monthly_interest_amount": 550000,
            "start_date": "2026-08-06",
            "due_date": "2026-09-06",
            "assets": [
                {
                    "asset_type": "motorcycle",
                    "description": "Honda Air Blade 2013",
                    "brand": "Honda",
                    "model_year": 2013,
                    "license_plate": unique_license_plate(),
                }
            ],
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["customer_id"] == customer_id
    assert len(data["assets"]) == 1
    assert data["assets"][0]["asset_type"] == "motorcycle"

def test_create_contract_requires_at_least_one_asset(
    client: TestClient,
) -> None:
    customer_id = create_customer(client)

    response = client.post(
        "/pawn-contracts/with-assets",
        json={
            "contract_code": unique_contract_code(),
            "customer_id": customer_id,
            "principal_amount": 11000000,
            "monthly_interest_amount": 550000,
            "start_date": "2026-08-06",
            "due_date": "2026-09-06",
            "assets": [],
        },
    )

    assert response.status_code == 422

def test_create_contract_with_assets_rejects_pawned_license_plate(
    client: TestClient,
) -> None:
    customer_id = create_customer(client)
    license_plate = unique_license_plate()

    first_payload = {
        "contract_code": unique_contract_code(),
        "customer_id": customer_id,
        "principal_amount": 11000000,
        "monthly_interest_amount": 550000,
        "start_date": "2026-08-06",
        "due_date": "2026-09-06",
        "assets": [
            {
                "asset_type": "motorcycle",
                "description": "First motorcycle",
                "license_plate": license_plate,
            }
        ],
    }

    second_payload = {
        **first_payload,
        "contract_code": unique_contract_code(),
    }

    first_response = client.post(
        "/pawn-contracts/with-assets",
        json=first_payload,
    )

    second_response = client.post(
        "/pawn-contracts/with-assets",
        json=second_payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409

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
    
def test_patch_contract_cannot_set_status_to_redeemed(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    response = client.patch(
        f"/pawn-contracts/{contract_id}",
        json={
            "status": "redeemed",
        },
    )

    assert response.status_code == 409

    assert response.json() == {
        "detail": (
            "Pawn contract must be redeemed through "
            "the redemption endpoint."
        ),
    }

    contract_response = client.get(
        f"/pawn-contracts/{contract_id}"
    )

    assert contract_response.status_code == 200
    assert contract_response.json()["status"] == "active"

    payments_response = client.get(
        f"/pawn-contracts/{contract_id}/payments"
    )
    
    assert payments_response.status_code == 200
    assert payments_response.json() == []

def test_redeem_endpoint_is_allowed_to_set_redeemed_status(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    response = client.post(
        f"/pawn-contracts/{contract_id}/redeem",
        json={
            "amount": 11000000,
            "payment_date": "2026-08-22",
        },
    )

    assert response.status_code == 201

    contract_response = client.get(
        f"/pawn-contracts/{contract_id}"
    )

    assert contract_response.json()["status"] == "redeemed"
