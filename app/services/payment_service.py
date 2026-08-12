from sqlalchemy.orm import Session

from app.models.pawn_contract import ContractStatus
from app.models.payment import Payment
from app.repositories.pawn_contract_repository import (
    get_contract_by_id,
)
from app.repositories.payment_repository import (
    create_payment,
    get_payment_by_id,
    list_payments_by_contract,
)
from app.schemas.payment import PaymentCreate


class PaymentNotFoundError(Exception):
    pass


class PaymentContractNotFoundError(Exception):
    pass


class PaymentContractClosedError(Exception):
    pass


def get_payment(
    db: Session,
    payment_id: int,
) -> Payment:
    payment = get_payment_by_id(
        db,
        payment_id,
    )

    if payment is None:
        raise PaymentNotFoundError

    return payment


def get_contract_payments(
    db: Session,
    contract_id: int,
) -> list[Payment]:
    contract = get_contract_by_id(
        db,
        contract_id,
    )

    if contract is None:
        raise PaymentContractNotFoundError

    return list_payments_by_contract(
        db,
        contract_id,
    )


def create_new_payment(
    db: Session,
    payment_data: PaymentCreate,
) -> Payment:
    contract = get_contract_by_id(
        db,
        payment_data.contract_id,
    )

    if contract is None:
        raise PaymentContractNotFoundError

    if contract.status in {
        ContractStatus.REDEEMED,
        ContractStatus.LIQUIDATED,
    }:
        raise PaymentContractClosedError

    try:
        payment = create_payment(
            db,
            payment_data,
        )

        db.commit()
        db.refresh(payment)

        return payment

    except Exception:
        db.rollback()
        raise
