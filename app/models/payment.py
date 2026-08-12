#model.payment
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum as SqlEnum, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.pawn_contract import PawnContract


class PaymentType(str, Enum):
    INTEREST = "interest"
    PRINCIPAL = "principal"
    REDEMPTION = "redemption"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    contract_id: Mapped[int] = mapped_column(
        ForeignKey("pawn_contracts.id"),
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 0),
        nullable=False,
    )

    payment_type: Mapped[PaymentType] = mapped_column(
        SqlEnum(
            PaymentType,
            name="payment_type",
        ),
        nullable=False,
    )

    payment_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    contract: Mapped["PawnContract"] = relationship(
        back_populates="payments",
    )
#model.payment
