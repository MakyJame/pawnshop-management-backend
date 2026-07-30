from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.repositories.customer_repository import (
    create_customer,
    delete_customer,
    get_customer_by_id,
    get_customer_by_phone,
    list_customers,
    update_customer,
)
from app.schemas.customer import CustomerCreate, CustomerUpdate


class CustomerNotFoundError(Exception):
    pass


class CustomerPhoneAlreadyExistsError(Exception):
    pass


def get_customer(
    db: Session,
    customer_id: int,
) -> Customer:
    customer = get_customer_by_id(db, customer_id)

    if customer is None:
        raise CustomerNotFoundError

    return customer


def get_customers(
    db: Session,
    offset: int = 0,
    limit: int = 20,
) -> list[Customer]:
    return list_customers(
        db,
        offset=offset,
        limit=limit,
    )


def create_new_customer(
    db: Session,
    customer_data: CustomerCreate,
) -> Customer:
    existing_customer = get_customer_by_phone(
        db,
        customer_data.phone,
    )

    if existing_customer is not None:
        raise CustomerPhoneAlreadyExistsError

    return create_customer(
        db,
        customer_data,
    )


def update_existing_customer(
    db: Session,
    customer_id: int,
    customer_data: CustomerUpdate,
) -> Customer:
    customer = get_customer(
        db,
        customer_id,
    )

    if (
        customer_data.phone is not None
        and customer_data.phone != customer.phone
    ):
        existing_customer = get_customer_by_phone(
            db,
            customer_data.phone,
        )

        if existing_customer is not None:
            raise CustomerPhoneAlreadyExistsError

    return update_customer(
        db,
        customer,
        customer_data,
    )


def delete_existing_customer(
    db: Session,
    customer_id: int,
) -> None:
    customer = get_customer(
        db,
        customer_id,
    )

    delete_customer(
        db,
        customer,
    )
