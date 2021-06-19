import pytest

from common.tests import factories

pytestmark = pytest.mark.django_db


def test_geo_area_importer(imported_fields_match):
    assert imported_fields_match(
        factories.GeographicalAreaFactory,
    )


def test_geo_area_with_parent_importer(imported_fields_match):
    assert imported_fields_match(
        factories.GeoGroupFactory,
        dependencies={"parent": factories.GeographicalAreaFactory},
    )


def test_geo_area_description_importer(imported_fields_match):
    assert imported_fields_match(
        factories.GeographicalAreaDescriptionFactory,
        dependencies={"described_geographicalarea": factories.GeographicalAreaFactory},
    )


def test_geo_area_membership_importer(imported_fields_match):
    group = factories.GeographicalAreaFactory.create(area_code=1)
    member = factories.GeographicalAreaFactory.create(area_code=0)
    assert imported_fields_match(
        factories.GeographicalMembershipFactory,
        dependencies={"geo_group": group, "member": member},
    )
