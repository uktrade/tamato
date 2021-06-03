import pytest

from common.tests import factories
from geo_areas import serializers

pytestmark = pytest.mark.django_db


def test_geo_area_importer(imported_fields_match):
    assert imported_fields_match(
        factories.GeographicalAreaFactory,
        serializers.GeographicalAreaSerializer,
    )


def test_geo_area_with_parent_importer(imported_fields_match):
    assert imported_fields_match(
        factories.GeoGroupFactory,
        serializers.GeographicalAreaSerializer,
        dependencies={"parent": factories.GeographicalAreaFactory},
    )


def test_geo_area_description_importer(imported_fields_match):
    assert imported_fields_match(
        factories.GeographicalAreaDescriptionFactory,
        serializers.GeographicalAreaDescriptionImporterSerializer,
        dependencies={"described_geographicalarea": factories.GeographicalAreaFactory},
    )


def test_geo_area_membership_importer(imported_fields_match):
    group = factories.GeographicalAreaFactory.create(area_code=1)
    member = factories.GeographicalAreaFactory.create(area_code=0)
    assert imported_fields_match(
        factories.GeographicalMembershipFactory,
        serializers.GeographicalMembershipSerializer,
        dependencies={"geo_group": group, "member": member},
    )
