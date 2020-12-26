import pytest

from common.tests import factories
from common.tests.util import validate_taric_xml

pytestmark = pytest.mark.django_db


@validate_taric_xml(factories.CertificateTypeFactory)
def test_certificate_type_xml(api_client, taric_schema, approved_transaction, xml):
    element = xml.find(".//certificate.type", xml.nsmap)
    assert element is not None
    element = xml.find(".//certificate.type.description", xml.nsmap)
    assert element is not None


@validate_taric_xml(factories.CertificateDescriptionFactory)
def test_certificate_description_xml(
    api_client, taric_schema, approved_transaction, xml
):
    element = xml.find(".//certificate.description", xml.nsmap)
    assert element is not None
    element = xml.find(".//certificate.description.period", xml.nsmap)
    assert element is not None


@validate_taric_xml(factories.CertificateFactory)
def test_certificate_xml(api_client, taric_schema, approved_transaction, xml):
    element = xml.find(".//certificate", xml.nsmap)
    assert element is not None
