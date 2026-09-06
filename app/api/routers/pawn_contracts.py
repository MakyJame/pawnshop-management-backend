from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from datetime import date

from app.db.session import get_db
from app.schemas.pawn_contract import (
    PawnContractCreate,
    PawnContractResponse,
    PawnContractUpdate,
)

from app.schemas.pawn_contract import (
    PawnContractWithAssetsCreate,
    PawnContractWithAssetsResponse,
    OverdueRefreshResponse,
)

from app.services.pawn_contract_service import (
    PawnContractNotEditableError,
<<<<<<< HEAD
    DirectLiquidatedStatusUpdateNotAllowedError,
=======
>>>>>>> practice/rebuild-backend
    LiquidationContractNotOverdueError,
    LiquidationGracePeriodNotExpiredError,
    liquidate_contract,
    PawnContractCodeAlreadyExistsError,
    PawnContractCustomerNotFoundError,
    PawnContractNotFoundError,
    LicensePlateAlreadyPawnedError,
    create_new_pawn_contract,
    get_pawn_contract,
    get_pawn_contracts,
    update_existing_pawn_contract,
    create_pawn_contract_with_assets,
     mark_overdue_contracts,
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

@router.post(
    "/refresh-overdue",
    response_model=OverdueRefreshResponse,
)
def refresh_overdue_contracts_endpoint(
    db: Session = Depends(get_db),
) -> OverdueRefreshResponse:
    contracts = mark_overdue_contracts(
        db,
        date.today(),
    )

    return OverdueRefreshResponse(
        updated_count=len(contracts),
        contract_ids=[
            contract.id
            for contract in contracts
        ],
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

    except PawnContractNotEditableError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Pawn contract can only be edited "
                "while it is active."
            ),
        ) from error

<<<<<<< HEAD

    except InvalidPawnContractStatusError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pawn contract status transition is not allowed.",
        ) from error

    except PawnContractNotEditableError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Pawn contract can only be edited "
                "while it is active."
        ),
    ) from error

=======
>>>>>>> practice/rebuild-backend
@router.post(
    "/{contract_id}/liquidate",
    response_model=PawnContractResponse,
)
def liquidate_pawn_contract_endpoint(
    contract_id: int,
    db: Session = Depends(get_db),
) -> PawnContractResponse:
    try:
        return liquidate_contract(
            db,
            contract_id,
            as_of_date=date.today(),
        )

    except PawnContractNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pawn contract not found.",
        ) from error

    except LiquidationContractNotOverdueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only overdue pawn contracts "
                "can be liquidated."
            ),
        ) from error

    except LiquidationGracePeriodNotExpiredError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Pawn contract cannot be liquidated "
                "until the 3-day grace period has expired."
            ),
        ) from error

