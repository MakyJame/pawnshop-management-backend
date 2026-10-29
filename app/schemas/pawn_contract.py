from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.pawn_contract import ContractStatus

from app.schemas.pawn_asset import (
    PawnAssetNestedCreate,
    PawnAssetResponse,
)
from app.schemas.customer import CustomerCreate, CustomerResponse
from app.schemas.payment import PaymentResponse, PaymentSummary

class PawnContractCreate(BaseModel):
    customer_id: int = Field(gt=0)

    principal_amount: Decimal = Field(gt=0)

    monthly_interest_amount: Decimal = Field(ge=0)

    start_date: date

    model_config = ConfigDict(
        extra="forbid",
    )

class PawnContractRenewCreate(BaseModel):
    additional_amount: Decimal = Field(gt=0)

    monthly_interest_amount: Decimal = Field(ge=0)

    start_date: date

    model_config = ConfigDict(extra="forbid")

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
    previous_contract_id: int | None

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

class PawnContractDetailsCreate(BaseModel):
    principal_amount: Decimal = Field(gt=0)

    monthly_interest_amount: Decimal = Field(ge=0)

    start_date: date

    model_config = ConfigDict(extra="forbid")

class PawnContractWithCustomerAndAssetsCreate(BaseModel):
    customer_id: int | None = Field(
        default=None,
        gt=0,
    )

    customer: CustomerCreate | None = None

    contract: PawnContractDetailsCreate

    assets: list[PawnAssetNestedCreate] = Field(
        min_length=1,
        max_length=10,
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_customer_selection(self):
        if (self.customer_id is None) == (self.customer is None):
            raise ValueError(
                "Provide exactly one of customer_id or customer"
            )

        return self

class PawnContractDetailsResponse(BaseModel):
    contract: PawnContractResponse
    customer: CustomerResponse
    assets: list[PawnAssetResponse]
    payments: list[PaymentResponse]
    payment_summary: PaymentSummary

class PawnContractSearchResponse(BaseModel):
    contract_id: int
    contract_code: str
    status: ContractStatus

    customer_id: int
    customer_name: str
    customer_phone: str

    asset_id: int
    license_plate: str

    model_config = ConfigDict(from_attributes=True)
