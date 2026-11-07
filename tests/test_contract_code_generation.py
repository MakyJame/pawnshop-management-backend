from datetime import date

from app.repositories.pawn_contract_repository import (
    generate_contract_code,
)


def test_generate_contract_code_uses_license_plate():
    result = generate_contract_code(
        license_plate="68D1-58050",
        start_date=date(2025, 2, 9),
    )

    assert result == "TL-20250209-68D1-58050"


def test_generate_contract_code_with_another_license_plate():
    result = generate_contract_code(
        license_plate="59A1-12345",
        start_date=date(2026, 7, 13),
    )

    assert result == "TL-20260713-59A1-12345"
