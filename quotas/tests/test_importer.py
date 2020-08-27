from operator import itemgetter

import pytest

from common.tests import factories
from common.tests.util import generate_test_import_xml
from common.tests.util import requires_interdependent_export
from common.validators import UpdateType
from importer.management.commands.import_taric import import_taric
from quotas import models
from quotas import serializers
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


def test_quota_order_number_importer_create(valid_user):
    order_number = factories.QuotaOrderNumberFactory.build(
        update_type=UpdateType.CREATE
    )
    data = serializers.QuotaOrderNumberSerializer(
        order_number, context={"format": "xml"}
    ).data
    xml = generate_test_import_xml(data)

    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED)

    db_quota_order_number = models.QuotaOrderNumber.objects.get(sid=order_number.sid)

    assert db_quota_order_number.order_number == order_number.order_number
    assert db_quota_order_number.valid_between.lower == order_number.valid_between.lower
    assert db_quota_order_number.valid_between.upper == order_number.valid_between.upper


@requires_interdependent_export
def test_quota_order_number_origin_importer_create(valid_user):
    origin = factories.QuotaOrderNumberOriginFactory.build(
        update_type=UpdateType.CREATE
    )
    data = serializers.QuotaOrderNumberOriginSerializer(
        origin, context={"format": "xml"}
    ).data
    xml = generate_test_import_xml(data)

    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED)

    db_origin = models.QuotaOrderNumberOrigin.objects.get(sid=origin.sid)

    assert db_origin.order_number == origin.order_number
    assert db_origin.geographical_area == origin.geographical_area
    assert db_origin.valid_between.lower == origin.valid_between.lower
    assert db_origin.valid_between.upper == origin.valid_between.upper


@requires_interdependent_export
def test_quota_order_number_origin_importer_create(valid_user):
    origin_exclusion = factories.QuotaOrderNumberOriginExclusionFactory.build(
        update_type=UpdateType.CREATE
    )
    data = serializers.QuotaOrderNumberOriginExclusionSerializer(
        origin_exclusion, context={"format": "xml"}
    ).data
    xml = generate_test_import_xml(data)

    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED)

    db_origin_exclusion = models.QuotaOrderNumberOriginExclusion.objects.get(
        origin=origin_exclusion.origin,
        excluded_geographical_area=origin_exclusion.excluded_geographical_area,
    )

    assert db_origin_exclusion.origin == origin_exclusion.origin
    assert (
        db_origin_exclusion.excluded_geographical_area
        == origin_exclusion.excluded_geographical_area
    )


@requires_interdependent_export
def test_quota_definition_importer_create(valid_user):
    definition = factories.QuotaDefinitionFactory.build(update_type=UpdateType.CREATE)
    data = serializers.QuotaDefinitionSerializer(
        definition, context={"format": "xml"}
    ).data
    xml = generate_test_import_xml(data)

    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED)

    db_definition = models.QuotaDefinition.objects.get(sid=definition.sid)

    assert db_definition.order_number == definition.order_number
    assert db_definition.volume == definition.volume
    assert db_definition.initial_volume == definition.initial_volume
    assert db_definition.valid_between.lower == definition.valid_between.lower
    assert db_definition.valid_between.upper == definition.valid_between.upper
    assert db_definition.maximum_precision == definition.maximum_precision
    assert db_definition.quota_critical == definition.quota_critical
    assert db_definition.quota_critical_threshold == definition.quota_critical_threshold
    assert db_definition.description == definition.description


@requires_interdependent_export
def test_quota_association_importer_create(valid_user):
    association = factories.QuotaAssociationFactory.build(update_type=UpdateType.CREATE)
    data = serializers.QuotaAssociationSerializer(
        association, context={"format": "xml"}
    ).data
    xml = generate_test_import_xml(data)

    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED)

    db_association = models.QuotaAssociation.objects.get(
        main_quota=association.main_quota,
        sub_quota=association.sub_quota,
    )

    assert db_association.sub_quota_relation_type == association.sub_quota_relation_type
    assert db_association.coefficient == association.coefficient


@requires_interdependent_export
def test_quota_suspension_importer_create(valid_user):
    suspension = factories.QuotaSuspensionFactory.build(update_type=UpdateType.CREATE)
    data = serializers.QuotaSuspensionSerializer(
        suspension, context={"format": "xml"}
    ).data
    xml = generate_test_import_xml(data)

    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED)

    db_suspension = models.QuotaSuspension.objects.get(sid=suspension.sid)

    assert db_suspension.quota_definition == suspension.quota_definition
    assert db_suspension.description == suspension.description


@requires_interdependent_export
def test_quota_blocking_importer_create(valid_user):
    blocking = factories.QuotaBlockingFactory.build(update_type=UpdateType.CREATE)
    data = serializers.QuotaBlockingSerializer(blocking, context={"format": "xml"}).data
    xml = generate_test_import_xml(data)

    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED)

    db_blocking = models.QuotaBlocking.objects.get(sid=blocking.sid)

    assert db_blocking.quota_definition == blocking.quota_definition
    assert db_blocking.blocking_period_type == blocking.blocking_period_type
    assert db_blocking.description == blocking.description


@requires_interdependent_export
@pytest.mark.parametrize("subrecord_code", ["00", "05", "10", "15", "20", "25", "30"])
def test_quota_event_importer_create(subrecord_code, valid_user):
    event = factories.QuotaEventFactory.build(
        update_type=UpdateType.CREATE, subrecord_code=subrecord_code
    )
    data = serializers.QuotaEventSerializer(event, context={"format": "xml"}).data
    xml = generate_test_import_xml(data)

    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED)

    db_event = models.QuotaEvent.objects.get(
        subrecord_code=event.subrecord_code,
        quota_definition=event.quota_definition,
        occurrence_timestamp=event.occurrence_timestamp,
    )

    db_data = list(db_event.data.items()).sorted(key=itemgetter(0))
    data = list(event.data.items()).sorted(key=itemgetter(0))
    assert db_data == data
