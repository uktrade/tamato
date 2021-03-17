import decimal
from math import floor
from typing import Union


def clean_duty_sentence(value: Union[str, int, float]) -> str:
    """Given a value, return a string representing a duty sentence taking into
    account that the value may be storing simple percentages as a number
    value."""
    if isinstance(value, float) or isinstance(value, int):
        # This is a percentage value that Excel has
        # represented as a number.
        decimal.getcontext().prec = 3
        decimal.getcontext().rounding = decimal.ROUND_DOWN
        return f"{decimal.Decimal(str(value)):.3%}"
    else:
        # All other values will appear as text.
        return str(value)


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
