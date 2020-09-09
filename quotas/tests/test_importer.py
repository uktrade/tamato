from operator import itemgetter

import pytest

from common.tests import factories
from common.tests.util import validate_taric_import
from quotas import serializers

pytestmark = pytest.mark.django_db


@validate_taric_import(
    serializers.QuotaOrderNumberSerializer, factories.QuotaOrderNumberFactory
)
def test_quota_order_number_importer_create(valid_user, test_object, db_object):
    assert db_object.order_number == test_object.order_number
    assert db_object.valid_between.lower == test_object.valid_between.lower
    assert db_object.valid_between.upper == test_object.valid_between.upper


@validate_taric_import(
    serializers.QuotaOrderNumberOriginSerializer,
    factories.QuotaOrderNumberOriginFactory,
    dependencies={
        "order_number": factories.QuotaOrderNumberFactory,
        "geographical_area": factories.GeographicalAreaFactory,
    },
)
def test_quota_order_number_origin_importer_create(valid_user, test_object, db_object):
    assert db_object.order_number == test_object.order_number
    assert db_object.geographical_area == test_object.geographical_area
    assert db_object.valid_between.lower == test_object.valid_between.lower
    assert db_object.valid_between.upper == test_object.valid_between.upper


@validate_taric_import(
    serializers.QuotaOrderNumberOriginExclusionSerializer,
    factories.QuotaOrderNumberOriginExclusionFactory,
    dependencies={
        "origin": factories.QuotaOrderNumberOriginFactory,
        "excluded_geographical_area": factories.GeographicalAreaFactory,
    },
)
def test_quota_order_number_origin_exclusion_importer_create(
    valid_user, test_object, db_object
):
    assert db_object.origin == test_object.origin
    assert (
        db_object.excluded_geographical_area == test_object.excluded_geographical_area
    )


@validate_taric_import(
    serializers.QuotaDefinitionImporterSerializer,
    factories.QuotaDefinitionFactory,
    dependencies={"order_number": factories.QuotaOrderNumberFactory},
)
def test_quota_definition_importer_create(valid_user, test_object, db_object):
    assert db_object.order_number == test_object.order_number
    assert db_object.volume == test_object.volume
    assert db_object.initial_volume == test_object.initial_volume
    assert db_object.valid_between.lower == test_object.valid_between.lower
    assert db_object.valid_between.upper == test_object.valid_between.upper
    assert db_object.maximum_precision == test_object.maximum_precision
    assert db_object.quota_critical == test_object.quota_critical
    assert db_object.quota_critical_threshold == test_object.quota_critical_threshold
    assert db_object.description == test_object.description


@validate_taric_import(
    serializers.QuotaAssociationSerializer,
    factories.QuotaAssociationFactory,
    dependencies={
        "main_quota": factories.QuotaDefinitionFactory,
        "sub_quota": factories.QuotaDefinitionFactory,
    },
)
def test_quota_association_importer_create(valid_user, test_object, db_object):
    assert db_object.sub_quota_relation_type == test_object.sub_quota_relation_type
    assert db_object.coefficient == test_object.coefficient


@validate_taric_import(
    serializers.QuotaSuspensionSerializer,
    factories.QuotaSuspensionFactory,
    dependencies={"quota_definition": factories.QuotaDefinitionFactory},
)
def test_quota_suspension_importer_create(valid_user, test_object, db_object):
    assert db_object.quota_definition == test_object.quota_definition
    assert db_object.description == test_object.description


@validate_taric_import(
    serializers.QuotaBlockingSerializer,
    factories.QuotaBlockingFactory,
    dependencies={"quota_definition": factories.QuotaDefinitionFactory},
)
def test_quota_blocking_importer_create(valid_user, test_object, db_object):
    assert db_object.quota_definition == test_object.quota_definition
    assert db_object.blocking_period_type == test_object.blocking_period_type
    assert db_object.description == test_object.description


@pytest.mark.parametrize("subrecord_code", ["00", "05", "10", "15", "20", "25", "30"])
def test_quota_event_importer_create(subrecord_code, valid_user):
    @validate_taric_import(
        serializers.QuotaEventSerializer,
        factories.QuotaEventFactory,
        factory_kwargs={"subrecord_code": subrecord_code},
        dependencies={"quota_definition": factories.QuotaDefinitionFactory},
    )
    def run_assertions(_valid_user, test_object, db_object):
        db_data = sorted(db_object.data.items(), key=itemgetter(0))
        data = sorted(
            ((key, str(value)) for key, value in test_object.data.items()),
            key=itemgetter(0),
        )
        assert db_data == data
        assert test_object.subrecord_code == db_object.subrecord_code

    run_assertions(valid_user)
