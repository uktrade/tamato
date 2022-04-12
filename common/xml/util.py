import contextlib
import logging
import re
from typing import Collection
from xml.etree import ElementTree

from common.validators import UpdateType
from common.xml.namespaces import nsmap


@contextlib.contextmanager
def rewrite(filename: str):
    """Opens the passed XML file and yields the parsed XML tree for
    modification, and then overwrite the original file with the modified tree
    afterwards."""

    with open(filename, "rb") as file:
        tree = ElementTree.parse(file)
        root = tree.getroot()
        yield root

    tree.write(filename, "utf-8", True)


ATTRIBUTE_XPATH = re.compile(r"\[@([a-z]+)\]")


def renumber_paths(element: ElementTree.Element, start_from: int, *paths: str):
    """
    Re-numbers the integer values contained in XML attributes or text values to
    start from a new value.

    Differences between values are retained, so that if an XML tree contains a
    sequence of values the sequence will still exist but will just have been
    shifted to start at the new starting value. The values are expected to be in
    order within the file, i.e. the smallest value should appear first.

    Attributes or tags are identified using XPath strings. If the XPath string
    contains an attribute declaration, that attribute is what will be updated.
    Otherwise, the XML tag's text content will be updated. In both cases, there
    is expected to be an original value.

    Multiple paths can be used, allowing multiple text values and attributes to
    be updated at once.

    Example input:

        <root>
            <element id="123"/>
            <something>124</something>
        </root>

    Calling ``renumber(input, 456, "element[@id]", "something")`` results in:

        <root>
            <element id="456"/>
            <sometihng>457</something>
        </root>
    """
    add_value = None
    for path in paths:
        result = ATTRIBUTE_XPATH.search(path)
        if result:
            # We are updating an XML attribute.
            attribute = result.groups()[0]
            getter = lambda e: int(e.get(attribute))
            setter = lambda e, v: e.set(attribute, str(v))
        else:
            # We are updating the body of an XML element.
            getter = lambda e: int(getattr(e, "text"))
            setter = lambda e, v: setattr(e, "text", str(v))

        if not add_value:
            first_tag = element.find(path, nsmap)
            first_value = int(getter(first_tag))
            add_value = start_from - first_value

        for tag in element.findall(path, nsmap):
            value = int(getter(tag))
            setter(tag, str(value + add_value))


def renumber_transactions(envelope: ElementTree.Element, start_from: int):
    """Renumbers transactions in the passed TARIC XML file to start from the
    specified value."""
    renumber_paths(
        envelope,
        start_from,
        ".//oub:transaction.id",
        ".//env:transaction[@id]",
    )


def renumber_records(envelope: ElementTree.Element, start_from: int, record_name: str):
    """
    Renumbers the integer values found in TARIC XML records matching paths with
    numbers that start from the passed integer.

    Any records that are CREATEd will receive a new value. Any values that are
    UPDATEd or DELETEd will only receive a new value if they were CREATEd in
    this file.
    """
    logger = logging.getLogger(__name__)
    add_value = None
    remaps = dict()

    def get(element: ElementTree.Element) -> int:
        return int(element.text)

    def set(element: ElementTree.Element, value: int):
        element.text = str(value)

    for transaction in envelope.findall(".//env:transaction", nsmap):
        for record in transaction.findall(".//oub:record", nsmap):
            update_type = get(record.find(".//oub:update.type", namespaces=nsmap))

            for tag in record.findall(f".//{record_name}", nsmap):
                current_value = get(tag)

                if update_type == UpdateType.CREATE:
                    if not add_value:
                        add_value = start_from - current_value

                    remaps[current_value] = current_value + add_value

                if current_value in remaps:
                    set(tag, remaps[current_value])

    logger.debug("Renumbered %d distinct values of %s", len(remaps), record_name)


def element_contains(
    haystack: ElementTree.Element,
    needle_name: str,
    needle_values: Collection[str],
) -> bool:
    """Returns whether the passed element contains a descendent element matching
    the passed tag name which has any of passed text values."""

    for tag in haystack.findall(f".//{needle_name}", nsmap):
        if tag.text in needle_values:
            return True

    return False


def remove_transactions(
    envelope: ElementTree.Element,
    element_name: str,
    element_values: Collection[str],
):
    """
    Removes transactions from the passed TARIC XML tree where the passed tag
    name is present and has the passed value.

    For example, calling ``filter_taric(root, "oub:measure.sid", "12345678",
    "23456789")`` will remove any transaction containing any reference to a
    measure SID 12345678 or 23456789. This might be the measure itself or it
    might also include any conditions or components that reference the measure.
    """
    logger = logging.getLogger(__name__)

    for transaction in envelope.findall("./env:transaction", nsmap):
        if element_contains(transaction, element_name, element_values):
            logger.debug("Removing transaction", transaction.attrib["id"])
            envelope.remove(transaction)
