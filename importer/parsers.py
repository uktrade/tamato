from __future__ import annotations

import logging
import xml.etree.ElementTree as etree
from typing import Any
from typing import Callable
from typing import Dict
from typing import Mapping
from typing import Optional
from xml.etree.ElementTree import Element

from common.validators import UpdateType
from importer.namespaces import Tag
from importer.nursery import get_nursery

logger = logging.getLogger(__name__)


class ParserError(Exception):
    pass


class InvalidDataError(Exception):
    pass


class ElementParser:
    """
    Base class for element specific parsers.

    ElementParser classes uses introspection to build a lookup table of child element
    parsers to their output JSON field name.

    This allows 2 options for adding child elements to a Parent element.

    Option 1:

    .. code:: python

        class ChildElement(ElementParser):
            tag = Tag("child", prefix="ns")
            field = TextElement("field")

        class ParentElement(ElementParser):
            tag = Tag("parent", prefix="ns")
            child = ChildElement()

    Option 2:

    .. code:: python

        class ParentElement(ElementParser):
            tag = Tag("parent", prefix="ns")


        @ParentElement.register_child("child")
        class ChildElement(ElementParser):
            tag = Tag("child", prefix="ns")
            some_field = TextElement("field")


    When handling XML such as:

    .. code:: xml

        <ns:parent>
            <ns:child id="2">
                <ns:field>Text</ns:field>
            </ns:child>
        </ns:parent>

    This class will build a JSON object in `self.data` with
    the following structure:

    .. code:: json

        {"child": {"id": 2, "field": "Text"}}
    """

    record_code: str
    """
    The type id of this model's type family in the TARIC specification.

    This number groups together a number of different models into 'records'.
    Where two models share a record code, they are conceptually expressing
    different properties of the same logical model.

    In theory each :class:`~common.transactions.Transaction` should only contain
    models with a single :attr:`record_code` (but differing
    :attr:`subrecord_code`.)
    """

    subrecord_code: str
    """
    The type id of this model in the TARIC specification. The
    :attr:`subrecord_code` when combined with the :attr:`record_code` uniquely
    identifies the type within the specification.

    The subrecord code gives the intended order for models in a transaction,
    with comparatively smaller subrecord codes needing to come before larger
    ones.
    """

    tag: Optional[Tag] = None
    data_class: type = dict
    end_hook: Optional[Callable[[Any, Element], None]] = None

    def __init__(self, tag: Tag = None, many: bool = False, depth: int = 1):
        self.child = None
        self.parent: Optional[ElementParser] = None
        self.data = self.data_class()
        self.depth = depth
        self.many = many
        self.parent = None
        self.text = None
        self.started = False

        if tag:
            self.tag = tag

    @property
    def _field_lookup(self) -> Dict[ElementParser, str]:
        field_lookup = {
            parser: field
            for field, parser in self.__class__.__dict__.items()
            if isinstance(parser, ElementParser)
        }

        field_lookup.update(getattr(self, "_additional_components", {}))
        return field_lookup

    def is_parser_for_element(
        self,
        parser: ElementParser,
        element: etree.Element,
    ) -> bool:
        """Check if the parser matches the element."""
        return parser.tag == element.tag

    def get_parser(self, element: etree.Element) -> Optional[ElementParser]:
        for parser in self._field_lookup.keys():
            if self.is_parser_for_element(parser, element):
                return parser

    def start(self, element: etree.Element, parent: ElementParser = None):
        """
        Handle the start of an XML tag. The tag may not yet have all of its
        children.

        We have a few cases where there are tags nested within a tag of the same name.

        Example:

        .. code:: xml

            <oub:additional.code>
                <oub:additional.code.sid>00000001</oub:additional.code.sid>
                <oub:additional.code.type.id>A</oub:additional.code.type.id>
                <oub:additional.code>AAA</oub:additional.code>
                <oub:validity.start.date>2021-01-01</oub:validity.start.date>
            </oub:additional.code>

        In this case matching on tags is not enough and so we also need to keep
        track of whether this parser is already parsing an element. If it is, we
        don't want to select any child parsers. If it is not, we know that this
        is an element that this parser should be parsing.
        """

        self.parent = parent
        if not self.started:
            self.data = self.data_class()
            self.started = True
        else:
            # if the tag matches one of the child elements of this element, get the
            # parser for that element
            if not self.child:
                self.child = self.get_parser(element)

        # if currently in a child element, delegate to the child parser
        if self.child:
            self.child.start(element, self)

    def end(self, element: etree.Element):
        # if currently in a child element, delegate to the child parser
        if self.child:
            self.child.end(element)

            # leaving the child element, so stop delegating
            if not self.child.started and self.is_parser_for_element(
                self.child,
                element,
            ):
                field_name = self._field_lookup[self.child]
                if self.child.many:
                    self.data.setdefault(field_name, []).append(self.child.data)
                else:
                    self.data[field_name] = self.child.data
                self.child = None

        # leaving this element, so marshal the data
        elif self.is_parser_for_element(self, element):
            if element.text:
                self.text = element.text.strip()
            self.data.update(element.attrib.items())
            if callable(self.end_hook):
                self.end_hook(self.data, element)
            self.started = False
            self.clean()
            self.validate()

    def clean(self):
        """Clean up data."""

    def validate(self):
        """Validate data."""

    @classmethod
    def register_child(cls, name, *args, **kwargs):
        if not hasattr(cls, "_additional_components"):
            cls._additional_components = {}

        def wraps(parser):
            cls._additional_components[parser(*args, **kwargs)] = name
            return parser

        return wraps


class ValueElementMixin:
    """Provides a convenient way to define a parser for elements that contain
    only a text value and have no attributes or children."""

    native_type: type
    """The Python type that most closely matches the type of the XML element."""

    def clean(self):
        super().clean()
        self.data = self.native_type(self.text)


class ConstantElement(ValueElementMixin, ElementParser):
    """
    Represents an element that is always a constant value in the XML.

    The actual value is ignored and not put into the database. The value
    specified in the constructor will be put back into the XML.
    """

    def __init__(
        self,
        tag: Tag,
        value: str,  # pylint: disable=unused-argument
    ) -> None:
        super().__init__(tag)

    def clean(self):
        pass


class TextElement(ValueElementMixin, ElementParser):
    """
    Represents an element which contains a text value.

    .. code-block:: XML

        <msg:record.code>Example Text</msg:record.code>
    """

    native_type = str


class IntElement(ValueElementMixin, ElementParser):
    """
    Represents an element which contains an integer value.

    .. code-block:: XML

        <msg:record.code>430</msg:record.code>
    """

    native_type = int

    def __init__(
        self,
        *args,
        format: str = "FM99999999999999999999",  # pylint: disable=unused-argument
    ):
        super().__init__(*args)


class BooleanElement(ValueElementMixin, ElementParser):
    """
    Represents an element which contains a true or false value.

    The actual value in the XML by default is assumed to be a 1 for True and a 0
    for False. This can be customised by passing in different values.

    .. code-block:: XML

        <msg:some.value>1</msg:some.value>
        <msg:some.value>0</msg:some.value>
    """

    native_type = bool

    def __init__(self, *args, true_value: str = "1", false_value: str = "0", **kwargs):
        self.true_value = true_value
        self.false_value = false_value
        super().__init__(*args, **kwargs)

    def clean(self):
        if self.text == self.true_value:
            self.data = True
        elif self.text == self.false_value:
            self.data = False
        else:
            self.data = None


class RangeLowerElement(TextElement):
    """Represents an element that is the lower part of a range."""


class RangeUpperElement(TextElement):
    """Represents an element that is the upper part of a range."""


class CompoundElement(ValueElementMixin, ElementParser):
    """
    Represents an element in XML that is actually a concatenation of one or more
    logical values and separators.

    The separator by default is assumed to be a pipe character. The parsed data
    will always contain a tuple that is the size of the number of expected
    fields (the original field and any extras) – if less than the specified
    number of separators occur the rightmost fields will have value ``None``.

    .. code-block:: XML

        <msg:some.value>one|two|three</msg:some.value>
    """

    native_type = tuple

    def __init__(
        self,
        tag: Tag,
        *extra_fields: str,
        separator: str = "|",
    ):
        super().__init__(tag)
        self.extra_fields = extra_fields
        self.separator = separator

    def clean(self):
        parts = self.text.split(self.separator, len(self.extra_fields))
        missing = len(self.extra_fields) - len(parts) + 1
        self.data = self.native_type([*parts, *([None] * missing)])


class ValidityMixin:
    """Parse validity start and end dates."""

    valid_between_lower = RangeLowerElement(Tag("validity.start.date"))
    valid_between_upper = RangeUpperElement(Tag("validity.end.date"))

    def clean(self):
        super().clean()
        valid_between = {}

        if "valid_between_lower" in self.data:
            valid_between["lower"] = self.data.pop("valid_between_lower")

        if "valid_between_upper" in self.data:
            valid_between["upper"] = self.data.pop("valid_between_upper")

        if valid_between:
            self.data["valid_between"] = valid_between


class ValidityStartMixin:
    """Parse validity start date."""

    validity_start = TextElement(Tag("validity.start.date"))


class Writable:
    """
    A parser which implements the Writable interface can write its changes to
    the database.

    Not all TARIC3 elements correspond to database entities (particularly simple
    text elements, but also envelopes and app.messages).
    """

    nursery = get_nursery()

    def create(self, data: Mapping[str, Any], transaction_id: int):
        """Preps the given data as a create record and submits it to the nursery
        for processing."""
        data.update(update_type=UpdateType.CREATE)

        dispatch_object = {
            "data": data,
            "tag": self.tag.name,
            "transaction_id": transaction_id,
        }

        self.nursery.submit(dispatch_object)

    def update(self, data: Mapping[str, Any], transaction_id: int):
        """Update a DB record with provided data."""
        data.update(update_type=UpdateType.UPDATE.value)

        dispatch_object = {
            "data": data,
            "tag": self.tag.name,
            "transaction_id": transaction_id,
        }

        self.nursery.submit(dispatch_object)

    def delete(self, data: Mapping[str, Any], transaction_id: int):
        """Delete a DB record with provided data."""
        data.update(update_type=UpdateType.DELETE.value)

        dispatch_object = {
            "data": data,
            "tag": self.tag.name,
            "transaction_id": transaction_id,
        }

        self.nursery.submit(dispatch_object)
