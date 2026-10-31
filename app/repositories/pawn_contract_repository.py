from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pawn_contract import PawnContract, ContractStatus
from app.models.pawn_asset import PawnAsset
from app.models.customer import Customer

from app.schemas.pawn_contract import (
    PawnContractCreate,
    PawnContractUpdate,
)

from datetime import date
from decimal import Decimal

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
        .order_by(PawnContract.id)
        .offset(offset)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def create_contract(
    db: Session,
    contract_data: PawnContractCreate,
    due_date: date,
    *,
    monthly_interest_amount: Decimal,
) -> PawnContract:

    contract_fields = contract_data.model_dump(
        exclude={"monthly_interest_amount"},
    )

    contract = PawnContract(
        **contract_fields,
        monthly_interest_amount=monthly_interest_amount,
        due_date=due_date,
    )

    db.add(contract)
    db.flush()

    contract.contract_code = generate_contract_code(
        contract.id,
        contract.start_date,
    )
    db.flush()

    return contract

def create_renewed_contract(
    db: Session,
      *,
    customer_id: int,
    principal_amount: Decimal,
    monthly_interest_amount: Decimal,
    start_date: date,
    due_date: date,
    previous_contract_id: int,
) -> PawnContract:
    contract = PawnContract(
        customer_id=customer_id,
        principal_amount=principal_amount,
        monthly_interest_amount=monthly_interest_amount,
        start_date=start_date,
        due_date=due_date,
        previous_contract_id=previous_contract_id,
    )
    db.add(contract)
    db.flush()
    
    contract.contract_code = generate_contract_code(
        contract.id,
        contract.start_date,
    )
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

def list_active_contracts_past_due(
    db: Session,
    as_of_date: date,
) -> list[PawnContract]:
    statement = (
        select(PawnContract)
        .where(
            PawnContract.status == ContractStatus.ACTIVE,
            PawnContract.due_date < as_of_date,
        )
        .order_by(PawnContract.id)
    )

    return list(db.scalars(statement).all())

def generate_contract_code(
    contract_id: int,
    start_date: date,
) -> str:
    date_part = start_date.strftime("%Y%m%d")
    return f"TL-{date_part}-{contract_id}"

def search_contracts_by_license_plate(
    db: Session,
    license_plate: str,
    offset: int = 0,
    limit: int = 20,
) -> list[dict]:

    escaped_plate = (
        license_plate
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )

    pattern = f"%{escaped_plate}%"

    statement = (
        select(
            PawnContract.id.label("contract_id"),
            PawnContract.contract_code,
            PawnContract.status,

            Customer.id.label("customer_id"),
            Customer.name.label("customer_name"),
            Customer.phone.label("customer_phone"),

            PawnAsset.id.label("asset_id"),
            PawnAsset.license_plate,
        )
        .select_from(PawnAsset)
        .join(
            PawnContract,
            PawnAsset.contract_id == PawnContract.id,
        )
        .join(
            Customer,
            PawnContract.customer_id == Customer.id,
        )
        .where(
            PawnAsset.license_plate.ilike(
                pattern,
                escape="\\",
            )
        )
        .order_by(
            PawnContract.id.desc(),
            PawnAsset.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )

    results = db.execute(statement).mappings().all()

    return [dict(row) for row in results]
