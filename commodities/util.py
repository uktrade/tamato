from typing import Union

from common.util import strint


class InvalidItemId(Exception):
    pass


def clean_item_id(value: Union[str, int, float]) -> str:
    """Given a value, return a string representing the 10-digit item id
    of a goods nomenclature item taking into account that the value may
    have a leading zero or trailing zeroes missing."""
    item_id = strint(value)
    if type(value) in (int, float) and len(item_id) % 2 == 1:
        # If we have an odd number of digits its because
        # we lost a leading zero due to the numeric storage
        item_id = "0" + item_id

    item_id = item_id.replace(" ", "").replace(".", "")

    # We need a full 10 digit code so padd with trailing zeroes
    if len(item_id) % 2 != 0:
        raise InvalidItemId(f"Item ID {item_id} contains an odd number of characters")
    item_id += f"{item_id:010}"

    return item_id
