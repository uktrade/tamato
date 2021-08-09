import pytest

from common.tests import factories
from common.tests.util import validate_taric_xml
from common.xml.namespaces import nsmap

pytestmark = pytest.mark.django_db


@validate_taric_xml(factories.RegulationGroupFactory)
def test_group_xml(xml):
    element = xml.find(".//oub:regulation.group", nsmap)
    assert element is not None


@validate_taric_xml(factories.RegulationFactory)
def test_regulation_xml(xml):
    element = xml.find(".//oub:base.regulation", nsmap)
    assert element is not None


@validate_taric_xml(factories.RegulationFactory)
def test_information_text_contains_url_and_public_id(xml):
    text = xml.findtext(".//oub:information.text", namespaces=nsmap)
    assert "|" in text
    assert "https://" in text
    assert "S.I." in text


@validate_taric_xml(factories.AmendmentFactory)
def test_amendment_xml(xml):
    element = xml.find(".//oub:modification.regulation", nsmap)
    assert element is not None


@validate_taric_xml(factories.SuspensionFactory)
def test_suspension_xml(xml):
    element = xml.find(".//oub:full.temporary.stop.regulation", nsmap)
    assert element is not None
    element = xml.find(".//oub:fts.regulation.action", nsmap)
    assert element is not None


@validate_taric_xml(factories.ReplacementFactory)
def test_replacement_xml(xml):
    element = xml.find(".//oub:regulation.replacement", nsmap)
    assert element is not None
