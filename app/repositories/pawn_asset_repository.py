from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pawn_asset import PawnAsset
from app.models.pawn_contract import ContractStatus, PawnContract
from app.schemas.pawn_asset import PawnAssetCreate, PawnAssetUpdate


def get_asset_by_id(
    db: Session,
    asset_id: int,
) -> PawnAsset | None:
    return db.get(PawnAsset, asset_id)


def list_assets_by_contract(
    db: Session,
    contract_id: int,
) -> list[PawnAsset]:
    statement = (
        select(PawnAsset)
        .where(PawnAsset.contract_id == contract_id)
        .order_by(PawnAsset.id)
    )

    return list(db.scalars(statement).all())


def get_active_asset_by_license_plate(
    db: Session,
    license_plate: str,
) -> PawnAsset | None:
    statement = (
        select(PawnAsset)
        .join(PawnContract)
        .where(
            PawnAsset.license_plate == license_plate,
            PawnContract.status == ContractStatus.ACTIVE,
        )
    )

    return db.scalar(statement)


def create_asset(
    db: Session,
    asset_data: PawnAssetCreate,
) -> PawnAsset:
    asset = PawnAsset(
        **asset_data.model_dump(),
    )

    db.add(asset)
    db.flush()
    db.refresh(asset)

    return asset


def update_asset(
    db: Session,
    asset: PawnAsset,
    asset_data: PawnAssetUpdate,
) -> PawnAsset:
    update_data = asset_data.model_dump(
        exclude_unset=True,
    )

    for field, value in update_data.items():
        setattr(asset, field, value)

    db.commit()
    db.refresh(asset)

    return asset
