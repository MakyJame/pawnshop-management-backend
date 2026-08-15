from sqlalchemy.orm import Session

from app.models.pawn_asset import PawnAsset
from app.repositories.pawn_asset_repository import (
    create_asset,
    get_active_asset_by_license_plate,
    get_asset_by_id,
    list_assets_by_contract,
    update_asset,
)
from app.repositories.pawn_contract_repository import get_contract_by_id
from app.schemas.pawn_asset import PawnAssetCreate, PawnAssetUpdate


class PawnAssetNotFoundError(Exception):
    pass


class PawnAssetContractNotFoundError(Exception):
    pass


class LicensePlateAlreadyPawnedError(Exception):
    pass

def get_pawn_asset(
    db: Session,
    asset_id: int,
) -> PawnAsset:
    asset = get_asset_by_id(db, asset_id)

    if asset is None:
        raise PawnAssetNotFoundError

    return asset


def get_contract_assets(
    db: Session,
    contract_id: int,
) -> list[PawnAsset]:
    contract = get_contract_by_id(db, contract_id)

    if contract is None:
        raise PawnAssetContractNotFoundError

    return list_assets_by_contract(
        db,
        contract_id,
    )


def create_new_pawn_asset(
    db: Session,
    asset_data: PawnAssetCreate,
) -> PawnAsset:
    contract = get_contract_by_id(
        db,
        asset_data.contract_id,
    )

    if contract is None:
        raise PawnAssetContractNotFoundError

    if asset_data.license_plate is not None:
        existing_asset = get_active_asset_by_license_plate(
            db,
            asset_data.license_plate,
        )

        if existing_asset is not None:
            raise LicensePlateAlreadyPawnedError

    return create_asset(
        db,
        asset_data,
    )


def update_existing_pawn_asset(
    db: Session,
    asset_id: int,
    asset_data: PawnAssetUpdate,
) -> PawnAsset:
    asset = get_pawn_asset(
        db,
        asset_id,
    )

    if (
        asset_data.license_plate is not None
        and asset_data.license_plate != asset.license_plate
    ):
        existing_asset = get_active_asset_by_license_plate(
            db,
            asset_data.license_plate,
        )

        if existing_asset is not None:
            raise LicensePlateAlreadyPawnedError

    return update_asset(
        db,
        asset,
        asset_data,
    )
