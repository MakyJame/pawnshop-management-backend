from sqlalchemy.orm import Session

from app.models.pawn_contract import ContractStatus, PawnContract
from app.models.pawn_asset import PawnAsset

from app.repositories.customer_repository import get_customer_by_id
from app.repositories.pawn_contract_repository import (
    create_contract,
    get_contract_by_code,
    get_contract_by_id,
    list_contracts,
    update_contract,
)

from app.repositories.pawn_asset_repository import (
    get_active_asset_by_license_plate,
)

from app.schemas.pawn_contract import (
    PawnContractCreate,
    PawnContractUpdate,
    PawnContractWithAssetsCreate
)

from app.schemas.pawn_asset import PawnAssetCreate


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

    if contract.status == ContractStatus.LIQUIDATED:
        raise InvalidPawnContractStatusError

    if (
        contract.status == ContractStatus.REDEEMED
        and contract_data.status is not None
    ):
        raise InvalidPawnContractStatusError

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
