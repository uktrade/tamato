from datetime import date
from typing import Type
from typing import Union

import pytest

from common.tests import factories
from common.tests.util import generate_test_import_xml
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
    through_model: Union[Type[models.TrackedModel], Type[factories.TrackedModelMixin]],
    valid_user,
    update_type=UpdateType.CREATE,
    factory_kwargs=None,
    **extra_data
):
    base_regulation = factories.RegulationFactory.create()

    if update_type != UpdateType.CREATE:
        test_regulation = factories.RegulationFactory.create(role_type=role_type)
        through_model.create(
            enacting_regulation=test_regulation,
            target_regulation=base_regulation,
            **(factory_kwargs or {})
        )
        through_model = through_model._meta.model
    else:
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
            "information_text": "|".join(
                [
                    test_regulation.information_text,
                    test_regulation.public_identifier,
                    test_regulation.url,
                ]
            ),
            "approved": test_regulation.approved,
        },
        "target_regulation": {
            "role_type": base_regulation.role_type,
            "regulation_id": base_regulation.regulation_id,
        },
        "taric_template": template,
        "update_type": update_type,
        **extra_data,
    }

    xml = generate_test_import_xml(data)
    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED.value)

    through_table_instance = through_model.objects.get(
        enacting_regulation__regulation_id=test_regulation.regulation_id,
        target_regulation__regulation_id=base_regulation.regulation_id,
        update_type=update_type,
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


def test_regulation_group_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.RegulationGroupFactory, serializers.GroupSerializer
    )


def test_regulation_group_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.RegulationGroupFactory, serializers.GroupSerializer
    )


def test_regulation_importer_create(imported_fields_match):
    regulation = factories.RegulationFactory.build(
        regulation_group=factories.RegulationGroupFactory.create()
    )

    assert imported_fields_match(
        regulation,
        serializers.RegulationImporterSerializer,
    )


def test_regulation_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.RegulationFactory,
        serializers.RegulationImporterSerializer,
        dependencies={"regulation_group": factories.RegulationGroupFactory},
    )


def test_amendment_importer_create(valid_user):
    create_and_test_m2m_regulation(
        RoleType.MODIFICATION, "taric/amendment.xml", models.Amendment, valid_user
    )


@pytest.mark.parametrize("update_type", [UpdateType.UPDATE, UpdateType.DELETE])
def test_amendment_importer_update(valid_user, update_type):
    amendment = create_and_test_m2m_regulation(
        RoleType.MODIFICATION,
        "taric/amendment.xml",
        factories.AmendmentFactory,
        valid_user,
        update_type=update_type,
    )

    amendment_version_group = amendment.version_group
    enacting_regulation_version_group = amendment.enacting_regulation.version_group
    assert amendment_version_group.versions.count() == 2
    assert amendment_version_group.current_version == amendment
    assert enacting_regulation_version_group.versions.count() == 2
    assert (
        enacting_regulation_version_group.current_version
        == amendment.enacting_regulation
    )


def test_suspension_importer_create(valid_user):
    effective_end_date = date(2021, 2, 1)
    suspension = create_and_test_m2m_regulation(
        RoleType.FULL_TEMPORARY_STOP,
        "taric/suspension.xml",
        models.Suspension,
        valid_user,
        effective_end_date=effective_end_date,
        action_record_code=models.Suspension.action_record_code,
        action_subrecord_code=models.Suspension.action_subrecord_code,
    )
    assert suspension.effective_end_date == effective_end_date


@pytest.mark.parametrize("update_type", [UpdateType.UPDATE, UpdateType.DELETE])
def test_suspension_importer_update(valid_user, update_type):
    effective_end_date = date(2021, 2, 1)
    suspension = create_and_test_m2m_regulation(
        RoleType.FULL_TEMPORARY_STOP,
        "taric/suspension.xml",
        factories.SuspensionFactory,
        valid_user,
        update_type=update_type,
        factory_kwargs={"effective_end_date": effective_end_date},
        effective_end_date=effective_end_date,
        action_record_code=models.Suspension.action_record_code,
        action_subrecord_code=models.Suspension.action_subrecord_code,
    )

    suspension_version_group = suspension.version_group
    enacting_regulation_version_group = suspension.enacting_regulation.version_group
    assert suspension_version_group.versions.count() == 2
    assert suspension_version_group.current_version == suspension
    assert enacting_regulation_version_group.versions.count() == 2
    assert (
        enacting_regulation_version_group.current_version
        == suspension.enacting_regulation
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


def test_replacement_importer_update(valid_user):
    replacement = factories.ReplacementFactory.create()

    data = {
        "enacting_regulation": {
            "role_type": replacement.enacting_regulation.role_type,
            "regulation_id": replacement.enacting_regulation.regulation_id,
        },
        "target_regulation": {
            "role_type": replacement.target_regulation.role_type,
            "regulation_id": replacement.target_regulation.regulation_id,
        },
        "taric_template": "taric/replacement.xml",
        "update_type": UpdateType.UPDATE.value,
        "measure_type_id": replacement.measure_type_id,
        "geographical_area_id": "UK",
        "chapter_heading": replacement.chapter_heading,
    }

    xml = generate_test_import_xml(data)
    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED.value)

    replacements = models.Replacement.objects.filter(
        enacting_regulation__regulation_id=replacement.enacting_regulation.regulation_id,
        target_regulation__regulation_id=replacement.target_regulation.regulation_id,
    )

    assert replacements.count() == 2

    replacement = replacements.get(update_type=UpdateType.UPDATE)

    assert replacement.measure_type_id == replacement.measure_type_id
    assert replacement.geographical_area_id == replacement.geographical_area_id
    assert replacement.chapter_heading == replacement.chapter_heading
    assert replacement.enacting_regulation == replacement.enacting_regulation
    assert replacement.target_regulation == replacement.target_regulation
    version_group = replacement.version_group
    assert version_group.versions.count() == 2
    assert (
        version_group == replacements.get(update_type=UpdateType.CREATE).version_group
    )
    assert version_group.current_version == replacement
