from sqlalchemy.orm import Session

from datetime import date

from app.models.pawn_contract import ContractStatus, PawnContract
from app.models.pawn_asset import PawnAsset

from app.repositories.customer_repository import get_customer_by_id
from app.repositories.pawn_contract_repository import (
    create_contract,
    get_contract_by_code,
    get_contract_by_id,
    list_contracts,
    update_contract,
    list_active_contracts_past_due,
)

from app.repositories.pawn_asset_repository import (
    get_active_asset_by_license_plate,
)

from app.schemas.pawn_contract import (
    PawnContractCreate,
    PawnContractUpdate,
    PawnContractResponse,
    PawnContractWithAssetsCreate
)

from app.schemas.pawn_asset import PawnAssetCreate

ALLOWED_STATUS_TRANSITIONS: dict[
    ContractStatus,
    set[ContractStatus],
] = {
    ContractStatus.ACTIVE: {
        #ContractStatus.OVERDUE,
        ContractStatus.LIQUIDATED,
    },
    ContractStatus.OVERDUE: {
        ContractStatus.LIQUIDATED,
    },
    ContractStatus.REDEEMED: set(),
    ContractStatus.LIQUIDATED: set(),
}

class PawnContractNotFoundError(Exception):
    pass


class PawnContractCodeAlreadyExistsError(Exception):
    pass


class PawnContractCustomerNotFoundError(Exception):
    pass


class InvalidPawnContractStatusError(Exception):
    pass

class LicensePlateAlreadyPawnedError(Exception):
    pass

class DirectRedeemedStatusUpdateNotAllowedError(Exception):
    pass

class DirectOverdueStatusUpdateNotAllowedError(Exception):
    pass

def get_pawn_contract(
    db: Session,
    contract_id: int,
) -> PawnContract:
    contract = get_contract_by_id(db, contract_id)

    if contract is None:
        raise PawnContractNotFoundError

    return contract


def get_pawn_contracts(
    db: Session,
    offset: int = 0,
    limit: int = 20,
) -> list[PawnContract]:
    return list_contracts(
        db,
        offset=offset,
        limit=limit,
    )


def create_new_pawn_contract(
    db: Session,
    contract_data: PawnContractCreate,
) -> PawnContract:
    customer = get_customer_by_id(
        db,
        contract_data.customer_id,
    )

    if customer is None:
        raise PawnContractCustomerNotFoundError

    existing_contract = get_contract_by_code(
        db,
        contract_data.contract_code,
    )

    if existing_contract is not None:
        raise PawnContractCodeAlreadyExistsError

    try:
        contract = create_contract(
            db,
            contract_data,
        )

        db.commit()
        db.refresh(contract)
        
        return contract
    except Exception:
        db.rollback()
        raise


def update_existing_pawn_contract(
    db: Session,
    contract_id: int,
    contract_data: PawnContractUpdate,
) -> PawnContract:
    contract = get_pawn_contract(
        db,
        contract_id,
    )

    if contract_data.status is not None:
        validate_status_transition(
            contract.status,
            contract_data.status,
        )

    try:
        updated_contract = update_contract(
            db,
            contract,
            contract_data,
        )

        db.commit()
        db.refresh(updated_contract)

        return updated_contract
    except Exception:
        db.rollback()
        raise

def create_pawn_contract_with_assets(
    db: Session,
    contract_data: PawnContractWithAssetsCreate,
) -> PawnContract:
    customer = get_customer_by_id(
        db,
        contract_data.customer_id,
    )

    if customer is None:
        raise PawnContractCustomerNotFoundError

    existing_contract = get_contract_by_code(
        db,
        contract_data.contract_code,
    )

    if existing_contract is not None:
        raise PawnContractCodeAlreadyExistsError

    for asset_data in contract_data.assets:
        if asset_data.license_plate is None:
            continue

        existing_asset = get_active_asset_by_license_plate(
            db,
            asset_data.license_plate,
        )

        if existing_asset is not None:
            raise LicensePlateAlreadyPawnedError

    try:
        contract_fields = contract_data.model_dump(
            exclude={"assets"},
        )

        contract = PawnContract(
            **contract_fields,
        )

        db.add(contract)
        db.flush()

        for asset_data in contract_data.assets:
            asset = PawnAsset(
                contract_id=contract.id,
                **asset_data.model_dump(),
            )

            db.add(asset)

        db.commit()
        db.refresh(contract)

        return contract

    except Exception:
        db.rollback()
        raise

def validate_status_transition(
    current_status: ContractStatus,
    new_status: ContractStatus,
) -> None:
    if new_status == ContractStatus.REDEEMED:
        raise DirectRedeemedStatusUpdateNotAllowedError

    if new_status == ContractStatus.OVERDUE:
        raise DirectOverdueStatusUpdateNotAllowedError

    allowed_statuses = ALLOWED_STATUS_TRANSITIONS[
        current_status
    ]

    if new_status not in allowed_statuses:
        raise InvalidPawnContractStatusError

def mark_overdue_contracts(
    db: Session,
    as_of_date: date,
) -> list[PawnContract]:
    contracts = list_active_contracts_past_due(
        db,
        as_of_date,
    )

    try:
        for contract in contracts:
            contract.status = ContractStatus.OVERDUE

        db.commit()

        for contract in contracts:
            db.refresh(contract)

        return contracts

    except Exception:
        db.rollback()
        raise

def calculate_days_overdue(
    due_date: date,
    as_of_date: date,
) -> int:
    if due_date < as_of_date:
        return (as_of_date - due_date).days
    return 0

def calculate_overdue_bucket(
    days_overdue: int,
) -> str:
    if day_overdue < 0:
        raise ValueError(
            "days_overdue cannot be negative"
        )

    if days_overdue == 0:
        return "not_overdue"

    if days_overdue <= 30:
        return "overdue_1_30"

    if days_overdue <= 60:
        return "overdue_31_60"

    if days_overdue <= 90:
        return "overdue_61_90"

    return "over_90_plus"

def build_pawn_contract_response(
    contract: PawnContract,
    as_of_date: date,
) -> PawnContractResponse:
    days_overdue = calculate_days_overdue(
        contract.due_date,
        as_of_date,
    )

    overdue_bucket = calculate_overdue_bucket(
        days_overdue,
    )

    return PawnContractResponse(
        id=contract.id,
        contract_code=contract.contract_code,
        customer_id=contract.customer_id,
        principal_amount=contract.principal_amount,
        monthly_interest_amount=contract.monthly_interest_amount,
        start_date=contract.start_date,
        due_date=contract.due_date,
        status=contract.status,
        days_overdue=days_overdue,
        overdue_bucket=overdue_bucket,
    )
