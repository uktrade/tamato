import pytest

from common.tests import factories
from common.tests.util import validate_taric_xml

pytestmark = pytest.mark.django_db


@validate_taric_xml(factories.RegulationFactory)
def test_regulation_xml(api_client, taric_schema, approved_workbasket, xml):
    element = xml.find(".//base.regulation", xml.nsmap)
    assert element is not None


@validate_taric_xml(factories.RegulationFactory)
def test_information_text_contains_url_and_public_id(api, schema, workbasket, xml):
    text = xml.findtext(".//information.text", namespaces=xml.nsmap)
    assert "|" in text
    assert "https://" in text
    assert "S.I." in text
