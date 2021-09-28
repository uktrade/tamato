import pytest

from common.tests import factories
from common.tests.util import validate_taric_xml
from common.xml.namespaces import nsmap

pytestmark = pytest.mark.django_db


@validate_taric_xml(factories.AdditionalCodeTypeFactory)
def test_additional_code_type_xml(xml):
    assert xml.xpath(".//oub:additional.code.type", namespaces=nsmap)
    assert xml.xpath(".//oub:additional.code.type.description", namespaces=nsmap)


@validate_taric_xml(factories.AdditionalCodeDescriptionFactory)
def test_additional_code_description_xml(xml):
    assert xml.xpath(".//oub:additional.code.description", namespaces=nsmap)
    assert xml.xpath(".//oub:additional.code.description.period", namespaces=nsmap)


@validate_taric_xml(factories.AdditionalCodeFactory)
def test_additional_code_xml(xml):
    assert xml.xpath(".//oub:additional.code", namespaces=nsmap)
