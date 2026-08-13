from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.repositories.customer_repository import get_customer_by_phone
from app.schemas.pawn_asset import PawnAssetNestedCreate
from app.schemas.pawn_contract import PawnContractWithAssetsCreate
from app.services.pawn_contract_service import (
    LicensePlateAlreadyPawnedError,
    PawnContractCodeAlreadyExistsError,
    PawnContractCustomerNotFoundError,
    create_pawn_contract_with_assets,
)


CUSTOMER_PHONE = "0789606002"


def seed_pawn_contracts_with_assets(
    db: Session,
) -> None:
    customer = get_customer_by_phone(
        db,
        CUSTOMER_PHONE,
    )

    if customer is None:
        print(
            "Customer does not exist:",
            CUSTOMER_PHONE,
        )
        return

    contract_data = PawnContractWithAssetsCreate(
        contract_code="M-2026-002",
        customer_id=customer.id,
        principal_amount=Decimal("10000000"),
        monthly_interest_amount=Decimal("500000"),
        start_date=date(2026, 8, 4),
        due_date=date(2026, 9, 4),
        assets=[
            PawnAssetNestedCreate(
                asset_type="motorcycle",
                description="Xe máy Honda Air Blade đời 2014",
                brand="Honda Air Blade",
                model_year=2014,
                license_plate="61D1-0002",
            ),
        ],
    )

    try:
        contract = create_pawn_contract_with_assets(
            db,
            contract_data,
        )

        print(
            "Created pawn contract:",
            contract.id,
            contract.contract_code,
        )

        for asset in contract.assets:
            print(
                "Created pawn asset:",
                asset.id,
                asset.license_plate,
            )

    except PawnContractCodeAlreadyExistsError:
        print(
            "Pawn contract already exists:",
            contract_data.contract_code,
        )

    except PawnContractCustomerNotFoundError:
        print(
            "Customer does not exist:",
            CUSTOMER_PHONE,
        )

    except LicensePlateAlreadyPawnedError:
        print(
            "License plate is already pawned."
        )


def main() -> None:
    db = SessionLocal()

    try:
        seed_pawn_contracts_with_assets(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
