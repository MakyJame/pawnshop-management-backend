from app.db.session import SessionLocal
from app.schemas.customer import CustomerCreate
from app.services.customer_service import (
    CustomerPhoneAlreadyExistsError,
    create_new_customer,
)


def seed_customers() -> None:
    db = SessionLocal()

    try:
        try:
            customer = create_new_customer(
                db,
                CustomerCreate(
                    name="Nguyen Van Hung",
                    phone="0328888718",
                ),
            )

            print(
                "Created customer:",
                customer.id,
                customer.name,
            )

        except CustomerPhoneAlreadyExistsError:
            print("Customer already exists: 0328888718")

    finally:
        db.close()


if __name__ == "__main__":
    seed_customers()
