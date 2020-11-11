import pytest

from common.tests import factories
from common.tests.util import validate_taric_xml

pytestmark = pytest.mark.django_db


@validate_taric_xml(factories.GeographicalAreaFactory)
def test_geographical_area_xml(api_client, taric_schema, xml):
    element = xml.find(".//geographical.area", xml.nsmap)
    assert element is not None


@validate_taric_xml(factories.GeographicalAreaDescriptionFactory)
def test_geographical_area_description_xml(api_client, taric_schema, xml):
    element = xml.find(".//geographical.area.description", xml.nsmap)
    assert element is not None
    element = xml.find(".//geographical.area.description.period", xml.nsmap)
    assert element is not None


@validate_taric_xml(factories.GeographicalMembershipFactory)
def test_geo_membership_xml(api_client, taric_schema, xml):
    element = xml.find(".//geographical.area.membership", xml.nsmap)
    assert element is not None
