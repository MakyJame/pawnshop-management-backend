from datetime import date
from decimal import Decimal

from app.db.session import SessionLocal
from app.repositories.customer_repository import get_customer_by_phone
from app.schemas.pawn_contract import PawnContractCreate
from app.services.pawn_contract_service import (
    PawnContractCodeAlreadyExistsError,
    PawnContractCustomerNotFoundError,
    create_new_pawn_contract,
)


CUSTOMER_PHONE = "0789606001"
CONTRACT_CODE = "M-2026-003"


def seed_pawn_contracts() -> None:
    db = SessionLocal()

    try:
        customer = get_customer_by_phone(
            db,
            CUSTOMER_PHONE,
        )

        if customer is None:
            print(
                "Customer does not exist. "
                "Run seed_customers first."
            )
            return

        try:
            contract = create_new_pawn_contract(
                db,
                PawnContractCreate(
                    contract_code=CONTRACT_CODE,
                    customer_id=customer.id,
                    principal_amount=Decimal("5000000"),
                    monthly_interest_amount=Decimal("0"),
                    start_date=date(2026, 8, 4),
                    due_date=date(2026, 9, 4),
                ),
            )

            print(
                "Created pawn contract:",
                contract.id,
                contract.contract_code,
            )

        except PawnContractCodeAlreadyExistsError:
            print(
                "Pawn contract already exists:",
                CONTRACT_CODE,
            )

        except PawnContractCustomerNotFoundError:
            print(
                "Customer does not exist:",
                CUSTOMER_PHONE,
            )

    finally:
        db.close()


if __name__ == "__main__":
    seed_pawn_contracts()
