import pytest

from common.tests import factories

pytestmark = pytest.mark.django_db


def test_certificate_type_importer(imported_fields_match):
    assert imported_fields_match(
        factories.CertificateTypeFactory,
    )


def test_certificate_importer(imported_fields_match):
    assert imported_fields_match(
        factories.CertificateFactory,
        dependencies={"certificate_type": factories.CertificateTypeFactory},
    )


def test_certificate_description_importer(imported_fields_match):
    assert imported_fields_match(
        factories.CertificateDescriptionFactory,
        dependencies={"described_certificate": factories.CertificateFactory},
    )
