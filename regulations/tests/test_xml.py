import pytest

from common.tests import factories
from common.tests.util import validate_taric_xml
from common.xml.namespaces import nsmap

pytestmark = pytest.mark.django_db


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
