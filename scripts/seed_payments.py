from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.payment import PaymentType
from app.repositories.pawn_contract_repository import get_contract_by_code
from app.schemas.payment import (
    PaymentCreate,
    RedemptionCreate,
)
from app.services.payment_service import (
    PaymentContractClosedError,
    PaymentContractNotFoundError,
    RedemptionAmountMismatchError,
    create_new_payment,
    redeem_contract,
)


CONTRACT_CODE = "M-2026-002"


def seed_payments(
    db: Session,
) -> None:
    contract = get_contract_by_code(
        db,
        CONTRACT_CODE,
    )

    if contract is None:
        print(
            "Pawn contract does not exist:",
            CONTRACT_CODE,
        )
        return

    payments_data = [
        PaymentCreate(
            contract_id=contract.id,
            amount=Decimal("500000"),
            payment_type=PaymentType.INTEREST,
            payment_date=date(2026, 8, 10),
            note="Interest payment 1",
        ),
        PaymentCreate(
            contract_id=contract.id,
            amount=Decimal("500000"),
            payment_type=PaymentType.INTEREST,
            payment_date=date(2026, 8, 17),
            note="Interest payment 2",
        ),
        PaymentCreate(
            contract_id=contract.id,
            amount=Decimal("2000000"),
            payment_type=PaymentType.PRINCIPAL,
            payment_date=date(2026, 8, 20),
            note="Partial principal payment",
        ),
        PaymentCreate(
            contract_id=contract.id,
            amount=Decimal("1000000"),
            payment_type=PaymentType.PRINCIPAL,
            payment_date=date(2026, 8, 25),
            note="Second principal payment",
        ),
    ]

    for payment_data in payments_data:
        try:
            payment = create_new_payment(
                db,
                payment_data,
            )

            print(
                "Created payment:",
                payment.id,
                payment.payment_type.value,
                payment.amount,
            )

        except PaymentContractClosedError:
            print(
                "Pawn contract is closed:",
                CONTRACT_CODE,
            )
            return

        except PaymentContractNotFoundError:
            print(
                "Pawn contract does not exist:",
                CONTRACT_CODE,
            )
            return

    outstanding_principal = Decimal("7000000")

    redemption_data = RedemptionCreate(
        amount=outstanding_principal,
        payment_date=date(2026, 8, 30),
        note="Customer redeemed pawned asset",
    )

    try:
        redemption = redeem_contract(
            db,
            contract.id,
            redemption_data,
        )

        print(
            "Created redemption payment:",
            redemption.payment.id,
            redemption.payment.amount,
        )

        print(
            "Contract redeemed:",
            redemption.contract_id,
        )

    except RedemptionAmountMismatchError:
        print(
            "Redemption amount does not match outstanding principal."
        )

    except PaymentContractClosedError:
        print(
            "Pawn contract cannot be redeemed:",
            CONTRACT_CODE,
        )

    except PaymentContractNotFoundError:
        print(
            "Pawn contract does not exist:",
            CONTRACT_CODE,
        )


def main() -> None:
    db = SessionLocal()

    try:
        seed_payments(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
