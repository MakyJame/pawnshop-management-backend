from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.pawn_contract import (
    PawnContractCreate,
    PawnContractResponse,
    PawnContractUpdate,
)

from app.schemas.pawn_contract import (
    PawnContractWithAssetsCreate,
    PawnContractWithAssetsResponse,
)

from app.services.pawn_contract_service import (
    DirectRedeemedStatusUpdateNotAllowedError,
    InvalidPawnContractStatusError,
    PawnContractCodeAlreadyExistsError,
    PawnContractCustomerNotFoundError,
    PawnContractNotFoundError,
    LicensePlateAlreadyPawnedError,
    create_new_pawn_contract,
    get_pawn_contract,
    get_pawn_contracts,
    update_existing_pawn_contract,
    create_pawn_contract_with_assets,
)


router = APIRouter(
    prefix="/pawn-contracts",
    tags=["Pawn Contracts"],
)


@router.post(
    "",
    response_model=PawnContractResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_pawn_contract_endpoint(
    contract_data: PawnContractCreate,
    db: Session = Depends(get_db),
) -> PawnContractResponse:
    try:
        return create_new_pawn_contract(
            db,
            contract_data,
        )
    except PawnContractCustomerNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        ) from error
    except PawnContractCodeAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pawn contract code already exists.",
        ) from error

@router.post(
    "/with-assets",
    response_model=PawnContractWithAssetsResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_pawn_contract_with_assets_endpoint(
    contract_data: PawnContractWithAssetsCreate,
    db: Session = Depends(get_db),
) -> PawnContractWithAssetsResponse:
    try:
        return create_pawn_contract_with_assets(
            db,
            contract_data,
        )

    except PawnContractCustomerNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        ) from error

    except PawnContractCodeAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pawn contract code already exists.",
        ) from error

    except LicensePlateAlreadyPawnedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="License plate is already pawned.",
        ) from error


@router.get(
    "",
    response_model=list[PawnContractResponse],
)
def list_pawn_contracts_endpoint(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[PawnContractResponse]:
    return get_pawn_contracts(
        db,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{contract_id}",
    response_model=PawnContractResponse,
)
def get_pawn_contract_endpoint(
    contract_id: int,
    db: Session = Depends(get_db),
) -> PawnContractResponse:
    try:
        return get_pawn_contract(
            db,
            contract_id,
        )
    except PawnContractNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pawn contract not found.",
        ) from error


@router.patch(
    "/{contract_id}",
    response_model=PawnContractResponse,
)
def update_pawn_contract_endpoint(
    contract_id: int,
    contract_data: PawnContractUpdate,
    db: Session = Depends(get_db),
) -> PawnContractResponse:
    try:
        return update_existing_pawn_contract(
            db,
            contract_id,
            contract_data,
        )
    except PawnContractNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pawn contract not found.",
        ) from error
    except InvalidPawnContractStatusError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pawn contract status does not allow this update.",
        ) from error

    except DirectRedeemedStatusUpdateNotAllowedError as error:
        raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            "Pawn contract must be redeemed through "
            "the redemption endpoint."
        ),
    ) from error
