#models.pawn_contract
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum as SqlEnum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.pawn_asset import PawnAsset
    from app.models.payment import Payment


class ContractStatus(str, Enum):
    ACTIVE = "active"
    REDEEMED = "redeemed"
    OVERDUE = "overdue"
    LIQUIDATED = "liquidated"


class PawnContract(Base):
    __tablename__ = "pawn_contracts"

    id: Mapped[int] = mapped_column(primary_key=True)

    contract_code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False,
        index=True,
    )

    principal_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 0),
        nullable=False,
    )

    monthly_interest_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 0),
        nullable=False,
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    due_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    status: Mapped[ContractStatus] = mapped_column(
        SqlEnum(
            ContractStatus,
            name="contract_status",
        ),
        default=ContractStatus.ACTIVE,
        nullable=False,
    )

    customer: Mapped["Customer"] = relationship(
        back_populates="pawn_contracts",
    )

    assets: Mapped[list["PawnAsset"]] = relationship(
        back_populates="contract",
        cascade="all, delete-orphan",
    )

    payments: Mapped[list["Payment"]] = relationship(
        back_populates="contract",
        cascade="all, delete-orphan",
    )

#models.pawn_contract
