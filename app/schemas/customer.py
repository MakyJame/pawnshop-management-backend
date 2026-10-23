from pydantic import BaseModel, ConfigDict, Field, BeforeValidator

from typing import Annotated

def remove_whitespace(value: object) -> object:
    if isinstance(value, str):
        return "".join(value.split())
    return value

Phone = Annotated[
    str,
    Field(
        pattern=r"^0[0-9]{9}$",
        min_length=10,
        max_length=10,
    ),
    BeforeValidator(remove_whitespace),
]

Identity = Annotated[
    str,
    Field(
        pattern=r"^[0-9]{12}$",
        min_length=12,
        max_length=12,
    ),
    BeforeValidator(remove_whitespace),
]

class CustomerBase(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=100,
    )

    phone: Phone
    identity: Identity | None = None

class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    phone: Phone | None = None
    identity: Identity | None = None


class CustomerResponse(CustomerBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
