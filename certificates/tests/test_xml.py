import pytest

from common.tests import factories
from common.tests.util import validate_taric_xml
from common.xml.namespaces import nsmap

pytestmark = pytest.mark.django_db


@validate_taric_xml(factories.CertificateTypeFactory)
def test_certificate_type_xml(xml):
    element = xml.find(".//oub:certificate.type", nsmap)
    assert element is not None
    element = xml.find(".//oub:certificate.type.description", nsmap)
    assert element is not None


@validate_taric_xml(factories.CertificateDescriptionFactory)
def test_certificate_description_xml(xml):
    element = xml.find(".//oub:certificate.description", nsmap)
    assert element is not None
    element = xml.find(".//oub:certificate.description.period", nsmap)
    assert element is not None


@validate_taric_xml(factories.CertificateFactory)
def test_certificate_xml(xml):
    element = xml.find(".//oub:certificate", nsmap)
    assert element is not None
