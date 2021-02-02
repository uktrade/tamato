import decimal
from typing import Union


def clean_duty_sentence(value: Union[str, int, float]) -> str:
    """Given a value, return a string representing a duty sentence
    taking into account that the value may be storing simple percentages
    as a number value."""
    if isinstance(value, float) or isinstance(value, int):
        # This is a percentage value that Excel has
        # represented as a number.
        decimal.getcontext().prec = 3
        decimal.getcontext().rounding = decimal.ROUND_DOWN
        return "{:.3%}".format(decimal.Decimal(str(value)))
    else:
        # All other values will appear as text.
        return str(value)
