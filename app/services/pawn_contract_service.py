from sqlalchemy.orm import Session

from app.models.pawn_contract import ContractStatus, PawnContract
from app.repositories.customer_repository import get_customer_by_id
from app.repositories.pawn_contract_repository import (
    create_contract,
    get_contract_by_code,
    get_contract_by_id,
    list_contracts,
    update_contract,
)
from app.schemas.pawn_contract import (
    PawnContractCreate,
    PawnContractUpdate,
)


class PawnContractNotFoundError(Exception):
    pass


class PawnContractCodeAlreadyExistsError(Exception):
    pass


class PawnContractCustomerNotFoundError(Exception):
    pass


class InvalidPawnContractStatusError(Exception):
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

    return create_contract(
        db,
        contract_data,
    )


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

    return update_contract(
        db,
        contract,
        contract_data,
    )
