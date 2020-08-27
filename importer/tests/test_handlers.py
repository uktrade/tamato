import xml.etree.ElementTree as etree

from importer.handlers import ElementHandler
from importer.handlers import TextElement
from importer.handlers import ValidityMixin
from importer.namespaces import Tag


def test_element_handler_empty_element():
    handler = ElementHandler(Tag("test"))
    handler.end(etree.Element(str(Tag("test")), {"value": "foo"}))
    assert handler.data == {"value": "foo"}


def test_element_handler_text_element():
    handler = ElementHandler(Tag("test"))
    el = etree.Element(str(Tag("test")))
    el.text = "foo"
    handler.end(el)
    assert handler.text == "foo"


def test_text_element_class():
    handler = TextElement(Tag("test"))
    el = etree.Element(str(Tag("test")))
    el.text = "foo"
    handler.end(el)
    assert handler.data == "foo"


def test_element_handler_with_child():
    class TestElement(ElementHandler):
        tag = Tag("test")
        foo = TextElement(Tag("foo"))

    handler = TestElement()

    el = etree.Element(str(Tag("test")))
    child = etree.Element(str(Tag("foo")))
    child.text = "bar"
    el.append(child)

    handler.start(el)
    handler.start(child)
    handler.end(child)
    handler.end(el)

    assert handler.data == {"foo": "bar"}


def test_element_handler_with_repeated_children():
    class Foo(ElementHandler):
        tag = Tag("foo")

    class TestElement(ElementHandler):
        tag = Tag("test")
        foo = Foo(many=True)

    handler = TestElement()

    el = etree.Element(str(Tag("test")))
    children = [etree.Element(str(Tag("foo")), {"id": i}) for i in range(3)]
    el.extend(children)

    handler.start(el)
    for child in children:
        handler.start(child)
        handler.end(child)
    handler.end(el)

    assert handler.data == {
        "foo": [
            {"id": 0},
            {"id": 1},
            {"id": 2},
        ],
    }


def test_validity_mixin():
    class TestElement(ValidityMixin, ElementHandler):
        tag = Tag("test")
        valid_between_lower = TextElement(Tag("validity.start.date"))
        valid_between_upper = TextElement(Tag("validity.end.date"))

    handler = TestElement()

    el = etree.Element(str(Tag("test")))
    start_date = etree.Element(str(Tag("validity.start.date")))
    start_date.text = "2020-01-01"
    end_date = etree.Element(str(Tag("validity.end.date")))
    end_date.text = "2020-01-02"
    el.extend([start_date, end_date])

    handler.start(el)
    for child in el:
        handler.start(child)
        handler.end(child)
    handler.end(el)

    assert handler.data == {
        "valid_between": {
            "lower": "2020-01-01",
            "upper": "2020-01-02",
        },
    }
