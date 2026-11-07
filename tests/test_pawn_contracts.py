from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.models.customer import Customer
from app.models.pawn_asset import PawnAsset
from app.models.pawn_contract import ContractStatus, PawnContract

from app.repositories.customer_repository import (
    create_customer as create_customer_in_db,
)

from app.schemas.customer import CustomerCreate
from app.schemas.pawn_contract import (
    PawnContractCreate,
    PawnContractWithAssetsCreate,
)

from app.services.pawn_contract_service import (
    create_pawn_contract_with_assets,
    liquidate_contract,
    mark_overdue_contracts,
)

def unique_phone() -> str:
    return f"09{str(uuid4().int)[-8:]}"

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

    license_plate = unique_license_plate()

    response = client.post(
        "/pawn-contracts/with-assets",
        json={
            "customer_id": customer_id,
            "principal_amount": 11000000,
            "start_date": "2026-08-22",
            "assets": [
                {
                    "brand": "Honda",
                    "model_year": 2013,
                    "license_plate": license_plate,
                }
            ],
        },
    )

    assert response.status_code == 201

    return response.json()["id"]

def create_liquidated_contract(
    db_session,
) -> int:
    customer = create_customer_in_db(
        db_session,
        CustomerCreate(
            name="Liquidated Test Customer",
            phone=unique_phone(),
        ),
    )

    db_session.commit()
    db_session.refresh(customer)

    contract = create_pawn_contract_with_assets(
        db_session,
        PawnContractWithAssetsCreate(
            customer_id=customer.id,
            principal_amount=11000000,
            start_date=date(2026, 7, 1),
            assets=[
                {
                    "brand": "Honda",
                    "model_year": 2013,
                    "license_plate": unique_license_plate(),
                }
            ],
        ),
    )
    mark_overdue_contracts(
        db_session,
        as_of_date=date(2026, 8, 2),
    )

    liquidated_contract = liquidate_contract(
        db_session,
        contract.id,
        as_of_date=date(2026, 8, 5),
    )

    assert (
        liquidated_contract.status
        == ContractStatus.LIQUIDATED
    )

    return contract.id

def test_create_pawn_contract_success(
    client: TestClient,
) -> None:
    customer_id = create_customer(client)
    license_plate = unique_license_plate()

    response = client.post(
        "/pawn-contracts/with-assets",
        json={
            "customer_id": customer_id,
            "principal_amount": 11000000,
            "start_date": "2026-08-03",
            "assets": [
                {
                    "brand": "Honda",
                    "model_year": 2013,
                    "license_plate": license_plate,
                }
            ],
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["start_date"] == "2026-08-03"
    assert data["due_date"] == "2026-09-03"
    assert data["customer_id"] == customer_id
    assert data["status"] == "active"

    assert data["contract_code"] == (
        f"TL-20260803-{license_plate}"
    )

def test_create_contract_with_assets_success(
    client: TestClient,
) -> None:
    customer_id = create_customer(client)

    license_plate = unique_license_plate()

    response = client.post(
        "/pawn-contracts/with-assets",
        json={
            "customer_id": customer_id,
            "principal_amount": 11000000,
            "start_date": "2026-08-06",
            "assets": [
                {
                    "brand": "Honda",
                    "model_year": 2013,
                    "license_plate": license_plate,
                }
            ],
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["start_date"] == "2026-08-06"
    assert data["due_date"] == "2026-09-06"

    assert data["customer_id"] == customer_id
    assert len(data["assets"]) == 1

    assert data["assets"][0]["license_plate"] == license_plate

    expected_contract_code = f"TL-20260806-{license_plate}"

    assert data["contract_code"] == expected_contract_code

def test_create_contract_requires_at_least_one_asset(
    client: TestClient,
) -> None:
    customer_id = create_customer(client)

    response = client.post(
        "/pawn-contracts/with-assets",
        json={
            "customer_id": customer_id,
            "principal_amount": 11000000,
            "start_date": "2026-08-06",
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
        "customer_id": customer_id,
        "principal_amount": 11000000,
        "start_date": "2026-08-06",

        "assets": [
            {
                "license_plate": license_plate,
            }
        ],
    }

    second_payload = {
        **first_payload,
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
    client: TestClient,
) -> None:
    response = client.post(
        "/pawn-contracts/with-assets",
        json={
            "customer_id": 999999999,
            "principal_amount": 11000000,
            "start_date": "2026-08-03",
            "assets": [
                {
                    "brand": "Honda",
                    "model_year": 2013,
                    "license_plate": unique_license_plate(),
                }
            ],
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Customer not found.",
    }

def test_create_pawn_contract_rejects_client_supplied_due_date(
    client: TestClient,
) -> None:
    customer_id = create_customer(client)

    response = client.post(
        "/pawn-contracts/with-assets",
        json={
            "customer_id": customer_id,
            "principal_amount": 11000000,
            "start_date": "2026-09-03",
            "due_date": "2026-10-03",
            "assets": [
                {
                    "brand": "Honda",
                    "model_year": 2013,
                    "license_plate": unique_license_plate(),
                }
            ],
        },
    )

    assert response.status_code == 422

    errors = response.json()["detail"]

    assert any(
        "due_date" in error["loc"]
        for error in errors
    )

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

    assert response.status_code == 422

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

def test_overdue_contract_can_be_liquidated(
    db_session,
) -> None:
    customer = create_customer_in_db(
        db_session,
        CustomerCreate(
            name="Overdue Liquidation Customer",
            phone=unique_phone(),
        ),
    )

    db_session.commit()
    db_session.refresh(customer)

    contract = create_pawn_contract_with_assets(
        db_session,
        PawnContractWithAssetsCreate(
            customer_id=customer.id,
            principal_amount=11000000,
            start_date=date(2026, 7, 1),
            assets=[
                {
                    "brand": "Honda",
                    "model_year": 2013,
                    "license_plate": unique_license_plate(),
                }
            ],
        ),
    )
    mark_overdue_contracts(
        db_session,
        as_of_date=date(2026, 8, 2),
    )

    liquidated_contract = liquidate_contract(
        db_session,
        contract.id,
        as_of_date=date(2026, 8, 5),
    )

    assert (
        liquidated_contract.status
        == ContractStatus.LIQUIDATED
    )

def test_overdue_contract_cannot_return_to_active(
    client: TestClient,
    db_session,
) -> None:
    customer = create_customer_in_db(
        db_session,
        CustomerCreate(
            name="Overdue Status Test Customer",
            phone=unique_phone(),
        ),
    )

    db_session.commit()
    db_session.refresh(customer)

    contract = create_pawn_contract_with_assets(
        db_session,
        PawnContractWithAssetsCreate(
            customer_id=customer.id,
            principal_amount=11000000,
            start_date=date(2026, 7, 1),
            assets=[
                {
                    "brand": "Honda",
                    "model_year": 2013,
                    "license_plate": unique_license_plate(),
                }
            ],
        ),
    )
    updated_contracts = mark_overdue_contracts(
        db_session,
        as_of_date=date(2026, 8, 2),
    )

    assert len(updated_contracts) == 1
    assert updated_contracts[0].status == ContractStatus.OVERDUE

    response = client.patch(
        f"/pawn-contracts/{contract.id}",
        json={
            "status": "active",
        },
    )

    assert response.status_code == 422


def test_liquidated_contract_cannot_change_status(
    client: TestClient,
    db_session,
) -> None:
    contract_id = create_liquidated_contract(
        db_session,
    )

    response = client.patch(
        f"/pawn-contracts/{contract_id}",
        json={
            "status": "active",
        },
    )

    assert response.status_code == 422

    contract_response = client.get(
        f"/pawn-contracts/{contract_id}"
    )

    assert contract_response.status_code == 200
    assert (
        contract_response.json()["status"]
        == "liquidated"
    )

def test_redeemed_contract_cannot_change_status(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    redeem_response = client.post(
        f"/pawn-contracts/{contract_id}/redeem",
        json={
            "amount": 11000000,
            "payment_date": "2026-08-22",
        },
    )

    assert redeem_response.status_code == 201

    response = client.patch(
        f"/pawn-contracts/{contract_id}",
        json={
            "status": "overdue",
        },
    )

    assert response.status_code == 422

def test_mark_overdue_contracts_marks_past_due_contract(
    db_session,
) -> None:
    customer = create_customer_in_db(
        db_session,
        CustomerCreate(
            name="Overdue Test Customer",
            phone=unique_phone(),
        ),
    )

    db_session.commit()
    db_session.refresh(customer)

    contract = create_pawn_contract_with_assets(
        db_session,
        PawnContractWithAssetsCreate(
            customer_id=customer.id,
            principal_amount=11000000,
            start_date=date(2026, 7, 1),
            assets=[
                {
                    "brand": "Honda",
                    "model_year": 2013,
                    "license_plate": unique_license_plate(),
                }
            ],
        ),
    )

    updated_contracts = mark_overdue_contracts(
        db_session,
        as_of_date=date(2026, 8, 2),
    )

    assert len(updated_contracts) == 1
    assert updated_contracts[0].id == contract.id
    assert updated_contracts[0].status == ContractStatus.OVERDUE

def test_mark_overdue_contracts_does_not_change_future_contract(
    db_session,
) -> None:
    customer = create_customer_in_db(
        db_session,
        CustomerCreate(
            name="Future Contract Customer",
            phone=unique_phone(),
        ),
    )

    db_session.commit()
    db_session.refresh(customer)

    contract = create_pawn_contract_with_assets(
        db_session,
        PawnContractWithAssetsCreate(
            customer_id=customer.id,
            principal_amount=11000000,
            start_date=date(2026, 7, 10),
            assets=[
                {
                    "brand": "Honda",
                    "model_year": 2013,
                    "license_plate": unique_license_plate(),
                }
            ],
        ),
    )
    updated_contracts = mark_overdue_contracts(
        db_session,
        as_of_date=date(2026, 8, 2),
    )

    assert updated_contracts == []

    db_session.refresh(contract)

    assert contract.status == ContractStatus.ACTIVE

def test_mark_overdue_contracts_does_not_mark_due_today(
    db_session,
) -> None:
    customer = create_customer_in_db(
        db_session,
        CustomerCreate(
            name="Due Today Customer",
            phone=unique_phone(),
        ),
    )

    db_session.commit()
    db_session.refresh(customer)

    contract = create_pawn_contract_with_assets(
        db_session,
        PawnContractWithAssetsCreate(
            customer_id=customer.id,
            principal_amount=11000000,
            start_date=date(2026, 7, 22),
            assets=[
                {
                    "brand": "Honda",
                    "model_year": 2013,
                    "license_plate": unique_license_plate(),
                }
            ],
        ),
    )
    updated_contracts = mark_overdue_contracts(
        db_session,
        as_of_date=date(2026, 8, 22),
    )

    assert updated_contracts == []

    db_session.refresh(contract)

    assert contract.status == ContractStatus.ACTIVE

def test_mark_overdue_contracts_does_not_change_redeemed_contract(
    client: TestClient,
    db_session,
) -> None:
    contract_id = create_contract(client)

    redeem_response = client.post(
        f"/pawn-contracts/{contract_id}/redeem",
        json={
            "amount": 11000000,
            "payment_date": "2026-08-22",
        },
    )

    assert redeem_response.status_code == 201

    updated_contracts = mark_overdue_contracts(
        db_session,
        as_of_date=date(2026, 10, 1),
    )

    assert all(
        contract.id != contract_id
        for contract in updated_contracts
    )

    contract_response = client.get(
        f"/pawn-contracts/{contract_id}"
    )

    assert contract_response.status_code == 200
    assert contract_response.json()["status"] == "redeemed"

def test_mark_overdue_contracts_does_not_change_liquidated_contract(
    client: TestClient,
    db_session,
) -> None:
    contract_id = create_liquidated_contract(
        db_session,
    )

    updated_contracts = mark_overdue_contracts(
        db_session,
        as_of_date=date(2026, 10, 1),
    )

    assert all(
        contract.id != contract_id
        for contract in updated_contracts
    )

    contract_response = client.get(
        f"/pawn-contracts/{contract_id}"
    )

    assert contract_response.status_code == 200
    assert (
        contract_response.json()["status"]
        == "liquidated"
    )

def test_patch_contract_cannot_set_overdue_directly(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    response = client.patch(
        f"/pawn-contracts/{contract_id}",
        json={
            "status": "overdue",
        },
    )

    assert response.status_code == 422

    contract_response = client.get(
        f"/pawn-contracts/{contract_id}"
    )

    assert contract_response.status_code == 200
    assert contract_response.json()["status"] == "active"

def test_refresh_overdue_endpoint_returns_success(
    client: TestClient,
) -> None:
    response = client.post(
        "/pawn-contracts/refresh-overdue",
    )

    assert response.status_code == 200

    data = response.json()

    assert "updated_count" in data
    assert "contract_ids" in data

def test_patch_contract_cannot_set_status_to_liquidated(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    response = client.patch(
        f"/pawn-contracts/{contract_id}",
        json={
            "status": "liquidated",
        },
    )

    assert response.status_code == 422

    contract_response = client.get(
        f"/pawn-contracts/{contract_id}"
    )

    assert contract_response.status_code == 200
    assert contract_response.json()["status"] == "active"

def test_liquidate_endpoint_success(
    client: TestClient,
    db_session,
) -> None:
    customer = create_customer_in_db(
        db_session,
        CustomerCreate(
            name="Liquidation Endpoint Customer",
            phone=unique_phone(),
        ),
    )

    db_session.commit()
    db_session.refresh(customer)

    contract = create_pawn_contract_with_assets(
        db_session,
        PawnContractWithAssetsCreate(
            customer_id=customer.id,
            principal_amount=11000000,
            start_date=date(2026, 7, 1),
            assets=[
                {
                    "brand": "Honda",
                    "model_year": 2013,
                    "license_plate": unique_license_plate(),
                }
            ],
        ),
    )
    mark_overdue_contracts(
        db_session,
        as_of_date=date(2026, 8, 2),
    )

    response = client.post(
        f"/pawn-contracts/{contract.id}/liquidate",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "liquidated"

def test_liquidate_endpoint_rejects_active_contract(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    response = client.post(
        f"/pawn-contracts/{contract_id}/liquidate",
    )

    assert response.status_code == 409

    assert response.json() == {
        "detail": (
            "Only overdue pawn contracts "
            "can be liquidated."
        ),
    }

def test_liquidate_endpoint_rejects_missing_contract(
    client: TestClient,
) -> None:
    response = client.post(
        "/pawn-contracts/999999999/liquidate",
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Pawn contract not found.",
    }

def test_liquidated_contract_cannot_be_redeemed(
    client: TestClient,
    db_session,
) -> None:
    contract_id = create_liquidated_contract(
        db_session,
    )

    response = client.post(
        f"/pawn-contracts/{contract_id}/redeem",
        json={
            "amount": 11000000,
            "payment_date": "2026-09-01",
        },
    )

    assert response.status_code == 409

def test_create_contract_generates_contract_code(
    client: TestClient,
) -> None:
    customer_id = create_customer(client)
    license_plate = unique_license_plate()

    response = client.post(
        "/pawn-contracts/with-assets",
        json={
            "customer_id": customer_id,
            "principal_amount": 11000000,
            "start_date": "2026-09-20",
            "assets": [
                {
                    "brand": "Honda",
                    "model_year": 2013,
                    "license_plate": license_plate,
                }
            ],
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["contract_code"] == (
        f"TL-20260920-{license_plate}"
    )

def test_create_contract_rejects_client_supplied_contract_code(
    client: TestClient,
) -> None:
    customer_id = create_customer(client)
    license_plate = unique_license_plate()

    response = client.post(
        "/pawn-contracts/with-assets",
        json={
            "contract_code": "TL-20240909-1",
            "customer_id": customer_id,
            "principal_amount": 11000000,
            "start_date": "2026-09-20",
            "assets": [
                {
                    "brand": "Honda",
                    "model_year": 2013,
                    "license_plate": license_plate,
                }
            ],
        },
    )

    assert response.status_code == 422

    errors = response.json()["detail"]

    assert any(
        "contract_code" in error["loc"]
        for error in errors
    )

def test_create_contract_with_new_customer_and_assets(
    client: TestClient,
    db_session,
) -> None:
    phone = unique_phone()
    license_plate = unique_license_plate()

    response = client.post(
        "/pawn-contracts/with-customer-and-assets",
        json={
            "customer": {
                "name": "New Test Customer",
                "phone": phone,
            },
            "contract": {
                "principal_amount": 15000000,
                "start_date": "2026-10-21",
            },
            "assets": [
                {
                    "brand": "Honda",
                    "model_year": 2023,
                    "license_plate": license_plate,
                }
            ],
        },
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["customer_id"] is not None
    assert data["start_date"] == "2026-10-21"
    assert data["due_date"] == "2026-11-21"
    assert len(data["assets"]) == 1
    assert data["assets"][0]["license_plate"] == license_plate

    from app.models.customer import Customer

    customer = db_session.get(Customer, data["customer_id"])

    assert customer is not None
    assert customer.name == "New Test Customer"
    assert customer.phone == phone

def test_create_contract_reuses_existing_customer(
    client: TestClient,
) -> None:
    phone = unique_phone()

    customer_response = client.post(
        "/customers",
        json={
            "name": "Existing Test Customer",
            "phone": phone,
        },
    )

    assert customer_response.status_code == 201

    existing_customer_id = customer_response.json()["id"]

    response = client.post(
        "/pawn-contracts/with-customer-and-assets",
        json={
            "customer": {
                "name": "Existing Test Customer",
                "phone": phone,
            },
            "contract": {
                "principal_amount": 15000000,
                "start_date": "2026-10-21",
            },
            "assets": [
                {
                    "brand": "Honda",
                    "model_year": 2023,
                    "license_plate": unique_license_plate(),
                }
            ],
        },
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["customer_id"] == existing_customer_id
    assert len(data["assets"]) == 1

def test_create_contract_with_existing_customer_id(
    client: TestClient,
    db_session,
) -> None:
    # Arrange: Create an existing customer
    phone = unique_phone()
    customer_response = client.post(
        "/customers",
        json={
            "name": "Customer By ID",
            "phone": phone,
        },
    )

    assert customer_response.status_code == 201

    existing_customer_id = customer_response.json()["id"]

    customers_before = db_session.scalar(
        select(func.count()).select_from(Customer)
    )

    # Act: Create a pawn contract using customer_id
    response = client.post(
        "/pawn-contracts/with-customer-and-assets",
        json={
            "customer_id": existing_customer_id,
            "contract": {
                "principal_amount": 15000000,
                "start_date": "2026-10-21",
            },
            "assets": [
                {
                    "brand": "Honda",
                    "model_year": 2023,
                    "license_plate": unique_license_plate(),
                }
            ],
        },
    )

    # Assert: Verify the API response
    assert response.status_code == 201, response.text
    customers_after = db_session.scalar(
        select(func.count()).select_from(Customer)
    )
    assert customers_after == customers_before

    data = response.json()

    assert data["customer_id"] == existing_customer_id
    assert len(data["assets"]) == 1

    # Assert: Verify the existing customer still exists

    customer = db_session.get(Customer, existing_customer_id)

    assert customer is not None
    assert customer.name == "Customer By ID"
    assert customer.phone == phone

def test_create_contract_with_nonexistent_customer_id(
    client: TestClient,
) -> None:
    # Arrange: Prepare a customer ID that does not exist
    nonexistent_customer_id = 999999999

    # Act: Attempt to create a contract
    response = client.post(
        "/pawn-contracts/with-customer-and-assets",
        json={
            "customer_id": nonexistent_customer_id,
            "contract": {
                "principal_amount": 15000000,
                "start_date": "2026-10-21",
            },
            "assets": [
                {
                    "brand": "Honda",
                    "model_year": 2023,
                    "license_plate": unique_license_plate(),
                }
            ],
        },
    )

    # Assert: Customer does not exist
    assert response.status_code == 404, response.text

def test_create_contract_rejects_both_customer_id_and_customer(
    client: TestClient,
) -> None:
    response = client.post(
        "/pawn-contracts/with-customer-and-assets",
        json={
            "customer_id": 1,
            "customer": {
                "name": "Invalid Customer",
                "phone": unique_phone(),
            },
            "contract": {
                "principal_amount": 15000000,
                "start_date": "2026-10-21",
            },
            "assets": [
                {
                    "brand": "Honda",
                    "model_year": 2023,
                    "license_plate": unique_license_plate(),
                }
            ],
        },
    )

    assert response.status_code == 422, response.text

def test_create_contract_rejects_missing_customer_selection(
    client: TestClient,
) -> None:
    # Arrange & Act: Send a request without customer_id or customer
    response = client.post(
        "/pawn-contracts/with-customer-and-assets",
        json={
            "contract": {
                "principal_amount": 15000000,
                "start_date": "2026-10-21",
            },
            "assets": [
                {
                    "brand": "Honda",
                    "model_year": 2023,
                    "license_plate": unique_license_plate(),
                }
            ],
        },
    )

    # Assert: Request validation must fail
    assert response.status_code == 422, response.text

@pytest.mark.parametrize("customer_id", [-1, 0])
def test_create_contract_rejects_invalid_customer_id(
    client: TestClient,
    customer_id: int,
) -> None:
    # Arrange & Act
    response = client.post(
        "/pawn-contracts/with-customer-and-assets",
        json={
            "customer_id": customer_id,
            "contract": {
                "principal_amount": 15000000,
                "start_date": "2026-10-21",
            },
            "assets": [
                {
                    "brand": "Honda",
                    "model_year": 2023,
                    "license_plate": unique_license_plate(),
                }
            ],
        },
    )

    # Assert
    assert response.status_code == 422, response.text

    errors = response.json()["detail"]

    assert any(
        error["loc"] == ["body", "customer_id"]
        for error in errors
    )

def test_create_contract_rejects_customer_information_conflict(
    client: TestClient,
    db_session,
) -> None:
    phone = unique_phone()

    customer_response = client.post(
        "/customers",
        json={
            "name": "Nguyen Van A",
            "phone": phone,
        },
    )

    assert customer_response.status_code == 201

    response = client.post(
        "/pawn-contracts/with-customer-and-assets",
        json={
            "customer": {
                "name": "Nguyen Van B",
                "phone": phone,
            },
            "contract": {
                "principal_amount": 15000000,
                "start_date": "2026-10-21",
            },
            "assets": [
                {
                    "brand": "Honda",
                    "model_year": 2023,
                    "license_plate": unique_license_plate(),
                }
            ],
        },
    )

    assert response.status_code == 409, response.text

    contract_count = db_session.scalar(
        select(func.count()).select_from(PawnContract)
    )

    asset_count = db_session.scalar(
        select(func.count()).select_from(PawnAsset)
    )

    assert contract_count == 0
    assert asset_count == 0

def test_create_contract_with_customer_rejects_pawned_license_plate(
    client: TestClient,
    db_session,
) -> None:
    phone = unique_phone()
    license_plate = unique_license_plate()

    payload = {
        "customer": {
            "name": "License Plate Test Customer",
            "phone": phone,
        },
        "contract": {
            "principal_amount": 15000000,
            "start_date": "2026-10-21",
        },
        "assets": [
            {
                "brand": "Honda",
                "model_year": 2023,
                "license_plate": license_plate,
            }
        ],
    }

    first_response = client.post(
        "/pawn-contracts/with-customer-and-assets",
        json=payload,
    )

    assert first_response.status_code == 201, first_response.text

    second_response = client.post(
        "/pawn-contracts/with-customer-and-assets",
        json=payload,
    )

    assert second_response.status_code == 409, second_response.text

    contract_count = db_session.scalar(
        select(func.count()).select_from(PawnContract)
    )

    asset_count = db_session.scalar(
        select(func.count()).select_from(PawnAsset)
    )

    assert contract_count == 1
    assert asset_count == 1

def test_get_pawn_contract_details_success(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)
    response = client.get(
        f"/pawn-contracts/{contract_id}/details"
    )
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {
        "contract",
        "customer",
        "assets",
        "payments",
        "payment_summary",
    }
    assert data["contract"]["id"] == contract_id
    assert (
        data["customer"]["id"]
        == data["contract"]["customer_id"]
    )
    assert len(data["assets"]) == 1
    assert data["assets"][0]["contract_id"] == contract_id
    assert data["assets"][0]["brand"] == "Honda"
    assert data["assets"][0]["model_year"] == 2013
    assert data["assets"][0]["license_plate"].startswith("TEST-")
    assert data["payments"] == []
    assert (
        data["payment_summary"]["contract_id"]
        == contract_id
    )
    assert (
        data["payment_summary"]["outstanding_principal"]
        == "11000000"
    )

def test_get_pawn_contract_details_not_found(
    client: TestClient,
) -> None:
    response = client.get(
        "/pawn-contracts/999999/details"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Pawn contract not found"
    }

def test_get_pawn_contract_details_invalid_id(
    client: TestClient,
) -> None:
    response = client.get(
        "/pawn-contracts/abc/details"
    )

    assert response.status_code == 422

    data = response.json()

    assert "detail" in data

def test_get_pawn_contract_details_with_payments(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    interest_response = client.post(
        "/payments",
        json={
            "contract_id": contract_id,
            "amount": 550000,
            "payment_type": "interest",
            "payment_date": "2026-08-23",
        },
    )

    assert interest_response.status_code == 201

    principal_response = client.post(
        "/payments",
        json={
            "contract_id": contract_id,
            "amount": 2000000,
            "payment_type": "principal",
            "payment_date": "2026-08-24",
        },
    )

    assert principal_response.status_code == 201

    response = client.get(
        f"/pawn-contracts/{contract_id}/details"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["payments"]) == 2

    payment_types = {
        payment["payment_type"]
        for payment in data["payments"]
    }

    assert payment_types == {"interest", "principal"}

    summary = data["payment_summary"]

    assert summary["principal_amount"] == "11000000"
    assert summary["total_interest_paid"] == "550000"
    assert summary["total_principal_paid"] == "2000000"
    assert summary["total_redemption_paid"] == "0"
    assert summary["outstanding_principal"] == "9000000"


def test_patch_contract_recalculates_interest_due_date_and_preserves_contract_code(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)
    before_response = client.get(
        f"/pawn-contracts/{contract_id}"
    )

    assert before_response.status_code == 200

    original_contract_code = before_response.json()["contract_code"]



    response = client.patch(
        f"/pawn-contracts/{contract_id}",
        json={
            "principal_amount": 12000000,
            "start_date": "2026-10-15",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert int(data["principal_amount"]) == 12000000
    assert int(data["monthly_interest_amount"]) == 600000

    assert data["start_date"] == "2026-10-15"
    assert data["due_date"] == "2026-11-15"

    assert data["contract_code"] == original_contract_code

    get_response = client.get(
        f"/pawn-contracts/{contract_id}"
    )

    assert get_response.status_code == 200

    saved_contract = get_response.json()

    assert int(saved_contract["principal_amount"]) == 12000000
    assert int(saved_contract["monthly_interest_amount"]) == 600000

    assert saved_contract["start_date"] == "2026-10-15"
    assert saved_contract["due_date"] == "2026-11-15"

    assert saved_contract["contract_code"] == original_contract_code
def test_patch_contract_rejects_contract_with_existing_payment(
    client: TestClient,
) -> None:
    # Arrange: Create a contract
    contract_id = create_contract(client)

    # Arrange: Record an interest payment
    payment_response = client.post(
        "/payments",
        json={
            "contract_id": contract_id,
            "amount": 550000,
            "payment_type": "interest",
            "payment_date": "2026-08-23",
        },
    )

    assert payment_response.status_code == 201

    # Act: Attempt to modify the contract
    patch_response = client.patch(
        f"/pawn-contracts/{contract_id}",
        json={
            "principal_amount": 12000000,
        },
    )

    # Assert: Editing must be rejected
    assert patch_response.status_code == 409, patch_response.json()

    # Assert: The original principal must remain unchanged
    get_response = client.get(
        f"/pawn-contracts/{contract_id}"
    )

    assert get_response.status_code == 200

    saved_contract = get_response.json()

    assert int(saved_contract["principal_amount"]) == 11000000
    assert int(saved_contract["monthly_interest_amount"]) == 550000


def test_patch_contract_rejects_nonexistent_customer(
    client: TestClient,
) -> None:
    # Arrange: Create a valid contract
    contract_id = create_contract(client)

    # Arrange: Read the original customer ID
    get_response = client.get(
        f"/pawn-contracts/{contract_id}"
    )

    assert get_response.status_code == 200

    original_customer_id = get_response.json()["customer_id"]

    # Act: Attempt to assign a nonexistent customer
    patch_response = client.patch(
        f"/pawn-contracts/{contract_id}",
        json={
            "customer_id": 999999999,
        },
    )

    # Assert: Customer must exist
    assert patch_response.status_code == 404, patch_response.json()

    # Assert: Original customer must remain unchanged
    get_response = client.get(
        f"/pawn-contracts/{contract_id}"
    )

    assert get_response.status_code == 200

    saved_contract = get_response.json()

    assert saved_contract["customer_id"] == original_customer_id

def test_patch_contract_rejects_nonexistent_contract(
    client: TestClient,
) -> None:
    # Act: Attempt to update a nonexistent contract
    response = client.patch(
        "/pawn-contracts/999999999",
        json={
            "principal_amount": 12000000,
        },
    )

    # Assert: Contract must exist
    assert response.status_code == 404, response.json()

    assert response.json()["detail"] == "Pawn contract not found."

def test_patch_contract_rejects_empty_request(
    client: TestClient,
) -> None:
    # Arrange: Create an existing contract
    contract_id = create_contract(client)

    # Act: Send an empty PATCH request
    response = client.patch(
        f"/pawn-contracts/{contract_id}",
        json={},
    )

    # Assert: Empty updates are not allowed
    assert response.status_code == 422, response.json()

    # Assert: The error comes from request validation
    errors = response.json()["detail"]

    assert any(
        error["type"] == "value_error"
        for error in errors
    )

@pytest.mark.parametrize(
    "invalid_principal",
    [
        0,
        -1000000,
    ],
)
def test_patch_contract_rejects_nonpositive_principal(
    client: TestClient,
    invalid_principal: int,
) -> None:
    # Arrange
    contract_id = create_contract(client)

    # Act
    response = client.patch(
        f"/pawn-contracts/{contract_id}",
        json={
            "principal_amount": invalid_principal,
        },
    )

    # Assert
    assert response.status_code == 422, response.json()

    errors = response.json()["detail"]

    assert any(
        error["type"] == "greater_than"
        for error in errors
    )

@pytest.mark.parametrize(
    "field_name",
    [
        "customer_id",
        "principal_amount",
        "start_date",
    ],
)
def test_patch_contract_rejects_explicit_null(
    client: TestClient,
    field_name: str,
) -> None:
    # Arrange
    contract_id = create_contract(client)

    # Act
    response = client.patch(
        f"/pawn-contracts/{contract_id}",
        json={
            field_name: None,
        },
    )

    # Assert
    assert response.status_code == 422, response.json()

    errors = response.json()["detail"]

    assert any(
        error["type"] == "value_error"
        for error in errors
    )

def test_create_contract_rejects_multiple_assets(
    client: TestClient,
) -> None:
    customer_id = create_customer(client)

    response = client.post(
        "/pawn-contracts/with-assets",
        json={
            "customer_id": customer_id,
            "principal_amount": 11000000,
            "start_date": "2026-08-06",
            "assets": [
                {
                    "brand": "Honda",
                    "model_year": 2013,
                    "license_plate": unique_license_plate(),
                },
                {
                    "brand": "Yamaha",
                    "model_year": 2018,
                    "license_plate": unique_license_plate(),
                },
            ],
        },
    )

    assert response.status_code == 422

def test_create_contract_rejects_missing_license_plate(
    client: TestClient,
) -> None:
    customer_id = create_customer(client)

    response = client.post(
        "/pawn-contracts/with-assets",
        json={
            "customer_id": customer_id,
            "principal_amount": 11000000,
            "start_date": "2026-08-06",
            "assets": [
                {
                    "brand": "Honda",
                    "model_year": 2013,
                }
            ],
        },
    )

    assert response.status_code == 422

@pytest.mark.parametrize(
    "license_plate",
    [None, "", "   "],
)
def test_create_contract_rejects_invalid_license_plate(
    client: TestClient,
    license_plate: str | None,
) -> None:
    customer_id = create_customer(client)

    response = client.post(
        "/pawn-contracts/with-assets",
        json={
            "customer_id": customer_id,
            "principal_amount": 11000000,
            "start_date": "2026-08-06",
            "assets": [
                {
                    "brand": "Honda",
                    "model_year": 2013,
                    "license_plate": license_plate,
                }
            ],
        },
    )

    assert response.status_code == 422

def test_create_contract_with_customer_and_assets_generates_code_from_license_plate(
    client: TestClient,
) -> None:
    customer_id = create_customer(client)

    license_plate = unique_license_plate()

    response = client.post(
        "/pawn-contracts/with-customer-and-assets",
        json={
            "customer_id": customer_id,
            "contract": {
                "principal_amount": 11000000,
                "start_date": "2026-08-06",
            },
            "assets": [
                {
                    "brand": "Honda",
                    "model_year": 2013,
                    "license_plate": license_plate,
                }
            ],
        },
    )

    assert response.status_code == 201

    data = response.json()

    expected_contract_code = f"TL-20260806-{license_plate}"

    assert data["contract_code"] == expected_contract_code

def test_create_with_customer_and_assets_rejects_multiple_assets(
    client: TestClient,
) -> None:
    customer_id = create_customer(client)

    response = client.post(
        "/pawn-contracts/with-customer-and-assets",
        json={
            "customer_id": customer_id,
            "contract": {
                "principal_amount": 11000000,
                "start_date": "2026-08-06",
            },
            "assets": [
                {
                    "brand": "Honda",
                    "license_plate": unique_license_plate(),
                },
                {
                    "brand": "Yamaha",
                    "license_plate": unique_license_plate(),
                },
            ],
        },
    )

    assert response.status_code == 422

def test_create_with_customer_and_assets_rejects_missing_license_plate(
    client: TestClient,
) -> None:
    customer_id = create_customer(client)

    response = client.post(
        "/pawn-contracts/with-customer-and-assets",
        json={
            "customer_id": customer_id,
            "contract": {
                "principal_amount": 11000000,
                "start_date": "2026-08-06",
            },
            "assets": [
                {
                    "brand": "Honda",
                    "model_year": 2013,
                }
            ],
        },
    )

    assert response.status_code == 422

@pytest.mark.parametrize(
    "license_plate",
    [None, "", "   "],
)
def test_create_with_customer_and_assets_rejects_invalid_license_plate(
    client: TestClient,
    license_plate: str | None,
) -> None:
    customer_id = create_customer(client)

    response = client.post(
        "/pawn-contracts/with-customer-and-assets",
        json={
            "customer_id": customer_id,
            "contract": {
                "principal_amount": 11000000,
                "start_date": "2026-08-06",
            },
            "assets": [
                {
                    "brand": "Honda",
                    "model_year": 2013,
                    "license_plate": license_plate,
                }
            ],
        },
    )

    assert response.status_code == 422

def test_legacy_create_without_assets_is_rejected(
    client: TestClient,
) -> None:
    customer_id = create_customer(client)

    response = client.post(
        "/pawn-contracts",
        json={
            "customer_id": customer_id,
            "principal_amount": 11000000,
            "start_date": "2026-08-22",
        },
    )

    assert response.status_code == 422
