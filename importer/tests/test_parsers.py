import xml.etree.ElementTree as etree

from importer.namespaces import Tag
from importer.parsers import ElementParser
from importer.parsers import TextElement
from importer.parsers import ValidityMixin


def test_element_parser_empty_element():
    parser = ElementParser(Tag("test"))
    parser.end(etree.Element(str(Tag("test")), {"value": "foo"}))
    assert parser.data == {"value": "foo"}


def test_element_parser_text_element():
    parser = ElementParser(Tag("test"))
    el = etree.Element(str(Tag("test")))
    el.text = "foo"
    parser.end(el)
    assert parser.text == "foo"


def test_text_element_class():
    parser = TextElement(Tag("test"))
    el = etree.Element(str(Tag("test")))
    el.text = "foo"
    parser.end(el)
    assert parser.data == "foo"


def test_element_parser_with_child():
    class TestElement(ElementParser):
        tag = Tag("test")
        foo = TextElement(Tag("foo"))

    parser = TestElement()

    el = etree.Element(str(Tag("test")))
    child = etree.Element(str(Tag("foo")))
    child.text = "bar"
    el.append(child)

    parser.start(el)
    parser.start(child)
    parser.end(child)
    parser.end(el)

    assert parser.data == {"foo": "bar"}


def test_element_parser_with_repeated_children():
    class Foo(ElementParser):
        tag = Tag("foo")

    class TestElement(ElementParser):
        tag = Tag("test")
        foo = Foo(many=True)

    parser = TestElement()

    el = etree.Element(str(Tag("test")))
    children = [etree.Element(str(Tag("foo")), {"id": i}) for i in range(3)]
    el.extend(children)

    parser.start(el)
    for child in children:
        parser.start(child)
        parser.end(child)
    parser.end(el)

    assert parser.data == {
        "foo": [
            {"id": 0},
            {"id": 1},
            {"id": 2},
        ],
    }


def test_validity_mixin():
    class TestElement(ValidityMixin, ElementParser):
        tag = Tag("test")
        valid_between_lower = TextElement(Tag("validity.start.date"))
        valid_between_upper = TextElement(Tag("validity.end.date"))

    parser = TestElement()

    el = etree.Element(str(Tag("test")))
    start_date = etree.Element(str(Tag("validity.start.date")))
    start_date.text = "2020-01-01"
    end_date = etree.Element(str(Tag("validity.end.date")))
    end_date.text = "2020-01-02"
    el.extend([start_date, end_date])

    parser.start(el)
    for child in el:
        parser.start(child)
        parser.end(child)
    parser.end(el)

    assert parser.data == {
        "valid_between": {
            "lower": "2020-01-01",
            "upper": "2020-01-02",
        },
    }
