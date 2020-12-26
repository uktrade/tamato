import pytest

from common.tests import factories
from geo_areas import serializers

pytestmark = pytest.mark.django_db


def test_geo_area_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.GeographicalAreaFactory,
        serializers.GeographicalAreaSerializer,
    )


def test_geo_area_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.GeographicalAreaFactory, serializers.GeographicalAreaSerializer
    )


def test_geo_area_with_parent_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.GeographicalAreaFactory.build(
            parent=factories.GeographicalAreaFactory.create(), area_code=1
        ),
        serializers.GeographicalAreaSerializer,
    )


def test_geo_area_with_parent_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.GeographicalAreaFactory,
        serializers.GeographicalAreaSerializer,
        dependencies={"parent": factories.GeographicalAreaFactory},
        kwargs={"area_code": 1},
    )


def test_geo_area_description_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.GeographicalAreaDescriptionFactory.build(
            area=factories.GeographicalAreaFactory.create()
        ),
        serializers.GeographicalAreaDescriptionImporterSerializer,
    )


def test_geo_area_description_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.GeographicalAreaDescriptionFactory,
        serializers.GeographicalAreaDescriptionImporterSerializer,
        dependencies={"area": factories.GeographicalAreaFactory},
    )


def test_geo_area_membership_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.GeographicalMembershipFactory.build(
            geo_group=factories.GeographicalAreaFactory.create(area_code=1),
            member=factories.GeographicalAreaFactory.create(area_code=0),
        ),
        serializers.GeographicalMembershipSerializer,
    )


def test_geo_area_membership_importer_update(update_imported_fields_match):
    group = factories.GeographicalAreaFactory.create(area_code=1)
    member = factories.GeographicalAreaFactory.create(area_code=0)
    assert update_imported_fields_match(
        factories.GeographicalMembershipFactory,
        serializers.GeographicalMembershipSerializer,
        dependencies={"geo_group": group, "member": member},
    )
