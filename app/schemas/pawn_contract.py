from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.pawn_contract import ContractStatus

from app.schemas.pawn_asset import (
    PawnAssetNestedCreate,
    PawnAssetResponse,
)

class PawnContractCreate(BaseModel):
    contract_code: str = Field(
        min_length=1,
        max_length=30,
    )

    customer_id: int = Field(gt=0)

    principal_amount: Decimal = Field(gt=0)

    monthly_interest_amount: Decimal = Field(ge=0)

    start_date: date

    model_config = ConfigDict(
        extra="forbid",
    )

class PawnContractUpdate(BaseModel):
    monthly_interest_amount: Decimal | None = Field(
        default=None,
        ge=0,
    )
    model_config = ConfigDict(
        extra="forbid",
    )

class PawnContractResponse(BaseModel):
    id: int
    contract_code: str
    customer_id: int
    principal_amount: Decimal
    monthly_interest_amount: Decimal
    start_date: date
    due_date: date
    status: ContractStatus

    model_config = ConfigDict(from_attributes=True)

class PawnContractWithAssetsCreate(PawnContractCreate):
    assets: list[PawnAssetNestedCreate] = Field(
        min_length=1,
        max_length=10,
    )


class PawnContractWithAssetsResponse(PawnContractResponse):
    assets: list[PawnAssetResponse]

    model_config = ConfigDict(from_attributes=True)

class OverdueRefreshResponse(BaseModel):
    updated_count: int
    contract_ids: list[int]
