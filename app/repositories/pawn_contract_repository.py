from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pawn_contract import PawnContract, ContractStatus
from app.schemas.pawn_contract import (
    PawnContractCreate,
    PawnContractUpdate,
)


def get_contract_by_id(
    db: Session,
    contract_id: int,
) -> PawnContract | None:
    return db.get(PawnContract, contract_id)


def get_contract_by_code(
    db: Session,
    contract_code: str,
) -> PawnContract | None:
    statement = select(PawnContract).where(
        PawnContract.contract_code == contract_code
    )

    return db.scalar(statement)

def list_contracts(
    db: Session,
    offset: int = 0,
    limit: int = 20,
) -> list[PawnContract]:
    statement = (
        select(PawnContract)
        .order_by(PawnContract.id.desc())
        .offset(offset)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def create_contract(
    db: Session,
    contract_data: PawnContractCreate,
) -> PawnContract:
    contract = PawnContract(
        **contract_data.model_dump(),
    )

    db.add(contract)
    #db.commit()
   # db.refresh(contract)
    db.flush()

    return contract


def update_contract(
    db: Session,
    contract: PawnContract,
    contract_data: PawnContractUpdate,
) -> PawnContract:
    update_data = contract_data.model_dump(
        exclude_unset=True,
    )

    for field, value in update_data.items():
        setattr(contract, field, value)

    #db.commit()
    #db.refresh(contract)
    db.flush()
    
    return contract

#def get_active_contract_by_license_plate(
#    db: Session,
#    license_plate: str,
#) -> PawnContract | None:
#    statement = select(PawnContract).where(
#        PawnContract.license_plate == license_plate,
#        PawnContract.status == ContractStatus.ACTIVE,
#    )
#
#    return db.scalar(statement)

