import pytest

from common.tests import factories
from common.tests.util import validate_taric_xml

pytestmark = pytest.mark.django_db


@validate_taric_xml(factories.AdditionalCodeTypeFactory)
def test_additional_code_type_xml(api_client, taric_schema, approved_workbasket, xml):
    element = xml.find(".//additional.code.type", xml.nsmap)
    assert element is not None
    element = xml.find(".//additional.code.type.description", xml.nsmap)
    assert element is not None


@validate_taric_xml(factories.AdditionalCodeDescriptionFactory)
def test_additional_code_description_xml(
    api_client, taric_schema, approved_workbasket, xml
):
    element = xml.find(".//additional.code.description", xml.nsmap)
    assert element is not None
    element = xml.find(".//additional.code.description.period", xml.nsmap)
    assert element is not None


@validate_taric_xml(factories.AdditionalCodeFactory)
def test_additional_code_xml(api_client, taric_schema, approved_workbasket, xml):
    element = xml.find(".//additional.code", xml.nsmap)
    assert element is not None
