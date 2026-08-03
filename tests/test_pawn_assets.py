from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def unique_phone() -> str:
    return f"09{str(uuid4().int)[-8:]}"


def unique_contract_code() -> str:
    return f"HD-{str(uuid4())[:8]}"


def unique_license_plate() -> str:
    return f"TEST-{str(uuid4().int)[-6:]}"


def create_customer() -> int:
    response = client.post(
        "/customers",
        json={
            "name": "Asset Test Customer",
            "phone": unique_phone(),
        },
    )

    assert response.status_code == 201

    return response.json()["id"]


def create_contract() -> int:
    customer_id = create_customer()

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

    return response.json()["id"]


def test_create_pawn_asset_success() -> None:
    contract_id = create_contract()
    license_plate = unique_license_plate()

    response = client.post(
        "/pawn-assets",
        json={
            "contract_id": contract_id,
            "asset_type": "motorcycle",
            "description": "Xe máy Air Blade đời 2013",
            "brand": "Air Blade",
            "model_year": 2013,
            "license_plate": license_plate,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["contract_id"] == contract_id
    assert data["license_plate"] == license_plate


def test_create_pawn_asset_rejects_missing_contract() -> None:
    response = client.post(
        "/pawn-assets",
        json={
            "contract_id": 999999999,
            "asset_type": "motorcycle",
            "description": "Missing contract test",
            "brand": "Honda",
            "model_year": 2013,
            "license_plate": unique_license_plate(),
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Pawn contract not found.",
    }


def test_create_pawn_asset_rejects_duplicate_active_license_plate() -> None:
    first_contract_id = create_contract()
    second_contract_id = create_contract()
    license_plate = unique_license_plate()

    first_response = client.post(
        "/pawn-assets",
        json={
            "contract_id": first_contract_id,
            "asset_type": "motorcycle",
            "description": "First asset",
            "brand": "Honda",
            "model_year": 2013,
            "license_plate": license_plate,
        },
    )

    second_response = client.post(
        "/pawn-assets",
        json={
            "contract_id": second_contract_id,
            "asset_type": "motorcycle",
            "description": "Second asset",
            "brand": "Honda",
            "model_year": 2014,
            "license_plate": license_plate,
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_get_missing_pawn_asset_returns_not_found() -> None:
    response = client.get(
        "/pawn-assets/999999999",
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Pawn asset not found.",
    }


def test_list_assets_by_contract() -> None:
    contract_id = create_contract()

    create_response = client.post(
        "/pawn-assets",
        json={
            "contract_id": contract_id,
            "asset_type": "motorcycle",
            "description": "Contract asset test",
            "brand": "Honda",
            "model_year": 2013,
            "license_plate": unique_license_plate(),
        },
    )

    assert create_response.status_code == 201

    response = client.get(
        f"/pawn-contracts/{contract_id}/assets",
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1
