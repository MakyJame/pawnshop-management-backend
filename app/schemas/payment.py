#schema.payment
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.payment import PaymentType


class PaymentCreate(BaseModel):
    contract_id: int = Field(gt=0)

    amount: Decimal = Field(gt=0)

    payment_type: PaymentType

    payment_date: date

    note: str | None = Field(
        default=None,
        max_length=500,
    )


class PaymentResponse(BaseModel):
    id: int
    contract_id: int
    amount: Decimal
    payment_type: PaymentType
    payment_date: date
    note: str | None

    model_config = ConfigDict(
        from_attributes=True,
    )
#schema.payment

