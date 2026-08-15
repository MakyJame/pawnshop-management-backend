from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.payment import (
    PaymentCreate,
    PaymentResponse,
)

from app.services.payment_service import (
    PaymentContractClosedError,
    PaymentContractNotFoundError,
    PaymentNotFoundError,
    create_new_payment,
    get_contract_payments,
    get_payment,
)

router = APIRouter(
    tags=["Payment"],
)

@router.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)

def create_payment_endpoint(
    payment_data: PaymentCreate,
    db: Session = Depends(get_db),
) -> PaymentResponse:
    try:
        return create_new_payment(
            db,
            payment_data,
        )

    except PaymentContractNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pawn contract not found.",
        ) from error

    except PaymentContractClosedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pawn contract is closed and cannot receive payments.",
        ) from error

@router.get(
    "/payments/{payment_id}",
    response_model=PaymentResponse,
)

def get_payment_endpoint(
    payment_id: int,
    db: Session = Depends(get_db),
) -> PaymentResponse:
    try:
        return get_payment(
            db,
            payment_id,
        )

    except PaymentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        ) from error

@router.get(
    "/pawn-contracts/{contract_id}/payments",
    response_model=list[PaymentResponse],
)
def list_contract_payments_endpoint(
    contract_id: int,
    db: Session = Depends(get_db),
) -> list[PaymentResponse]:
    try:
        return get_contract_payments(
            db,
            contract_id,
        )

    except PaymentContractNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pawn contract not found.",
        ) from error
