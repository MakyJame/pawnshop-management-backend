from datetime import date

from app.services.pawn_contract_service import calculate_due_date

def test_calculate_due_date_adds_one_calendar_month() -> None:
    result = calculate_due_date(
        date(2026,9,6),
    )

    assert result == date(2026,10,6)

def test_calculate_due_date_handles_end_of_month() -> None:
    result = calculate_due_date(
        date(2026,1,30),
    )
    assert result == date(2026,2,28)
