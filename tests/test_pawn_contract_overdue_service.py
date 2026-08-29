from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.pawn_contract import ContractStatus, PawnContract
from app.repositories.customer_repository import (
    create_customer as create_customer_in_db,
)
from app.schemas.customer import CustomerCreate
from app.services.pawn_contract_service import mark_overdue_contracts

def test_overdue_contract_is_marked_overdue(
    db_session: Session,
) -> None:
    customer = create_customer_in_db(
        db_session,
        CustomerCreate(
            name="Overdue Test Customer",
            phone="0900000999",
        ),
    )

    db_session.commit()
    db_session.refresh(customer)

    contract = PawnContract(
        contract_code="TEST-OVERDUE-001",
        customer_id=customer.id,
        principal_amount=Decimal("11000000"),
        monthly_interest_amount=Decimal("550000"),
        start_date=date(2026, 7, 1),
        due_date=date(2026, 8, 1),
        status=ContractStatus.ACTIVE,
    )

    db_session.add(contract)
    db_session.commit()
    db_session.refresh(contract)

    updated_contracts = mark_overdue_contracts(
        db_session,
        as_of_date=date(2026, 8, 2),
    )

    assert len(updated_contracts) == 1
    assert updated_contracts[0].id == contract.id
    assert updated_contracts[0].status == ContractStatus.OVERDUE
