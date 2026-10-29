from decimal import Decimal


def calculate_monthly_interest(
    principal_amount: Decimal,
) -> Decimal:

    if principal_amount <= Decimal("0"):
        raise ValueError(
            "Principal amount must be greater than zero"
        )

    if principal_amount <= Decimal("5500000"):
        monthly_interest = principal_amount * Decimal("0.06")

    elif principal_amount <= Decimal("14000000"):
        monthly_interest = principal_amount * Decimal("0.05")

    elif principal_amount <= Decimal("20000000"):
        monthly_interest = (
            principal_amount * Decimal("0.05")
            - Decimal("50000")
        )

    elif principal_amount < Decimal("30000000"):
        monthly_interest = principal_amount * Decimal("0.045")

    elif principal_amount >= Decimal("30000000"):
        monthly_interest = principal_amount * Decimal("0.04")

    else:
        raise ValueError(
            "Interest rule for exactly 30,000,000 VND is not defined"
        )

    return monthly_interest.quantize(Decimal("1"))
