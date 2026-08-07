from app.db.session import SessionLocal
from sqlalchemy.orm import Session
from app.schemas.customer import CustomerCreate
from app.services.customer_service import (
    CustomerPhoneAlreadyExistsError,
    create_new_customer,
)

CUSTOMERS_DATA=[
    CustomerCreate(
        name="Minh 1",
        phone="0789606001",
    ),
    CustomerCreate(
        name="Minh 2",
        phone="0789606002",
    ),
    CustomerCreate(
        name="Minh 3",
        phone="0789606003",
    ),
]

def seed_customers(
    db: Session,
) -> None:
    #db = SessionLocal()

    for customer_data in CUSTOMERS_DATA:
        try:
            customer = create_new_customer(
                db,
                customer_data,
            )
            print(
                "Created customer:",
                customer.id,
                customer.name,
            )


        except CustomerPhoneAlreadyExistsError:
            print(
                    "Customer already exists: ",
                    customer_data.phone,
                  )

def main() -> None:
    db = SessionLocal()

    try:
        seed_customers(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
