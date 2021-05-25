import pytest

from certificates import serializers
from common.tests import factories

pytestmark = pytest.mark.django_db


def test_certificate_type_importer(imported_fields_match):
    assert imported_fields_match(
        factories.CertificateTypeFactory,
        serializers.CertificateTypeSerializer,
    )


def test_certificate_importer(imported_fields_match):
    assert imported_fields_match(
        factories.CertificateFactory,
        serializers.CertificateSerializer,
        dependencies={"certificate_type": factories.CertificateTypeFactory},
    )


def test_certificate_description_importer(imported_fields_match):
    assert imported_fields_match(
        factories.CertificateDescriptionFactory,
        serializers.CertificateDescriptionSerializer,
        dependencies={"described_certificate": factories.CertificateFactory},
    )
