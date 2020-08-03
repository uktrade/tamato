import xml.etree.ElementTree as etree
from typing import Optional

from importer.namespaces import Tag


class HandlerError(Exception):
    pass


class ElementHandler:
    """Base class for element specific handlers.

    ElementHandler classes uses introspection to build a lookup table of child element
    handlers to their output JSON field name.

    This allows 2 options for adding child elements to a Parent element.

    Option 1:

        class ChildElement(ElementHandler):
            tag = Tag("child", prefix="ns")
            field = TextElement("field")

        class ParentElement(ElementHandler):
            tag = Tag("parent", prefix="ns")
            child = ChildElement()

    Option 2:

        class ParentElement(ElementHandler):
            tag = Tag("parent", prefix="ns")


        @ParentElement.register_child("child")
        class ChildElement(ElementHandler):
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
        self._field_lookup = {}
        self.data = {}
        self.text = None
        self.many = many

        if tag:
            self.tag = tag

        for field, handler in self.__class__.__dict__.items():
            if isinstance(handler, ElementHandler):
                self._field_lookup[handler] = field

        self._field_lookup.update(getattr(self, "_additional_components", {}))

    def get_handler(self, element: etree.Element) -> Optional["ElementHandler"]:
        for handler in self._field_lookup.keys():
            if handler.tag == element.tag:
                return handler

    def start(self, element: etree.Element):
        if element.tag == self.tag:
            self.data = {}

        # if the tag matches one of the child elements of this element, get the
        # handler for that element
        if not self.child:
            self.child = self.get_handler(element)

        # if currently in a child element, delegate to the child handler
        if self.child:
            self.child.start(element)

    def end(self, element: etree.Element):
        # if currently in a child element, delegate to the child handler
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
    def register_child(cls, name):
        if not hasattr(cls, "_additional_components"):
            cls._additional_components = {}

        def wraps(handler):
            cls._additional_components[handler] = name
            return handler

        return wraps


class TextElement(ElementHandler):
    """Handle elements which contain a text value.

    This class provides a convenient way to define a handler for elements that contain
    only a text value and have no attributes or children, eg:

        <msg:record.code>430</msg:record.code>

    """

    def clean(self):
        super().clean()
        self.data = self.text


class ValidityMixin:
    """Handle validity start and end dates"""

    def clean(self):
        super().clean()
        self.data["valid_between"] = {
            "lower": self.data.pop("valid_between_lower", None),
            "upper": self.data.pop("valid_between_upper", None),
        }


class Writable:
    """A Handler which implements the Writable interface can write its changes to the
    database.

    Not all TARIC3 elements correspond to database entities (particularly simple text
    elements, but also envelopes and app.messages).
    """

    def create(self, data, workbasket_id):
        """Create a DB record with provided data"""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement `create` method"
        )

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
