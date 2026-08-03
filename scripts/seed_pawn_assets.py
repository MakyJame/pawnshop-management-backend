from app.db.session import SessionLocal
from app.repositories.pawn_contract_repository import (
    get_contract_by_code,
)
from app.schemas.pawn_asset import PawnAssetCreate
from app.services.pawn_asset_service import (
    LicensePlateAlreadyPawnedError,
    PawnAssetContractNotFoundError,
    create_new_pawn_asset,
)


CONTRACT_CODE = "M-2026-001"
LICENSE_PLATE = "36D1-18610"


def seed_pawn_assets() -> None:
    db = SessionLocal()

    try:
        contract = get_contract_by_code(
            db,
            CONTRACT_CODE,
        )

        if contract is None:
            print(
                "Pawn contract does not exist. "
                "Run seed_pawn_contracts first."
            )
            return

        try:
            asset = create_new_pawn_asset(
                db,
                PawnAssetCreate(
                    contract_id=contract.id,
                    asset_type="motorcycle",
                    description="Xe máy Air Blade đời 2013",
                    brand="Air Blade",
                    model_year=2013,
                    license_plate=LICENSE_PLATE,
                ),
            )

            print(
                "Created pawn asset:",
                asset.id,
                asset.license_plate,
            )

        except LicensePlateAlreadyPawnedError:
            print(
                "Pawn asset already exists:",
                LICENSE_PLATE,
            )

        except PawnAssetContractNotFoundError:
            print(
                "Pawn contract does not exist:",
                CONTRACT_CODE,
            )

    finally:
        db.close()


if __name__ == "__main__":
    seed_pawn_assets()
