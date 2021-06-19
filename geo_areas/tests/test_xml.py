import pytest

from common.tests import factories
from common.tests.util import validate_taric_xml
from common.xml.namespaces import nsmap

pytestmark = pytest.mark.django_db


@validate_taric_xml(
    factories.GeographicalAreaFactory,
    factory_kwargs={"description": None},
)
def test_geographical_area_xml(xml):
    element = xml.find(".//oub:geographical.area", nsmap)
    assert element is not None


@validate_taric_xml(factories.GeographicalAreaDescriptionFactory)
def test_geographical_area_description_xml(xml):
    element = xml.find(".//oub:geographical.area.description", nsmap)
    assert element is not None
    element = xml.find(".//oub:geographical.area.description.period", nsmap)
    assert element is not None


@validate_taric_xml(factories.GeographicalMembershipFactory)
def test_geo_membership_xml(xml):
    element = xml.find(".//oub:geographical.area.membership", nsmap)
    assert element is not None
