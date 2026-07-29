#from datetime import datetime
#from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from sqlalchemy import String
from app.db.base import Base

class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
            String(100),
            nullable=False,
    )

    phone: Mapped[str] = mapped_column(
            String(20),
            unique=True,
            nullable=False,
    )
