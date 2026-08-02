from pydantic import BaseModel, ConfigDict, Field, field_validator


class PawnAssetCreate(BaseModel):
    contract_id: int = Field(gt=0)

    asset_type: str = Field(
        min_length=2,
        max_length=50,
    )

    description: str = Field(
        min_length=2,
        max_length=500,
    )

    brand: str | None = Field(
        default=None,
        max_length=100,
    )

    model_year: int | None = Field(
        default=None,
        ge=1900,
        le=2100,
    )

    license_plate: str | None = Field(
        default=None,
        max_length=30,
    )

    @field_validator("license_plate")
    @classmethod
    def normalize_license_plate(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        return value.strip().upper().replace(" ", "")


class PawnAssetUpdate(BaseModel):
    asset_type: str | None = Field(
        default=None,
        min_length=2,
        max_length=50,
    )

    description: str | None = Field(
        default=None,
        min_length=2,
        max_length=500,
    )

    brand: str | None = Field(
        default=None,
        max_length=100,
    )

    model_year: int | None = Field(
        default=None,
        ge=1900,
        le=2100,
    )

    license_plate: str | None = Field(
        default=None,
        max_length=30,
    )

    @field_validator("license_plate")
    @classmethod
    def normalize_license_plate(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        return value.strip().upper().replace(" ", "")


class PawnAssetResponse(BaseModel):
    id: int
    contract_id: int
    asset_type: str
    description: str
    brand: str | None
    model_year: int | None
    license_plate: str | None

    model_config = ConfigDict(from_attributes=True)
