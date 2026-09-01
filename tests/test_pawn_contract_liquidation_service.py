import pytest

from datetime import date
from uuid import uuid4

from app.models.pawn_contract import ContractStatus
from app.repositories.customer_repository import (
    create_customer as create_customer_in_db,
)
from app.schemas.customer import CustomerCreate
from app.schemas.pawn_contract import PawnContractCreate
from app.services.pawn_contract_service import (
    LiquidationContractNotOverdueError,
    LiquidationGracePeriodNotExpiredError,
    create_new_pawn_contract,
    liquidate_contract,
    mark_overdue_contracts,
)
def unique_phone() -> str:
    return f"09{str(uuid4().int)[-8:]}"
def unique_contract_code() -> str:
    return f"HD-{str(uuid4())[:8]}"

def create_active_contract(
    db_session,
    *,
    due_date: date,
):
    customer = create_customer_in_db(
        db_session,
        CustomerCreate(
            name="Liquidation Test Customer",
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
            due_date=due_date,
        ),
    )

    return contract

def create_overdue_contract(
    db_session,
):
    contract = create_active_contract(
        db_session,
        due_date=date(2026, 8, 1),
    )

    updated_contracts = mark_overdue_contracts(
        db_session,
        as_of_date=date(2026, 8, 2),
    )

    assert len(updated_contracts) == 1
    assert contract.status == ContractStatus.OVERDUE

    return contract

def test_active_contract_cannot_be_liquidated(
    db_session,
) -> None:
    contract = create_active_contract(
        db_session,
        due_date=date(2026, 8, 1),
    )

    assert contract.status == ContractStatus.ACTIVE

    with pytest.raises(
        LiquidationContractNotOverdueError
    ):
        liquidate_contract(
            db_session,
            contract.id,
            as_of_date=date(2026, 8, 20),
        )

    db_session.refresh(contract)

    assert contract.status == ContractStatus.ACTIVE

def test_overdue_contract_cannot_be_liquidated_during_grace_period(
    db_session,
) -> None:
    contract = create_overdue_contract(
        db_session,
    )

    with pytest.raises(
        LiquidationGracePeriodNotExpiredError
    ):
        liquidate_contract(
            db_session,
            contract.id,
            as_of_date=date(2026, 8, 3),
        )

    db_session.refresh(contract)

    assert contract.status == ContractStatus.OVERDUE

def test_overdue_contract_cannot_be_liquidated_on_grace_period_end(
    db_session,
) -> None:
    contract = create_overdue_contract(
        db_session,
    )

    with pytest.raises(
        LiquidationGracePeriodNotExpiredError
    ):
        liquidate_contract(
            db_session,
            contract.id,
            as_of_date=date(2026, 8, 4),
        )

    db_session.refresh(contract)

    assert contract.status == ContractStatus.OVERDUE

def test_overdue_contract_can_be_liquidated_after_grace_period(
    db_session,
) -> None:
    contract = create_overdue_contract(
        db_session,
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

    db_session.refresh(contract)

    assert (
        contract.status
        == ContractStatus.LIQUIDATED
    )
