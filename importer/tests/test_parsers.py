import xml.etree.ElementTree as etree

import pytest

from importer.namespaces import Tag
from importer.parsers import BooleanElement
from importer.parsers import CompoundElement
from importer.parsers import ElementParser
from importer.parsers import TextElement
from importer.parsers import ValidityMixin


def test_element_parser_empty_element():
    parser = ElementParser(Tag(name="test"))
    parser.end(etree.Element(str(Tag(name="test")), {"value": "foo"}))
    assert parser.data == {"value": "foo"}


def test_element_parser_text_element():
    parser = ElementParser(Tag(name="test"))
    el = etree.Element(str(Tag(name="test")))
    el.text = "foo"
    parser.end(el)
    assert parser.text == "foo"


def test_text_element_class():
    parser = TextElement(Tag(name="test"))
    el = etree.Element(str(Tag(name="test")))
    el.text = "foo"
    parser.end(el)
    assert parser.data == "foo"


def test_element_parser_with_child():
    class TestElement(ElementParser):
        tag = Tag(name="test")
        foo = TextElement(Tag(name="foo"))

    parser = TestElement()

    el = etree.Element(str(Tag(name="test")))
    child = etree.Element(str(Tag(name="foo")))
    child.text = "bar"
    el.append(child)

    parser.start(el)
    parser.start(child)
    parser.end(child)
    parser.end(el)

    assert parser.data == {"foo": "bar"}


def test_element_parser_with_repeated_children():
    class Foo(ElementParser):
        tag = Tag(name="foo")

    class TestElement(ElementParser):
        tag = Tag(name="test")
        foo = Foo(many=True)

    parser = TestElement()

    el = etree.Element(str(Tag(name="test")))
    children = [etree.Element(str(Tag(name="foo")), {"id": i}) for i in range(3)]
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


def test_element_parser_with_grandchildren():
    class Grandchild(ElementParser):
        tag = Tag(name="grandchild")

    class Child(ElementParser):
        tag = Tag(name="child")
        grandchild = Grandchild(many=True)

    class TestElement(ElementParser):
        tag = Tag(name="test")
        child = Child(many=True)

    parser = TestElement()

    el = etree.Element(str(Tag(name="test")))
    child = etree.Element(str(Tag(name="child")))
    grandchild = etree.Element(str(Tag(name="grandchild")), {"id": "2"})

    child.extend([grandchild])
    el.extend([child])

    parser.start(el)
    parser.start(child)
    parser.start(grandchild)
    parser.end(grandchild)
    parser.end(child)
    parser.end(el)

    assert parser.data == {"child": [{"grandchild": [{"id": "2"}]}]}


def test_element_parser_with_two_levels_of_same_tag():
    class Grandchild(ElementParser):
        tag = Tag(name="child")

    class Child(ElementParser):
        tag = Tag(name="child")
        grandchild = Grandchild(many=True)

    class TestElement(ElementParser):
        tag = Tag(name="test")
        child = Child(many=True)

    parser = TestElement()

    el = etree.Element(str(Tag(name="test")))
    child = etree.Element(str(Tag(name="child")))
    grandchild = etree.Element(str(Tag(name="child")), {"id": "2"})

    child.extend([grandchild])
    el.extend([child])

    parser.start(el)
    parser.start(child)
    parser.start(grandchild)
    parser.end(grandchild)
    parser.end(child)
    parser.end(el)

    assert parser.data == {"child": [{"grandchild": [{"id": "2"}]}]}


def test_element_parser_with_partially_loaded_element():
    """
    If we use a streaming XML parser, the API will return start events for XML
    events before all/any of their children have been loaded.

    For this reason, we can't use any algorithm which looks at children as part
    of start events.
    """

    class Foo(ElementParser):
        tag = Tag(name="foo")

    class TestElement(ElementParser):
        tag = Tag(name="test")
        foo = Foo(many=True)

    parser = TestElement()

    el = etree.Element(str(Tag(name="test")))
    children = [etree.Element(str(Tag(name="foo")), {"id": str(i)}) for i in range(3)]

    parser.start(el)  # with no children
    for child in children:
        el.extend([child])
        parser.start(child)
        parser.end(child)
    parser.end(el)

    assert parser.data == {
        "foo": [
            {"id": "0"},
            {"id": "1"},
            {"id": "2"},
        ],
    }


def test_validity_mixin():
    class TestElement(ValidityMixin, ElementParser):
        tag = Tag(name="test")
        valid_between_lower = TextElement(Tag(name="validity.start.date"))
        valid_between_upper = TextElement(Tag(name="validity.end.date"))

    parser = TestElement()

    el = etree.Element(str(Tag(name="test")))
    start_date = etree.Element(str(Tag(name="validity.start.date")))
    start_date.text = "2020-01-01"
    end_date = etree.Element(str(Tag(name="validity.end.date")))
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


@pytest.mark.parametrize(
    ("true_value", "false_value", "text", "expected"),
    (
        ("1", "0", "1", True),
        ("1", "0", "0", False),
        ("Y", "N", "Y", True),
        ("Y", "N", "N", False),
        ("1", "0", "", None),
        ("1", "0", None, None),
        ("1", "0", "Y", None),
        ("1", "0", "N", None),
        ("1", "0", "00001", None),
        ("1", "0", "11111", None),
        ("1", "0", "10000", None),
    ),
)
def test_boolean_element_parser(true_value, false_value, text, expected):
    parser = BooleanElement(
        Tag(name="foo"),
        true_value=true_value,
        false_value=false_value,
    )

    el = etree.Element(str(Tag(name="foo")))
    el.text = text

    parser.start(el)
    parser.end(el)

    assert parser.data == expected


@pytest.mark.parametrize(
    ("num_children", "separator", "text", "expected"),
    (
        (0, "|", "foo", ("foo",)),
        (0, "|", "foo|bar", ("foo|bar",)),
        (1, "|", "foo", ("foo", None)),
        (1, "|", "foo|bar", ("foo", "bar")),
        (1, "|", "foo|bar|baz", ("foo", "bar|baz")),
        (2, "|", "foo", ("foo", None, None)),
        (2, "|", "foo|bar", ("foo", "bar", None)),
        (2, "|", "foo|bar|baz", ("foo", "bar", "baz")),
        (2, ";", "foo;bar;baz", ("foo", "bar", "baz")),
        (2, "|", "foo;bar;baz", ("foo;bar;baz", None, None)),
        (2, ";", "foo|bar|baz", ("foo|bar|baz", None, None)),
    ),
)
def test_compound_element_parser(num_children, separator, text, expected):
    parser = CompoundElement(
        Tag(name="foo"),
        *(str(i) for i in range(num_children)),
        separator=separator,
    )

    el = etree.Element(str(Tag(name="foo")))
    el.text = text

    parser.start(el)
    parser.end(el)

    assert parser.data == expected
