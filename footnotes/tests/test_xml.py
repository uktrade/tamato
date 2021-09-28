import pytest

from common.tests import factories
from common.tests.util import validate_taric_xml
from common.xml.namespaces import nsmap

pytestmark = pytest.mark.django_db


@validate_taric_xml(factories.FootnoteTypeFactory)
def test_footnote_type_xml(xml):
    assert xml.xpath(".//oub:footnote.type", namespaces=nsmap)
    assert xml.xpath(".//oub:footnote.type.description", namespaces=nsmap)


@validate_taric_xml(factories.FootnoteFactory)
def test_footnote_xml(xml):
    assert xml.xpath(".//oub:footnote", namespaces=nsmap)


@validate_taric_xml(factories.FootnoteDescriptionFactory)
def test_footnote_description_xml(xml):
    assert xml.xpath(".//oub:footnote.description.period", namespaces=nsmap)
    assert xml.xpath(".//oub:footnote.description", namespaces=nsmap)
