from uuid import uuid4

from fastapi.testclient import TestClient

from datetime import date

from app.models.pawn_contract import ContractStatus


from app.schemas.pawn_contract import PawnContractCreate
from app.services.pawn_contract_service import (
    create_new_pawn_contract,
    mark_overdue_contracts,
    liquidate_contract,
)

from app.repositories.customer_repository import (
    create_customer as create_customer_in_db,
)

from app.schemas.customer import CustomerCreate
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

    contract = create_new_pawn_contract(
        db_session,
        PawnContractCreate(
            contract_code=unique_contract_code(),
            customer_id=customer.id,
            principal_amount=11000000,
            monthly_interest_amount=550000,
            start_date=date(2026, 7, 1),
            due_date=date(2026, 8, 1),
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

#def test_active_contract_can_be_marked_overdue(
#    client: TestClient,
#) -> None:
#    contract_id = create_contract(client)
#    response = client.patch(
#        f"/pawn-contracts/{contract_id}",
#        json={
#            "status": "overdue",
#        },
#    )
#    assert response.status_code == 200
#    assert response.json()["status"] == "overdue"

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

    contract = create_new_pawn_contract(
        db_session,
        PawnContractCreate(
            contract_code=unique_contract_code(),
            customer_id=customer.id,
            principal_amount=11000000,
            monthly_interest_amount=550000,
            start_date=date(2026, 7, 1),
            due_date=date(2026, 8, 1),
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

    contract = create_new_pawn_contract(
        db_session,
        PawnContractCreate(
            contract_code=unique_contract_code(),
            customer_id=customer.id,
            principal_amount=11000000,
            monthly_interest_amount=550000,
            start_date=date(2026, 7, 1),
            due_date=date(2026, 8, 1),
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

    assert response.status_code == 409

    assert response.json() == {
        "detail": "Pawn contract status transition is not allowed.",
    }

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

    assert response.status_code == 409

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

    assert response.status_code == 409

#def test_calculate_days_overdue_after_due_date() -> None:
#    due_date = date(2026,8,20)
#    as_of_date = date(2026,8,27)
#    result = calculate_days_overdue(
#        due_date,
#        as_of_date,
#    )
#    assert result == 7

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

    contract = create_new_pawn_contract(
        db_session,
        PawnContractCreate(
            contract_code=unique_contract_code(),
            customer_id=customer.id,
            principal_amount=11000000,
            monthly_interest_amount=550000,
            start_date=date(2026, 7, 1),
            due_date=date(2026, 8, 1),
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

    contract = create_new_pawn_contract(
        db_session,
        PawnContractCreate(
            contract_code=unique_contract_code(),
            customer_id=customer.id,
            principal_amount=11000000,
            monthly_interest_amount=550000,
            start_date=date(2026, 7, 1),
            due_date=date(2026, 8, 10),
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

    contract = create_new_pawn_contract(
        db_session,
        PawnContractCreate(
            contract_code=unique_contract_code(),
            customer_id=customer.id,
            principal_amount=11000000,
            monthly_interest_amount=550000,
            start_date=date(2026, 7, 22),
            due_date=date(2026, 8, 22),
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

    assert response.status_code == 409

    contract_response = client.get(
        f"/pawn-contracts/{contract_id}"
    )

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

    assert response.status_code == 409

    assert response.json() == {
        "detail": (
            "Pawn contract must be liquidated through "
            "the liquidation endpoint."
        ),
    }

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

    contract = create_new_pawn_contract(
        db_session,
        PawnContractCreate(
            contract_code=unique_contract_code(),
            customer_id=customer.id,
            principal_amount=11000000,
            monthly_interest_amount=550000,
            start_date=date(2026, 7, 1),
            due_date=date(2026, 8, 1),
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

def test_active_contract_can_update_due_date(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    response = client.patch(
        f"/pawn-contracts/{contract_id}",
        json={
            "due_date": "2026-10-22",
        },
    )

    assert response.status_code == 200

    assert response.json()["due_date"] == "2026-10-22"

def test_active_contract_can_update_monthly_interest_amount(
    client: TestClient,
) -> None:
    contract_id = create_contract(client)

    response = client.patch(
        f"/pawn-contracts/{contract_id}",
        json={
            "monthly_interest_amount": 600000,
        },
    )

    assert response.status_code == 200

    assert response.json()["monthly_interest_amount"] == "600000"

def test_overdue_contract_cannot_update_due_date(
    client: TestClient,
    db_session,
) -> None:
    customer = create_customer_in_db(
        db_session,
        CustomerCreate(
            name="Overdue Update Customer",
            phone=unique_phone(),
        ),
    )

    db_session.commit()
    db_session.refresh(customer)

    contract = create_new_pawn_contract(
        db_session,
        PawnContractCreate(
            contract_code=unique_contract_code(),
            customer_id=customer.id,
            principal_amount=11000000,
            monthly_interest_amount=550000,
            start_date=date(2026, 7, 1),
            due_date=date(2026, 8, 1),
        ),
    )

    assert contract.status == ContractStatus.ACTIVE

    mark_overdue_contracts(
        db_session,
        as_of_date=date(2026, 8, 2),
    )

    db_session.refresh(contract)

    assert contract.status == ContractStatus.OVERDUE

    response = client.patch(
        f"/pawn-contracts/{contract.id}",
        json={
            "due_date": "2026-12-01",
        },
    )

    assert response.status_code == 409

    assert response.json() == {
        "detail": (
            "Pawn contract can only be edited "
            "while it is active."
        ),
    }

    contract_response = client.get(
        f"/pawn-contracts/{contract.id}",
    )

    assert contract_response.status_code == 200
    assert contract_response.json()["due_date"] == "2026-08-01"

def test_overdue_contract_cannot_update_monthly_interest_amount(
    client: TestClient,
    db_session,
) -> None:
    customer = create_customer_in_db(
        db_session,
        CustomerCreate(
            name="Overdue Interest Update Customer",
            phone=unique_phone(),
        ),
    )

    db_session.commit()
    db_session.refresh(customer)

    contract = create_new_pawn_contract(
        db_session,
        PawnContractCreate(
            contract_code=unique_contract_code(),
            customer_id=customer.id,
            principal_amount=11000000,
            monthly_interest_amount=550000,
            start_date=date(2026, 7, 1),
            due_date=date(2026, 8, 1),
        ),
    )

    mark_overdue_contracts(
        db_session,
        as_of_date=date(2026, 8, 2),
    )

    db_session.refresh(contract)

    assert contract.status == ContractStatus.OVERDUE

    response = client.patch(
        f"/pawn-contracts/{contract.id}",
        json={
            "monthly_interest_amount": 999999,
        },
    )

    assert response.status_code == 409

    assert response.json() == {
        "detail": (
            "Pawn contract can only be edited "
            "while it is active."
        ),
    }

    contract_response = client.get(
        f"/pawn-contracts/{contract.id}",
    )

    assert contract_response.status_code == 200

def test_redeemed_contract_cannot_update_due_date(
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

    contract_response = client.get(
        f"/pawn-contracts/{contract_id}",
    )

    assert contract_response.status_code == 200
    assert contract_response.json()["status"] == "redeemed"

    response = client.patch(
        f"/pawn-contracts/{contract_id}",
        json={
            "due_date": "2027-01-01",
        },
    )

    assert response.status_code == 409

    assert response.json() == {
        "detail": (
            "Pawn contract can only be edited "
            "while it is active."
        ),
    }

    contract_response = client.get(
        f"/pawn-contracts/{contract_id}",
    )

    assert contract_response.status_code == 200
    assert contract_response.json()["due_date"] == "2026-09-22"

def test_liquidated_contract_cannot_update_due_date(
    client: TestClient,
    db_session,
) -> None:
    contract_id = create_liquidated_contract(
        db_session,
    )

    response = client.patch(
        f"/pawn-contracts/{contract_id}",
        json={
            "due_date": "2027-01-01",
        },
    )

    assert response.status_code == 409

    assert response.json() == {
        "detail": (
            "Pawn contract can only be edited "
            "while it is active."
        ),
    }

    contract_response = client.get(
        f"/pawn-contracts/{contract_id}",
    )

    assert contract_response.status_code == 200
    assert contract_response.json()["status"] == "liquidated"
    assert contract_response.json()["due_date"] == "2026-08-01"
