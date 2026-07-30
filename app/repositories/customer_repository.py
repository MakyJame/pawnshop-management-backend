from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate


def get_customer_by_id(
    db: Session,
    customer_id: int,
) -> Customer | None:
    return db.get(Customer, customer_id)


def get_customer_by_phone(
    db: Session,
    phone: str,
) -> Customer | None:
    statement = select(Customer).where(Customer.phone == phone)

    return db.scalar(statement)


def list_customers(
    db: Session,
    offset: int = 0,
    limit: int = 20,
) -> list[Customer]:
    statement = (
        select(Customer)
        .order_by(Customer.id)
        .offset(offset)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def create_customer(
    db: Session,
    customer_data: CustomerCreate,
) -> Customer:
    customer = Customer(
        **customer_data.model_dump(),
    )

    db.add(customer)
    db.commit()
    db.refresh(customer)

    return customer


def update_customer(
    db: Session,
    customer: Customer,
    customer_data: CustomerUpdate,
) -> Customer:
    update_data = customer_data.model_dump(
        exclude_unset=True,
    )

    for field, value in update_data.items():
        setattr(customer, field, value)

    db.commit()
    db.refresh(customer)

    return customer


def delete_customer(
    db: Session,
    customer: Customer,
) -> None:
    db.delete(customer)
    db.commit()
