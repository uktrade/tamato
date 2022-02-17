import pytest

from common.tests import factories
from common.tests.util import validate_taric_xml
from common.xml.namespaces import nsmap

pytestmark = pytest.mark.django_db


@validate_taric_xml(factories.RegulationGroupFactory)
def test_group_xml(xml):
    assert xml.xpath(".//oub:regulation.group", namespaces=nsmap)


@validate_taric_xml(factories.RegulationFactory)
def test_regulation_xml(xml):
    assert xml.xpath(".//oub:base.regulation", namespaces=nsmap)


@validate_taric_xml(factories.RegulationFactory)
def test_information_text_contains_url_and_public_id(xml):
    text = xml.xpath(".//oub:information.text", namespaces=nsmap)[0].text
    assert "|" in text
    assert "https://" in text
    assert "S.I." in text


@validate_taric_xml(factories.AmendmentFactory)
def test_amendment_xml(xml):
    assert xml.xpath(".//oub:modification.regulation", namespaces=nsmap)


@validate_taric_xml(factories.SuspensionFactory)
def test_suspension_xml(xml):
    assert xml.xpath(".//oub:full.temporary.stop.regulation", namespaces=nsmap)
    assert xml.xpath(".//oub:fts.regulation.action", namespaces=nsmap)


@validate_taric_xml(factories.ReplacementFactory)
def test_replacement_xml(xml):
    assert xml.xpath(".//oub:regulation.replacement", namespaces=nsmap)
