import pytest

from common.tests import factories
from common.tests.util import validate_taric_xml
from common.xml.namespaces import nsmap

pytestmark = pytest.mark.django_db


@validate_taric_xml(factories.AdditionalCodeTypeFactory)
def test_additional_code_type_xml(xml):
    element = xml.find(".//oub:additional.code.type", nsmap)
    assert element is not None
    element = xml.find(".//oub:additional.code.type.description", nsmap)
    assert element is not None


@validate_taric_xml(factories.AdditionalCodeDescriptionFactory)
def test_additional_code_description_xml(xml):
    element = xml.find(".//oub:additional.code.description", nsmap)
    assert element is not None
    element = xml.find(".//oub:additional.code.description.period", nsmap)
    assert element is not None


@validate_taric_xml(factories.AdditionalCodeFactory)
def test_additional_code_xml(xml):
    element = xml.find(".//oub:additional.code", nsmap)
    assert element is not None
