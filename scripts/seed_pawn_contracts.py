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


CUSTOMER_PHONE = "0328888718"
CONTRACT_CODE = "M-2026-001"


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
                    principal_amount=Decimal("11000000"),
                    monthly_interest_amount=Decimal("0"),
                    start_date=date(2023, 12, 17),
                    due_date=date(2024, 1, 17),
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
