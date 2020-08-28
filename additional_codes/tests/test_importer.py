import pytest

from additional_codes import models
from additional_codes import serializers
from common.tests import factories
from common.tests.util import generate_test_import_xml
from common.validators import UpdateType
from importer.management.commands.import_taric import import_taric
from workbaskets.models import WorkflowStatus

pytestmark = pytest.mark.django_db


def test_additional_code_type_importer_create(valid_user):
    additional_code_type = factories.AdditionalCodeTypeFactory.build(
        update_type=UpdateType.CREATE.value
    )
    xml = generate_test_import_xml(
        serializers.AdditionalCodeTypeSerializer(
            additional_code_type, context={"format": "xml"}
        ).data
    )

    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED.value)

    db_additional_code_type = models.AdditionalCodeType.objects.get(
        sid=additional_code_type.sid
    )

    assert db_additional_code_type.sid == additional_code_type.sid
    assert (
        db_additional_code_type.application_code
        == additional_code_type.application_code
    )
    assert db_additional_code_type.description == additional_code_type.description
    assert (
        db_additional_code_type.valid_between.lower
        == additional_code_type.valid_between.lower
    )
    assert (
        db_additional_code_type.valid_between.upper
        == additional_code_type.valid_between.upper
    )


def test_additional_code_importer_create(valid_user):
    additional_code_type = factories.AdditionalCodeTypeFactory()
    additional_code = factories.AdditionalCodeFactory.build(
        update_type=UpdateType.CREATE.value, type=additional_code_type
    )
    xml = generate_test_import_xml(
        serializers.AdditionalCodeSerializer(
            additional_code, context={"format": "xml"}
        ).data
    )

    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED.value)

    db_additional_code = models.AdditionalCode.objects.get(sid=additional_code.sid)

    assert db_additional_code.sid == int(additional_code.sid)
    assert db_additional_code.type == additional_code_type
    assert db_additional_code.code == additional_code.code
    assert db_additional_code.valid_between.lower == additional_code.valid_between.lower
    assert db_additional_code.valid_between.upper == additional_code.valid_between.upper


def test_additional_code_description_importer_create(valid_user):
    additional_code = factories.AdditionalCodeFactory()
    description = factories.AdditionalCodeDescriptionFactory.build(
        update_type=UpdateType.CREATE.value,
        described_additional_code=additional_code,
    )
    xml = generate_test_import_xml(
        serializers.AdditionalCodeDescriptionSerializer(
            description, context={"format": "xml"}
        ).data
    )

    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED.value)

    db_description = models.AdditionalCodeDescription.objects.get(
        description_period_sid=description.description_period_sid
    )

    assert db_description.description_period_sid == description.description_period_sid
    assert db_description.description == description.description
    assert db_description.described_additional_code == additional_code
    assert db_description.valid_between.lower == description.valid_between.lower
    assert db_description.valid_between.upper == description.valid_between.upper
