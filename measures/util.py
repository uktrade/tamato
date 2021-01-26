from typing import Union


def clean_duty_sentence(value: Union[str, int, float]) -> str:
    """Given a value, return a string representing a duty sentence
    taking into account that the value may be storing simple percentages
    as a number value."""
    if isinstance(value, float):
        # This is a percentage value that Excel has
        # represented as a number.
        return "{:.3%}".format(value)
    elif isinstance(value, int):
        return "{:d}%".format(value)
    else:
        # All other values will appear as text.
        return str(value)
