import pytest

from certificates import serializers
from common.tests import factories
from common.tests.util import validate_taric_import

pytestmark = pytest.mark.django_db


@validate_taric_import(
    serializers.CertificateTypeSerializer, factories.CertificateTypeFactory
)
def test_certificate_type_importer_create(valid_user, test_object, db_object):
    assert db_object.sid == test_object.sid
    assert db_object.description == test_object.description
    assert db_object.valid_between.lower == test_object.valid_between.lower
    assert db_object.valid_between.upper == test_object.valid_between.upper


@validate_taric_import(
    serializers.CertificateSerializer,
    factories.CertificateFactory,
    dependencies={"certificate_type": factories.CertificateTypeFactory},
)
def test_certificate_importer_create(valid_user, test_object, db_object):
    assert db_object.sid == test_object.sid
    assert db_object.certificate_type == test_object.certificate_type


@validate_taric_import(
    serializers.CertificateDescriptionSerializer,
    factories.CertificateDescriptionFactory,
    dependencies={"described_certificate": factories.CertificateFactory},
)
def test_certificate_description_importer_create(valid_user, test_object, db_object):
    assert db_object.sid == test_object.sid
    assert db_object.description == test_object.description
    assert db_object.described_certificate == test_object.described_certificate
    assert db_object.valid_between.lower == test_object.valid_between.lower
    assert db_object.valid_between.upper == test_object.valid_between.upper
