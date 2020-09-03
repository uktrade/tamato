import pytest

from additional_codes import serializers
from common.tests import factories
from common.tests.util import validate_taric_import

pytestmark = pytest.mark.django_db


@validate_taric_import(
    serializers.AdditionalCodeTypeSerializer, factories.AdditionalCodeTypeFactory
)
def test_additional_code_type_importer_create(valid_user, test_object, db_object):

    assert db_object.sid == test_object.sid
    assert db_object.application_code == test_object.application_code
    assert db_object.description == test_object.description
    assert db_object.valid_between.lower == test_object.valid_between.lower
    assert db_object.valid_between.upper == test_object.valid_between.upper


@validate_taric_import(
    serializers.AdditionalCodeSerializer,
    factories.AdditionalCodeFactory,
    dependencies={"type": factories.AdditionalCodeTypeFactory},
)
def test_additional_code_importer_create(valid_user, test_object, db_object):
    assert db_object.sid == int(test_object.sid)
    assert db_object.code == test_object.code
    assert db_object.valid_between.lower == test_object.valid_between.lower
    assert db_object.valid_between.upper == test_object.valid_between.upper


@validate_taric_import(
    serializers.AdditionalCodeDescriptionSerializer,
    factories.AdditionalCodeDescriptionFactory,
    dependencies={"described_additional_code": factories.AdditionalCodeFactory},
)
def test_additional_code_description_importer_create(
    valid_user, db_object, test_object
):
    assert db_object.description_period_sid == test_object.description_period_sid
    assert db_object.description == test_object.description
    assert db_object.valid_between.lower == test_object.valid_between.lower
    assert db_object.valid_between.upper == test_object.valid_between.upper
