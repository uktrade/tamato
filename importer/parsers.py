import logging
import xml.etree.ElementTree as etree
from typing import Optional

from common.validators import UpdateType
from importer.namespaces import Tag
from importer.nursery import get_nursery

logger = logging.getLogger(__name__)


class ParserError(Exception):
    pass


class ElementParser:
    """Base class for element specific parsers.

    ElementParser classes uses introspection to build a lookup table of child element
    parsers to their output JSON field name.

    This allows 2 options for adding child elements to a Parent element.

    Option 1:

        class ChildElement(ElementParser):
            tag = Tag("child", prefix="ns")
            field = TextElement("field")

        class ParentElement(ElementParser):
            tag = Tag("parent", prefix="ns")
            child = ChildElement()

    Option 2:

        class ParentElement(ElementParser):
            tag = Tag("parent", prefix="ns")


        @ParentElement.register_child("child")
        class ChildElement(ElementParser):
            tag = Tag("child", prefix="ns")
            some_field = TextElement("field")


    When handling XML such as:

        <ns:parent><ns:child id="2"><ns:field>Text</ns:field></ns:child></ns:parent>

    This class will build a JSON object in `self.data` with
    the following structure:

        {"child": {"id": 2, "field": "Text"}}

    """

    tag: Tag = None

    def __init__(self, tag: Tag = None, many: bool = False):
        self.child = None
        self.parent = None
        self.data = {}
        self.text = None
        self.many = many

        if tag:
            self.tag = tag

    @property
    def _field_lookup(self) -> dict:
        field_lookup = {
            parser: field
            for field, parser in self.__class__.__dict__.items()
            if isinstance(parser, ElementParser)
        }

        field_lookup.update(getattr(self, "_additional_components", {}))
        return field_lookup

    def get_parser(self, element: etree.Element) -> Optional["ElementParser"]:
        for parser in self._field_lookup.keys():
            if parser.tag == element.tag:
                return parser

    def start(self, element: etree.Element, parent=None):
        self.parent = parent

        if element.tag == self.tag:
            self.data = {}

        # if the tag matches one of the child elements of this element, get the
        # parser for that element
        if not self.child:
            self.child = self.get_parser(element)

        # if currently in a child element, delegate to the child parser
        if self.child:
            self.child.start(element, parent=self)

    def end(self, element: etree.Element):
        # if currently in a child element, delegate to the child parser
        if self.child:
            self.child.end(element)

            # leaving the child element, so stop delegating
            if element.tag == self.child.tag:
                field_name = self._field_lookup[self.child]
                if self.child.many:
                    self.data.setdefault(field_name, []).append(self.child.data)
                else:
                    self.data[field_name] = self.child.data
                self.child = None

        # leaving this element, so marshal the data
        if element.tag == self.tag:
            if element.text:
                self.text = element.text.strip()
            self.data.update(element.attrib.items())
            self.clean()
            self.validate()

    def clean(self):
        """Clean up data"""
        pass

    def validate(self):
        """Validate data"""
        pass

    @classmethod
    def register_child(cls, name, *args, **kwargs):
        if not hasattr(cls, "_additional_components"):
            cls._additional_components = {}

        def wraps(parser):
            cls._additional_components[parser(*args, **kwargs)] = name
            return parser

        return wraps


class TextElement(ElementParser):
    """Parse elements which contain a text value.

    This class provides a convenient way to define a parser for elements that contain
    only a text value and have no attributes or children, eg:

        <msg:record.code>430</msg:record.code>

    """

    def clean(self):
        super().clean()
        self.data = self.text


class ValidityMixin:
    """Parse validity start and end dates"""

    _additional_components = {
        TextElement(Tag("validity.start.date")): "valid_between_lower",
        TextElement(Tag("validity.end.date")): "valid_between_upper",
    }

    def clean(self):
        super().clean()
        valid_between = {}

        if "valid_between_lower" in self.data:
            valid_between["lower"] = self.data.pop("valid_between_lower")

        if "valid_between_upper" in self.data:
            valid_between["upper"] = self.data.pop("valid_between_upper")

        if valid_between:
            self.data["valid_between"] = valid_between


class Writable:
    """A parser which implements the Writable interface can write its changes to the
    database.

    Not all TARIC3 elements correspond to database entities (particularly simple text
    elements, but also envelopes and app.messages).
    """

    nursery = get_nursery()

    def create(self, data, workbasket_id):
        """
        Preps the given data as a create record and submits it to the nursery for processing.
        """
        data.update(update_type=UpdateType.CREATE.value)

        dispatch_object = {
            "data": data,
            "tag": self.tag.name,
            "workbasket_id": workbasket_id,
        }
        self.nursery.submit(dispatch_object)

    def update(self, data, workbasket_id):
        """Update a DB record with provided data"""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement `update` method"
        )

    def delete(self, data, workbasket_id):
        """Delete a DB record with provided data"""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement `delete` method"
        )
