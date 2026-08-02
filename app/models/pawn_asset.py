from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.pawn_contract import PawnContract


class PawnAsset(Base):
    __tablename__ = "pawn_assets"

    id: Mapped[int] = mapped_column(primary_key=True)

    contract_id: Mapped[int] = mapped_column(
        ForeignKey("pawn_contracts.id"),
        nullable=False,
        index=True,
    )

    asset_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    brand: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    model_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    license_plate: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        index=True,
    )

    contract: Mapped["PawnContract"] = relationship(
        back_populates="assets",
    )
