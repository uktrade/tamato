import decimal
from math import floor


def convert_eur_to_gbp(amount: str, eur_gbp_conversion_rate: float) -> str:
    """Convert EUR amount to GBP and round down to nearest pence."""
    converted_amount = (
        floor(
            int(
                decimal.Decimal(amount)
                * decimal.Decimal(eur_gbp_conversion_rate)
                * 100,
            ),
        )
        / 100
    )
    return f"{converted_amount:.3f}"
