#repo.payment
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payment import Payment
from app.schemas.payment import PaymentCreate


def get_payment_by_id(
    db: Session,
    payment_id: int,
) -> Payment | None:
    return db.get(
        Payment,
        payment_id,
    )

def list_payments_by_contract(
    db: Session,
    contract_id: int,
) -> list[Payment]:
    statement = (
        select(Payment)
        .where(Payment.contract_id == contract_id)
        .order_by(
            Payment.payment_date,
            Payment.id
        )
    )
    return list(
        db.scalars(statement).all()
    )

def create_payment(
    db: Session,    
    payment_data: PaymentCreate,
) -> Payment:
    payment = Payment(
        **payment_data.model_dump()
    )

    db.add(payment)
    db.flush()

    return payment


#repo.payment
