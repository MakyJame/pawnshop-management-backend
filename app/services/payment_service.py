from sqlalchemy.orm import Session

from app.models.pawn_contract import ContractStatus
from app.models.payment import Payment, PaymentType
from app.repositories.pawn_contract_repository import (
    get_contract_by_id,
)
from app.repositories.payment_repository import (
    create_payment,
    get_payment_by_id,
    list_payments_by_contract,
    get_total_paid_by_type,
)
from app.schemas.payment import PaymentCreate, PaymentSummary

from decimal import Decimal

class PaymentNotFoundError(Exception):
    pass


class PaymentContractNotFoundError(Exception):
    pass


class PaymentContractClosedError(Exception):
    pass

class PrincipalPaymentExceedsOutstandingError(Exception):
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
    if payment_data.payment_type == PaymentType.PRINCIPAL:
        total_principal_paid = get_total_paid_by_type(
                db,
                contract.id,
                PaymentType.PRINCIPAL,
        )
        outstanding_principal = contract.principal_amount - total_principal_paid
        if payment_data.amount > outstanding_principal: 
            raise PrincipalPaymentExceedsOutstandingError
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

def get_payment_summary(
    db: Session,
    contract_id: int,
) -> PaymentSummary:
    contract = get_contract_by_id(
        db,
        contract_id,
    )

    if contract is None:
        raise PaymentContractNotFoundError

    total_interest_paid = get_total_paid_by_type(
        db,
        contract_id,
        PaymentType.INTEREST,
    )

    total_principal_paid = get_total_paid_by_type(
        db,
        contract_id,
        PaymentType.PRINCIPAL,
    )

    outstanding_principal = contract.principal_amount - total_principal_paid

    if outstanding_principal < Decimal("0"):
        outstanding_principal = Decimal("0")

    return PaymentSummary(
        contract_id = contract.id,

        principal_amount = contract.principal_amount,
        total_interest_paid = total_interest_paid,
        total_principal_paid = total_principal_paid,
        outstanding_principal = outstanding_principal,
    )
