from fastapi import APIRouter, Depends, HTTPException,Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.pawn_asset import (
    PawnAssetCreate,
    PawnAssetResponse,
    PawnAssetUpdate,
)
from app.services.pawn_asset_service import (
    LicensePlateAlreadyPawnedError,
    PawnAssetContractNotFoundError,
    PawnAssetNotFoundError,
    create_new_pawn_asset,
    get_contract_assets,
    get_pawn_asset,
    update_existing_pawn_asset,
)

#from app.services.pawn_contract_service import (
#    get_pawn_contracts,
#)

router = APIRouter(
    tags=["Pawn Assets"],
)


@router.post(
    "/pawn-assets",
    response_model=PawnAssetResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_pawn_asset_endpoint(
    asset_data: PawnAssetCreate,
    db: Session = Depends(get_db),
) -> PawnAssetResponse:
    try:
        return create_new_pawn_asset(
            db,
            asset_data,
        )
    except PawnAssetContractNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pawn contract not found.",
        ) from error
    except LicensePlateAlreadyPawnedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="License plate is already pawned in an active contract.",
        ) from error


@router.get(
    "/pawn-assets/{asset_id}",
    response_model=PawnAssetResponse,
)
def get_pawn_asset_endpoint(
    asset_id: int,
    db: Session = Depends(get_db),
) -> PawnAssetResponse:
    try:
        return get_pawn_asset(
            db,
            asset_id,
        )
    except PawnAssetNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pawn asset not found.",
        ) from error


@router.get(
    "/pawn-contracts/{contract_id}/assets",
    response_model=list[PawnAssetResponse],
)
def list_contract_assets_endpoint(
    contract_id: int,
    db: Session = Depends(get_db),
) -> list[PawnAssetResponse]:
    try:
        return get_contract_assets(
            db,
            contract_id,
        )
    except PawnAssetContractNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pawn contract not found.",
        ) from error


@router.patch(
    "/pawn-assets/{asset_id}",
    response_model=PawnAssetResponse,
)
def update_pawn_asset_endpoint(
    asset_id: int,
    asset_data: PawnAssetUpdate,
    db: Session = Depends(get_db),
) -> PawnAssetResponse:
    try:
        return update_existing_pawn_asset(
            db,
            asset_id,
            asset_data,
        )
    except PawnAssetNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pawn asset not found.",
        ) from error
    except LicensePlateAlreadyPawnedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="License plate is already pawned in an active contract.",
        ) from error
