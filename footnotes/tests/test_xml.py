import pytest

from common.tests import factories
from common.tests.util import validate_taric_xml
from common.xml.namespaces import nsmap

pytestmark = pytest.mark.django_db


@validate_taric_xml(factories.FootnoteTypeFactory)
def test_footnote_type_xml(xml):
    element = xml.find(".//oub:footnote.type", nsmap)
    assert element is not None
    element = xml.find(".//oub:footnote.type.description", nsmap)
    assert element is not None


@validate_taric_xml(factories.FootnoteFactory)
def test_footnote_xml(xml):
    element = xml.find(".//oub:footnote", nsmap)
    assert element is not None


@validate_taric_xml(factories.FootnoteDescriptionFactory)
def test_footnote_description_xml(xml):
    element = xml.find(".//oub:footnote.description.period", nsmap)
    assert element is not None
    element = xml.find(".//oub:footnote.description", nsmap)
    assert element is not None
