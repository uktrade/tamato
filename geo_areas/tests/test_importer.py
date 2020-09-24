import pytest

from common.tests import factories
from common.tests.util import generate_test_import_xml
from common.tests.util import validate_taric_import
from common.validators import UpdateType
from geo_areas import models
from geo_areas import serializers
from importer.management.commands.import_taric import import_taric
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


@validate_taric_import(
    serializers.GeographicalAreaSerializer, factories.GeographicalAreaFactory
)
def test_geo_area_importer_create(valid_user, test_object, db_object):
    assert db_object.sid == test_object.sid
    assert db_object.area_id == test_object.area_id
    assert db_object.area_code == test_object.area_code
    assert db_object.valid_between.lower == test_object.valid_between.lower
    assert db_object.valid_between.upper == test_object.valid_between.upper


@validate_taric_import(
    serializers.GeographicalAreaSerializer,
    factories.GeographicalAreaFactory,
    dependencies={"parent": factories.GeographicalAreaFactory},
    factory_kwargs={"area_code": 1},
)
def test_geo_area_with_parent_importer_create(valid_user, test_object, db_object):
    assert db_object.sid == test_object.sid
    assert db_object.area_id == test_object.area_id
    assert db_object.area_code == test_object.area_code
    assert test_object.parent is not None
    assert db_object.parent == test_object.parent
    assert db_object.valid_between.lower == test_object.valid_between.lower
    assert db_object.valid_between.upper == test_object.valid_between.upper


@validate_taric_import(
    serializers.GeographicalAreaDescriptionImporterSerializer,
    factories.GeographicalAreaDescriptionFactory,
    dependencies={"area": factories.GeographicalAreaFactory},
)
def test_geo_area_description_importer_create(valid_user, test_object, db_object):
    assert db_object.area == test_object.area
    assert db_object.description == test_object.description
    assert db_object.valid_between.lower == test_object.valid_between.lower
    assert db_object.valid_between.upper == test_object.valid_between.upper


def test_geo_area_membership_importer_create(valid_user):
    group = factories.GeographicalAreaFactory.create(area_code=1)
    member = factories.GeographicalAreaFactory.create(area_code=0)
    membership = factories.GeographicalMembershipFactory.build(
        geo_group=group, member=member, update_type=UpdateType.CREATE.value
    )
    xml = generate_test_import_xml(
        serializers.GeographicalMembershipSerializer(
            membership, context={"format": "xml"}
        ).data
    )

    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED.value)

    db_membership = models.GeographicalMembership.objects.get(
        geo_group=group, member=member
    )

    assert db_membership.geo_group == membership.geo_group
    assert db_membership.member == membership.member
    assert db_membership.valid_between.lower == membership.valid_between.lower
    assert db_membership.valid_between.upper == membership.valid_between.upper
