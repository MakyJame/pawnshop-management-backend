from pydantic import BaseModel, ConfigDict, Field


class CustomerBase(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=100,
    )

    phone: str = Field(
        min_length=8,
        max_length=20,
    )


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    phone: str | None = Field(
        default=None,
        min_length=8,
        max_length=20,
    )


class CustomerResponse(CustomerBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
