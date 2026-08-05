from app.db.session import SessionLocal
from app.schemas.customer import CustomerCreate
from app.services.customer_service import (
    CustomerPhoneAlreadyExistsError,
    create_new_customer,
)


def seed_customers() -> None:
    db = SessionLocal()
    customer_data = [
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
    try:
        for customer in customer_data:
            try:
                created_customer=create_new_customer(
                    db,
                    customer,
                )
                print(
                    "Created customer:",
                    created_customer.id,
                    created_customer.name,
                )


            except CustomerPhoneAlreadyExistsError:
                print("Customer already exists: 0328888718")

    finally:
        db.close()


if __name__ == "__main__":
    seed_customers()
