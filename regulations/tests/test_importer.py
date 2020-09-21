from datetime import date
from typing import Type

import pytest

from common.tests import factories
from common.tests.util import generate_test_import_xml
from common.tests.util import validate_taric_import
from common.validators import UpdateType
from importer.management.commands.import_taric import import_taric
from regulations import models
from regulations import serializers
from regulations.validators import RoleType
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


def create_and_test_m2m_regulation(
    role_type: int,
    template: str,
    through_model: Type[models.TrackedModel],
    valid_user,
    **extra_data
):
    base_regulation = factories.RegulationFactory.create()
    test_regulation = factories.RegulationFactory.build(role_type=role_type)
    data = {
        "enacting_regulation": {
            "role_type": test_regulation.role_type,
            "regulation_id": test_regulation.regulation_id,
            "published_date": test_regulation.published_at,
            "official_journal_number": test_regulation.official_journal_number,
            "official_journal_page": test_regulation.official_journal_page,
            "effective_end_date": test_regulation.effective_end_date,
            "replacement_indicator": test_regulation.replacement_indicator,
            "community_code": test_regulation.community_code,
            "stopped": test_regulation.stopped,
            "information_text": test_regulation.information_text,
            "approved": test_regulation.approved,
        },
        "target_regulation": {
            "role_type": base_regulation.role_type,
            "regulation_id": base_regulation.regulation_id,
        },
        "taric_template": template,
        "update_type": UpdateType.CREATE.value,
        **extra_data,
    }

    xml = generate_test_import_xml(data)
    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED.value)

    through_table_instance = through_model.objects.get(
        enacting_regulation__regulation_id=test_regulation.regulation_id,
        target_regulation__regulation_id=base_regulation.regulation_id,
    )

    enacting_regulation = through_table_instance.enacting_regulation

    assert through_table_instance.target_regulation == base_regulation
    assert enacting_regulation.role_type == test_regulation.role_type
    assert enacting_regulation.regulation_id == test_regulation.regulation_id
    assert (
        enacting_regulation.official_journal_number
        == test_regulation.official_journal_number
    )
    assert (
        enacting_regulation.official_journal_page
        == test_regulation.official_journal_page
    )
    assert enacting_regulation.published_at == test_regulation.published_at
    assert enacting_regulation.information_text == test_regulation.information_text
    assert enacting_regulation.public_identifier == test_regulation.public_identifier
    assert enacting_regulation.url == test_regulation.url
    assert enacting_regulation.approved == test_regulation.approved
    assert (
        enacting_regulation.replacement_indicator
        == test_regulation.replacement_indicator
    )
    assert enacting_regulation.effective_end_date == test_regulation.effective_end_date
    assert enacting_regulation.stopped == test_regulation.stopped
    assert enacting_regulation.community_code == test_regulation.community_code
    assert enacting_regulation.stopped == test_regulation.stopped

    return through_table_instance


@validate_taric_import(serializers.GroupSerializer, factories.RegulationGroupFactory)
def test_regulation_group_importer_create(valid_user, test_object, db_object):
    assert db_object.group_id == test_object.group_id
    assert db_object.description == test_object.description
    assert db_object.valid_between.lower == test_object.valid_between.lower
    assert db_object.valid_between.upper == test_object.valid_between.upper


@validate_taric_import(
    serializers.RegulationImporterSerializer,
    factories.RegulationFactory,
    dependencies={"regulation_group": factories.RegulationGroupFactory},
)
def test_regulation_importer_create(valid_user, test_object, db_object):
    assert db_object.role_type == test_object.role_type
    assert db_object.regulation_id == test_object.regulation_id
    assert db_object.official_journal_number == test_object.official_journal_number
    assert db_object.official_journal_page == test_object.official_journal_page
    assert db_object.published_at == test_object.published_at
    assert db_object.information_text == test_object.information_text
    assert db_object.public_identifier == test_object.public_identifier
    assert db_object.url == test_object.url
    assert db_object.approved == test_object.approved
    assert db_object.replacement_indicator == test_object.replacement_indicator
    assert db_object.effective_end_date == test_object.effective_end_date
    assert db_object.stopped == test_object.stopped
    assert db_object.community_code == test_object.community_code
    assert db_object.stopped == test_object.stopped
    assert db_object.valid_between.lower == test_object.valid_between.lower
    assert db_object.valid_between.upper == test_object.valid_between.upper


def test_amendment_importer_create(valid_user):
    create_and_test_m2m_regulation(
        RoleType.Modification.value, "taric/amendment.xml", models.Amendment, valid_user
    )


def test_suspension_importer_create(valid_user):
    effective_end_date = date(2021, 2, 1)
    suspension = create_and_test_m2m_regulation(
        RoleType["Full temporary stop"],
        "taric/suspension.xml",
        models.Suspension,
        valid_user,
        effective_end_date=effective_end_date,
        action_record_code=models.Suspension.action_record_code,
        action_subrecord_code=models.Suspension.action_subrecord_code,
    )
    assert suspension.effective_end_date == effective_end_date


def test_replacement_importer_create(valid_user):
    target_regulation = factories.RegulationFactory.create()
    enacting_regulation = factories.RegulationFactory.create()

    measure_type_id = "AAAAAA"
    geographical_area_id = "GB"
    chapter_heading = "01"

    data = {
        "enacting_regulation": {
            "role_type": enacting_regulation.role_type,
            "regulation_id": enacting_regulation.regulation_id,
        },
        "target_regulation": {
            "role_type": target_regulation.role_type,
            "regulation_id": target_regulation.regulation_id,
        },
        "taric_template": "taric/replacement.xml",
        "update_type": UpdateType.CREATE.value,
        "measure_type_id": measure_type_id,
        "geographical_area_id": geographical_area_id,
        "chapter_heading": chapter_heading,
    }

    xml = generate_test_import_xml(data)
    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED.value)

    replacement = models.Replacement.objects.get(
        enacting_regulation__regulation_id=enacting_regulation.regulation_id,
        target_regulation__regulation_id=target_regulation.regulation_id,
    )

    assert replacement.measure_type_id == measure_type_id
    assert replacement.geographical_area_id == geographical_area_id
    assert replacement.chapter_heading == chapter_heading
    assert replacement.enacting_regulation == enacting_regulation
    assert replacement.target_regulation == target_regulation
