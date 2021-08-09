import pytest

from common.tests import factories
from common.tests.util import validate_taric_xml
from common.xml.namespaces import nsmap

pytestmark = pytest.mark.django_db


@validate_taric_xml(factories.RegulationGroupFactory)
def test_group_xml(xml):
    assert xml.find(".//oub:regulation.group", nsmap) is not None


@validate_taric_xml(factories.RegulationFactory)
def test_regulation_xml(xml):
    assert xml.find(".//oub:base.regulation", nsmap) is not None


@validate_taric_xml(factories.RegulationFactory)
def test_information_text_contains_url_and_public_id(xml):
    text = xml.findtext(".//oub:information.text", namespaces=nsmap)
    assert "|" in text
    assert "https://" in text
    assert "S.I." in text


@validate_taric_xml(factories.AmendmentFactory)
def test_amendment_xml(xml):
    assert xml.find(".//oub:modification.regulation", nsmap) is not None


@validate_taric_xml(factories.SuspensionFactory)
def test_suspension_xml(xml):
    assert xml.find(".//oub:full.temporary.stop.regulation", nsmap) is not None
    assert xml.find(".//oub:fts.regulation.action", nsmap) is not None


@validate_taric_xml(factories.ReplacementFactory)
def test_replacement_xml(xml):
    assert xml.find(".//oub:regulation.replacement", nsmap) is not None
